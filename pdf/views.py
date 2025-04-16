import os
import uuid
import json

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.http import FileResponse, StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from dotenv import load_dotenv
from openai import OpenAI
import pdfplumber

from .models import PDF, Page, Section, PDFConversation, PDFMessage
from .serializers import PDFAnalysisSerializer, PDFMessageSerializer
from chat.models import Message
from accounts.permissions import IsTeacher, WritableIfIsTeacher

# Create your views here.
load_dotenv(override=True)
CLIENT = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
MODEL = os.getenv("MODEL")

with open(os.path.join(os.path.dirname(__file__), './prompts/summarize.txt'), 'r', encoding='utf-8') as file:
    PROMPT_SUMMARIZE = file.read()
    PROMPT_SUMMARIZE_TOKENS = Message.count_tokens(PROMPT_SUMMARIZE)
with open(os.path.join(os.path.dirname(__file__), './prompts/answer.txt'), 'r', encoding='utf-8') as file:
    PROMPT_ANSWER = file.read()
    PROMPT_ANSWER_TOKENS = Message.count_tokens(PROMPT_ANSWER)

class PDFFileUploadView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        unique_filename = f"{uuid.uuid4()}_{file.name}"
        file_path = default_storage.save(f'pdfs/{unique_filename}', ContentFile(file.read()))

        pdf = PDF.objects.create(title=file.name, file=file_path)

        return Response({"message": "File uploaded successfully", "pdf_id": pdf.id}, status=status.HTTP_201_CREATED)


class PDFFileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pdf_id):
        pdf = get_object_or_404(PDF, id=pdf_id)
        file_path = pdf.file.path

        if not default_storage.exists(file_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        file_url = default_storage.url(file_path)
        return Response({"id": pdf.id, "file_url": file_url, "title": pdf.title, "created_at": pdf.created_at}, status=status.HTTP_200_OK)


class PDFAnalysisView(APIView):
    permission_classes = [IsAuthenticated, WritableIfIsTeacher]
    
    def get(self, request, pdf_id):
        pdf = get_object_or_404(PDF, id=pdf_id)
        serializer = PDFAnalysisSerializer(pdf)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, pdf_id):
        pdf = get_object_or_404(PDF, id=pdf_id)
        file_path = pdf.file.path
        
        if not default_storage.exists(file_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # 提取pdf中的文本
        with default_storage.open(file_path, 'rb') as file_stream:
            with pdfplumber.open(file_stream) as file_parsed:
                pages = [page.extract_text() for page in file_parsed.pages]
        pdf_text = f"# {pdf.title}\n\n" + "\n".join([f"## 第 {i + 1} 页\n" + (f'```\n{page}\n```\n' if page else '无文本\n') for i, page in enumerate(pages)])
        
        # 调用大语言模型来生成大纲
        messages = [
            {"role": "system", "content": PROMPT_SUMMARIZE},
            {"role": "user", "content": pdf_text}
        ]
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={'type': 'json_object'},
        )
        outline = response.choices[0].message.content
        try:
            sections = json.loads(outline)
        except json.JSONDecodeError:
            return Response({"error": "Failed to parse outline from AI response"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 保存结果到数据库
        with transaction.atomic():
            pdf.pages.all().delete()
            for i, page_text in enumerate(pages):
                Page.objects.create(pdf=pdf, page_number=i + 1, content=page_text)
            
            pdf.sections.all().delete()
            for s in sections:
                Section.objects.create(
                    pdf=pdf,
                    title=s.get("title", ""),
                    description=s.get("description", ""),
                    start_page=s.get("start_page"),
                    end_page=s.get("end_page")
                )
        
        return Response({"message": "PDF analyzed and sections saved successfully"}, status=status.HTTP_200_OK)


class PDFMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pdf_id):
        pdf = get_object_or_404(PDF, id=pdf_id)
        pdf_messages = PDFMessage.objects.filter(pdf_conversation__pdf=pdf).select_related('message__conversation').order_by('message__created_at')

        section_id = request.query_params.get('section_id')
        if section_id:
            section = get_object_or_404(Section, id=section_id, pdf=pdf)
            pdf_messages = pdf_messages.filter(section=section)
        
        page_id = request.query_params.get('page_id')
        if page_id:
            page = get_object_or_404(Page, id=page_id, pdf=pdf)
            pdf_messages = pdf_messages.filter(page=page)

        serializer = PDFMessageSerializer(pdf_messages, many=True)
        return Response({"messages": serializer.data}, status=status.HTTP_200_OK)


class PDFAskQuestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pdf_id):
        MAX_QUESTION_LENGTH = 1024

        data = request.data
        user_content = data.get("content")
        if not user_content:
            return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)
        tokens = Message.count_tokens(user_content)
        if tokens > MAX_QUESTION_LENGTH:
            return Response({"error": "Content exceeds maximum length"}, status=status.HTTP_400_BAD_REQUEST)
        page_id = data.get("page_id")
        section_id = data.get("section_id")

        try:
            pdf_conversation = PDFConversation.get_or_create_conversation(pdf_id=pdf_id, user=request.user)
            PDFMessage.create_message(
                pdf_conversation=pdf_conversation,
                page=get_object_or_404(Page, id=page_id, pdf=pdf_conversation.pdf) if page_id else None,
                section=get_object_or_404(Section, id=section_id, pdf=pdf_conversation.pdf) if section_id else None,
                role='user',
                content=user_content,
                tokens=tokens
            )
            return Response({"status": "Message added successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PDFGetAnswerView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pdf_id):
        CONTEXT_WINDOW = 8192
        RESERVED_ANSWER_LENGTH = 1024
        
        pdf = get_object_or_404(PDF, id=pdf_id)
        pdf_conversation = get_object_or_404(PDFConversation, pdf=pdf, conversation__user=request.user)
        last_pdf_message = PDFMessage.objects.filter(pdf_conversation=pdf_conversation).order_by('-message__created_at').first()
        if not last_pdf_message:
            return Response({"error": "No messages found for this PDF"}, status=status.HTTP_404_NOT_FOUND)

        try:
            messages = self._get_context(pdf_conversation.id, CONTEXT_WINDOW - RESERVED_ANSWER_LENGTH)
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
                PDFMessage.create_message(
                    pdf_conversation=pdf_conversation,
                    role='assistant',
                    content=assistant_content,
                    tokens=usage.completion_tokens,
                    page=last_pdf_message.page,
                    section=last_pdf_message.section
                )

            return StreamingHttpResponse(stream_response(), content_type='text/plain')
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_context(self, pdf_conversation_id, available_tokens):
        # system prompt
        available_tokens -= PROMPT_ANSWER_TOKENS
        if available_tokens < 0:
            raise ValueError("Not enough tokens available for system prompt")
        system_prompt = [{"role": "system", "content": PROMPT_ANSWER}]
        
        # 提问的prompt
        pdf_messages = PDFMessage.objects.filter(pdf_conversation_id=pdf_conversation_id).order_by('-message__created_at')
        last_pdf_message = pdf_messages.first()
        if not last_pdf_message:
            raise ValueError("No messages found for this PDF conversation")
        available_tokens -= last_pdf_message.message.tokens
        if available_tokens < 0:
            raise ValueError("Not enough tokens available for last message")
        question_prompt = [{"role": last_pdf_message.message.role, "content": last_pdf_message.message.content}]
        
        # 当前section的描述
        section_prompt = []
        section = last_pdf_message.section
        if section:
            section_background = f"我正在看着《{section.pdf.title}》的“{section.title}”章节，这一章节的大概内容是：\n" + f'```\n{section.description}\n```\n'
            section_background_tokens = Message.count_tokens(section_background)
            available_tokens -= section_background_tokens
            if available_tokens >= 0:
                section_prompt.append({"role": "user", "content": section_background})
        
        # 当前page的文本
        page_prompt = []
        page = last_pdf_message.page
        if page and page.content:
            page_background = f"更具体来说，我正在看着《{page.pdf.title}》的第{page.page_number}页，从这一页提取出来的文本如下：\n" + f'```\n{page.content}\n```\n'
            page_background_tokens = Message.count_tokens(page_background)
            available_tokens -= page_background_tokens
            if available_tokens >= 0:
                page_prompt.append({"role": "user", "content": page_background})
        
        # 历史问答记录
        history_prompts = []
        for m in pdf_messages[1:]:
            available_tokens -= m.message.tokens
            if available_tokens < 0:
                break
            else:
                history_prompts.append({"role": m.message.role, "content": m.message.content})
        history_prompts.reverse()
                
        return system_prompt + section_prompt + page_prompt + history_prompts + question_prompt

