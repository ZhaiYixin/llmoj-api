from rest_framework import serializers

from .models import ClassGroup, ClassMember, Assignment, AssignmentPdf, Homework
from accounts.serializers import UserSerializer
from pdf.serializers import PDFSerializer
from chat.models import ConversationTemplate, Conversation
from design.models import ProblemList

class ClassGroupSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    
    class Meta:
        model = ClassGroup
        fields = ['id', 'title', 'teacher', 'created_at']

class ClassMemberSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = ClassMember
        fields = ['id', 'student', 'created_at']

class ProblemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemList
        fields = ['id', 'title']

class ConversationTemplateSerializer(serializers.ModelSerializer):    
    class Meta:
        model = ConversationTemplate
        fields = ['id', 'title']

class AssignmentSerializer(serializers.ModelSerializer):    
    conversation_template = ConversationTemplateSerializer(read_only=True)
    problem_list = ProblemListSerializer(read_only=True)
    problem_list_id = serializers.PrimaryKeyRelatedField(queryset=ProblemList.objects.all(), source='problem_list', write_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'class_group', 'problem_list', 'problem_list_id', 'conversation_template', 'release_date', 'due_date', 'created_at']
        read_only_fields = ['id', 'created_at']

class AssignmentPdfSerializer(serializers.ModelSerializer):
    pdf = PDFSerializer(read_only=True)
    
    class Meta:
        model = AssignmentPdf
        fields = ['id', 'assignment', 'pdf', 'created_at']

class HomeworkSerializer(serializers.ModelSerializer):
    problems = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = ['id', 'assignment', 'class_member', 'todo_count', 'done_count', 'problems', 'conversation', 'created_at', 'updated_at']
        read_only_fields = ['todo_count', 'done_count', 'created_at', 'updated_at']

    def get_problems(self, obj):
        return obj.get_problems()
