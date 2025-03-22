from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import os
from openai import OpenAI

from .utils import _count_tokens
from .models import Conversation, Message

# Load environment variables from .env file
load_dotenv(override=True)
CLIENT = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
MODEL = os.getenv("MODEL")

# Load the prompt from the file
with open(os.path.join(os.path.dirname(__file__), './prompts/recommendations.txt'), 'r', encoding='utf-8') as file:
    PROMPT_RECOMMENDATIONS = file.read()
    PROMPT_RECOMMENDATIONS_TOKENS = _count_tokens(PROMPT_RECOMMENDATIONS)
with open(os.path.join(os.path.dirname(__file__), './prompts/system.txt'), 'r', encoding='utf-8') as file:
    PROMPT_SYSTEM = file.read()
    PROMPT_SYSTEM_TOKENS = _count_tokens(PROMPT_SYSTEM)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    username = request.query_params.get('username', None)
    if not username:
        username = request.user.username
    if username != request.user.username:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    conversations = Conversation.objects.filter(user__username=username).order_by('-created_at')
    conversation_list = [{"id": conv.id, "title": conv.title, "created_at": conv.created_at} for conv in conversations]
    return Response({"conversations": conversation_list}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, conversation_id):
    messages = Message.objects.filter(conversation_id=conversation_id).order_by('created_at')
    message_list = [{"role": msg.role, "content": msg.content} for msg in messages]
    return Response({"messages": message_list}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_question(request, conversation_id):
    MAX_QUESTION_LENGTH = 1024

    data = request.data
    user_content = data.get("content")
    if not user_content:
        return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)
    tokens = _count_tokens(user_content)
    if tokens > MAX_QUESTION_LENGTH:
        return Response({"error": "Content exceeds maximum length"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        conversation = Conversation.objects.get(id=conversation_id)
        Message.objects.create(conversation=conversation, role='user', content=user_content, tokens=tokens)
        return Response({"status": "Message added successfully"}, status=status.HTTP_201_CREATED)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

def _get_context(conversation_id, available_tokens):
    # 在长度有限的前提下，尽可能多地放入之前的消息，作为上下文
    conversation_messages = Message.objects.filter(conversation_id=conversation_id).order_by('-created_at')
    context_messages = []
    
    for msg in conversation_messages:
        available_tokens -= msg.tokens
        if available_tokens < 0:
            break
        else:
            context_messages.append({"role": msg.role, "content": msg.content})
    
    return context_messages[::-1]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_answer(request, conversation_id):
    CONTEXT_WINDOW = 8192
    RESERVED_ANSWER_LENGTH = 1024

    messages = [{"role": "system", "content": PROMPT_SYSTEM}]
    messages += _get_context(conversation_id, CONTEXT_WINDOW - PROMPT_SYSTEM_TOKENS - RESERVED_ANSWER_LENGTH)

    try:
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        )

        def stream_response():
            chunks = []
            for chunk in response:
                chunks.append(chunk)
                yield chunk.choices[0].delta.content

            assistant_content = "".join([chunk.choices[0].delta.content for chunk in chunks])
            last_chunk = chunks[-1]
            usage = last_chunk.usage
            conversation = Conversation.objects.get(id=conversation_id)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_content, tokens=usage.completion_tokens)

        return StreamingHttpResponse(stream_response(), content_type='text/plain')
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendations(request, conversation_id):
    CONTEXT_WINDOW = 2048
    RESERVED_ANSWER_LENGTH = 256

    messages = [{"role": "system", "content": PROMPT_SYSTEM}]
    messages += _get_context(conversation_id, CONTEXT_WINDOW - PROMPT_SYSTEM_TOKENS - PROMPT_RECOMMENDATIONS_TOKENS - RESERVED_ANSWER_LENGTH)
    messages.append({"role": "user", "content": PROMPT_RECOMMENDATIONS})

    try:
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        recommendations = response.choices[0].message.content
        return Response({"recommendations": recommendations.split('\n')}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
