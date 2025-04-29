from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import os
from openai import OpenAI

from .models import Conversation, Message, ConversationTemplate

# Load environment variables from .env file
load_dotenv(override=True)
CLIENT = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
MODEL = os.getenv("MODEL")

# Load the prompt from the file
with open(os.path.join(os.path.dirname(__file__), './prompts/recommendations.txt'), 'r', encoding='utf-8') as file:
    PROMPT_RECOMMENDATIONS = file.read()
    PROMPT_RECOMMENDATIONS_TOKENS = Message.count_tokens(PROMPT_RECOMMENDATIONS)
with open(os.path.join(os.path.dirname(__file__), './prompts/system.txt'), 'r', encoding='utf-8') as file:
    PROMPT_SYSTEM = file.read()
    PROMPT_SYSTEM_TOKENS = Message.count_tokens(PROMPT_SYSTEM)

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
    tokens = Message.count_tokens(user_content)
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
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    CONTEXT_WINDOW = 8192
    RESERVED_ANSWER_LENGTH = 1024

    messages = []
    tokens = CONTEXT_WINDOW - RESERVED_ANSWER_LENGTH
    if conversation.template:
        messages.append({"role": "system", "content": conversation.template.system_message})
        tokens -= conversation.template.system_message_tokens
    else:
        messages.append({"role": "system", "content": PROMPT_SYSTEM})
        tokens -= PROMPT_SYSTEM_TOKENS
    messages += _get_context(conversation_id, tokens)

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
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    last_message = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
    if last_message and conversation.updated_at < last_message.created_at:
        CONTEXT_WINDOW = 2048
        RESERVED_ANSWER_LENGTH = 256

        messages = []
        tokens = CONTEXT_WINDOW - PROMPT_RECOMMENDATIONS_TOKENS - RESERVED_ANSWER_LENGTH
        if conversation.template:
            messages.append({"role": "system", "content": conversation.template.system_message})
            tokens -= conversation.template.system_message_tokens
        else:
            messages.append({"role": "system", "content": PROMPT_SYSTEM})
            tokens -= PROMPT_SYSTEM_TOKENS
        messages.append({"role": "user", "content": PROMPT_RECOMMENDATIONS})

        try:
            response = CLIENT.chat.completions.create(
                model=MODEL,
                messages=messages
            )
            starters = response.choices[0].message.content
            conversation.starters = starters
            conversation.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    starters = conversation.starters
    recommendations = starters.split('\n') if starters else []
    if conversation.template and conversation.template.starters:
        recommendations = conversation.template.starters.split('\n') + recommendations
    return Response({"recommendations": recommendations}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_conversation(request):
    template_id = request.data.get("template_id")
    if template_id:
        template = get_object_or_404(ConversationTemplate, id=template_id)
        with transaction.atomic():
            conversation = Conversation.objects.create(user=request.user, template=template)
            if template.initial_conversation:
                initial_messages = Message.objects.filter(conversation=template.initial_conversation).order_by('created_at')
                messages_to_create = [
                    Message(
                        conversation=conversation,
                        role=message.role,
                        content=message.content,
                        tokens=message.tokens,
                        created_at=message.created_at
                    )
                    for message in initial_messages
                ]
                Message.objects.bulk_create(messages_to_create)
    else:
        conversation = Conversation.objects.create(user=request.user)
    return Response({"conversation_id": conversation.id}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_template(request, template_id):
    template = get_object_or_404(ConversationTemplate, id=template_id)
    return Response({
        "id": template.id,
        "title": template.title,
        "initial_conversation": template.initial_conversation.id if template.initial_conversation else None,
        "starters": template.starters
    }, status=status.HTTP_200_OK)