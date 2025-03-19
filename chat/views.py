import json
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
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

# Create your views here.
def _get_messages(conversation_id):
    conversation_messages = Message.objects.filter(conversation_id=conversation_id).order_by('created_at')
    return [{"role": msg.role, "content": msg.content} for msg in conversation_messages]

def get_messages(request, conversation_id):
    messages = _get_messages(conversation_id)
    return JsonResponse({"messages": messages})

def ask_question(request, conversation_id):
    MAX_QUESTION_LENGTH = 1024
    
    data = json.loads(request.body)
    user_content = data.get("content")
    if not user_content:
        return JsonResponse({"error": "Content is required"}, status=400)
    tokens = _count_tokens(user_content)
    if tokens > MAX_QUESTION_LENGTH:
        return JsonResponse({"error": "Content exceeds maximum length"}, status=400)

    conversation = Conversation.objects.get(id=conversation_id)
    Message.objects.create(conversation=conversation, role='user', content=user_content, tokens=tokens)

    return JsonResponse({"status": "Message added successfully"})

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

def get_answer(request, conversation_id):
    CONTEXT_WINDOW = 8192
    RESERVED_ANSWER_LENGTH = 1024
    
    messages = [{"role": "system", "content": PROMPT_SYSTEM}]
    messages += _get_context(conversation_id, CONTEXT_WINDOW - PROMPT_SYSTEM_TOKENS - RESERVED_ANSWER_LENGTH)

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

def get_recommendations(request, conversation_id):
    CONTEXT_WINDOW = 2048
    RESERVED_ANSWER_LENGTH = 256
    
    messages = [{"role": "system", "content": PROMPT_SYSTEM}]
    messages += _get_context(conversation_id, CONTEXT_WINDOW - PROMPT_SYSTEM_TOKENS - PROMPT_RECOMMENDATIONS_TOKENS - RESERVED_ANSWER_LENGTH)
    messages.append({"role": "user", "content": PROMPT_RECOMMENDATIONS})

    response = CLIENT.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    recommendations = response.choices[0].message.content
    return JsonResponse({"recommendations": recommendations.split('\n')})
