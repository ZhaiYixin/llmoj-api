from rest_framework import serializers
from .models import Problem, TestCase, Submission, TestCaseResult

class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ['id', 'title', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'ordinal', 'title', 'input', 'output']
        read_only_fields = ['id', 'ordinal']

class SubmissionSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'username', 'problem', 'src', 'lang', 'err', 'error_reason', 'created_at', 'updated_at']
        read_only_fields = ['id', 'username', 'problem', 'err', 'error_reason', 'created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username

    def validate(self, data):
        return data

class TestCaseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseResult
        fields = ['id', 'submission', 'test_case', 'result', 'cpu_time', 'real_time', 'memory', 'exit_code', 'signal', 'error', 'output']
