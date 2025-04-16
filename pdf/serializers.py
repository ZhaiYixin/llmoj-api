from rest_framework import serializers
from .models import Page, Section, PDF, PDFMessage
from chat.models import Message
from accounts.serializers import UserSerializer

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'page_number', 'content']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'title', 'description', 'start_page', 'end_page']

class PDFAnalysisSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = PDF
        fields = ['id', 'title', 'pages', 'sections']

class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='conversation.user', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'user', 'role', 'content', 'created_at']

class PDFMessageSerializer(serializers.ModelSerializer):
    message = MessageSerializer(read_only=True)

    class Meta:
        model = PDFMessage
        fields = ['id', 'message', 'section', 'page']