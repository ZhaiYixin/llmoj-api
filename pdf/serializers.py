from rest_framework import serializers
from .models import Page, Section, PDF, PDFMessage
from chat.models import Message
from accounts.serializers import UserSerializer

class PDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDF
        fields = ['id', 'title', 'file', 'created_at']

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'page_number', 'content']

class SectionSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = ['id', 'title', 'description', 'start_page', 'end_page', 'questions']

    def get_questions(self, obj):
        if not obj.questions:
            return []
        questions = obj.questions.split('\n')
        questions = list(filter(str.strip, questions))
        return questions

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