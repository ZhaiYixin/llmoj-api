import json
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from dotenv import load_dotenv
import os
from openai import OpenAI
from .models import Conversation, Message

# Load environment variables from .env file
load_dotenv()

# Create your views here.
class ConversationView(View):
    def get(self, request, conversation_id):
        messages = self._get_conversation_messages(conversation_id)
        return JsonResponse({"messages": messages})

    def post(self, request, conversation_id):
        try:
            data = json.loads(request.body)
            user_content = data.get("content")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not user_content:
            return JsonResponse({"error": "Missing 'content' in request body"}, status=400)

        messages = [{"role": "system", "content": "You are a helpful assistant"}]
        messages += self._get_conversation_messages(conversation_id)
        messages.append({"role": "user", "content": user_content})

        response_stream = self._get_openai_response_stream(messages)

        conversation = Conversation.objects.get(id=conversation_id)
        Message.objects.create(conversation=conversation, role='user', content=user_content)

        def stream_response():
            assistant_content = ""
            for chunk in response_stream:
                yield chunk
                assistant_content += chunk
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_content)

        return StreamingHttpResponse(stream_response(), content_type='text/plain')

    def _get_openai_response(self, messages):
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("BASE_URL")
        model = os.getenv("MODEL")

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content

    def _get_openai_response_stream(self, messages):
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("BASE_URL")
        model = os.getenv("MODEL")

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        for chunk in response:
            yield chunk.choices[0].delta.content

    def _get_conversation_messages(self, conversation_id):
        conversation_messages = Message.objects.filter(conversation_id=conversation_id).order_by('created_at')
        return [{"role": msg.role, "content": msg.content} for msg in conversation_messages]
