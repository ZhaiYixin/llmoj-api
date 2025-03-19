import json
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from dotenv import load_dotenv
import os
from openai import OpenAI
from .models import Conversation, Message

# Load environment variables from .env file
load_dotenv()
CLIENT = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
MODEL = os.getenv("MODEL")

# Load the prompt from the file
with open(os.path.join(os.path.dirname(__file__), './prompts/recommendations.txt'), 'r', encoding='utf-8') as file:
    PROMPT_RECOMMENDATIONS = file.read()

# Create your views here.
def _get_messages(conversation_id):
        conversation_messages = Message.objects.filter(conversation_id=conversation_id).order_by('created_at')
        return [{"role": msg.role, "content": msg.content} for msg in conversation_messages]

def get_messages(request, conversation_id):
    messages = _get_messages(conversation_id)
    return JsonResponse({"messages": messages})

def ask_question(request, conversation_id):
    data = json.loads(request.body)
    user_content = data.get("content")

    conversation = Conversation.objects.get(id=conversation_id)
    Message.objects.create(conversation=conversation, role='user', content=user_content)

    return JsonResponse({"status": "Message added successfully"})

def get_answer(request, conversation_id):
        messages = [{"role": "system", "content": "You are a helpful assistant"}]
        messages += _get_messages(conversation_id)

        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        )

        def stream_response():
            assistant_content = ""
            for chunk in response:
                assistant_content += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content
            conversation = Conversation.objects.get(id=conversation_id)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_content)

        return StreamingHttpResponse(stream_response(), content_type='text/plain')

def get_recommendations(request, conversation_id):
    messages = [{"role": "system", "content": "You are a helpful assistant"}]
    messages += _get_messages(conversation_id)
    messages.append({"role": "user", "content": PROMPT_RECOMMENDATIONS})

    response = CLIENT.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    recommendations = response.choices[0].message.content
    return JsonResponse({"recommendations": recommendations.split('\n')})
