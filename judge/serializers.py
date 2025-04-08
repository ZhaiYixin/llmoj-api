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
    status = serializers.SerializerMethodField(read_only=True)
    message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'username', 'problem', 'src', 'lang', 'status', 'message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'problem', 'created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username

    def get_status(self, obj):
        if obj.err:
            return obj.err
        
        if obj.success_count == obj.total_count:
            return "Accepted"
        elif obj.success_count == 0:
            return "WrongAnswer"
        else:
            return "PartiallyAccepted"
    
    def get_message(self, obj):
        if obj.err:
            return obj.error_reason
        
        return f"{obj.success_count} / {obj.total_count}"

class TestCaseResultSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField(read_only=True)
    message = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TestCaseResult
        fields = ['id', 'submission', 'test_case', 'status', 'message', 'output']
    
    @staticmethod
    def to_status(result):
        if result == TestCaseResult.ResultCode.SUCCESS:
            return "Accepted"
        elif result == TestCaseResult.ResultCode.WRONG_ANSWER:
            return "WrongAnswer"
        elif result == TestCaseResult.ResultCode.CPU_TIME_LIMIT_EXCEEDED:
            return "TimeLimitExceeded"
        elif result == TestCaseResult.ResultCode.REAL_TIME_LIMIT_EXCEEDED:
            return "TimeLimitExceeded"
        elif result == TestCaseResult.ResultCode.MEMORY_LIMIT_EXCEEDED:
            return "MemoryLimitExceeded"
        elif result == TestCaseResult.ResultCode.RUNTIME_ERROR:
            return "RuntimeError"
        else:
            return "SystemError"
    
    @staticmethod
    def to_message(result, output=None, cpu_time=None, real_time=None, memory=None, exit_code=None, signal=None, error=None):
        if result == TestCaseResult.ResultCode.SUCCESS:
            return output
        elif result == TestCaseResult.ResultCode.WRONG_ANSWER:
            return output
        elif result == TestCaseResult.ResultCode.CPU_TIME_LIMIT_EXCEEDED:
            return f"{cpu_time}ms"
        elif result == TestCaseResult.ResultCode.REAL_TIME_LIMIT_EXCEEDED:
            return f"{real_time}ms"
        elif result == TestCaseResult.ResultCode.MEMORY_LIMIT_EXCEEDED:
            return f"{memory}B"
        elif result == TestCaseResult.ResultCode.RUNTIME_ERROR:
            error_message = []
            if exit_code:
                error_message.append(f"exit code: {exit_code}")
            if signal:
                error_message.append(f"signal: {signal}")
            if output:
                error_message.append(output)
            return "\n".join(error_message)
        else:
            return f"error code: {error}"
    
    def get_status(self, obj):
        return self.to_status(result=obj.result)
    
    def get_message(self, obj):
        return self.to_message(result=obj.result, output=obj.output, cpu_time=obj.cpu_time, real_time=obj.real_time, memory=obj.memory, exit_code=obj.exit_code, signal=obj.signal, error=obj.error)
