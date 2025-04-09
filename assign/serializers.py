from rest_framework import serializers

from .models import ClassGroup, ClassMember, Assignment, Homework
from accounts.serializers import UserSerializer

class ClassGroupSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    
    class Meta:
        model = ClassGroup
        fields = ['id', 'title', 'teacher', 'created_at']

class ClassMemberSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = ClassMember
        fields = ['student', 'created_at']

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'class_group', 'problem_list', 'release_date', 'due_date', 'created_at']
        read_only_fields = ['id', 'created_at']

class HomeworkSerializer(serializers.ModelSerializer):
    problems = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = ['id', 'assignment', 'class_member', 'todo_count', 'done_count', 'problems', 'created_at', 'updated_at']
        read_only_fields = ['todo_count', 'done_count', 'created_at', 'updated_at']

    def get_problems(self, obj):
        return obj.get_problems()
