from django.conf import settings
from django.db import models
from django.db import transaction

from chat.models import Conversation, Message

# Create your models here.
class Problem(models.Model):
    title = models.CharField(max_length=255, default='')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, related_name='test_cases', on_delete=models.CASCADE)
    ordinal = models.PositiveIntegerField()
    title = models.CharField(max_length=255, default='', blank=True)
    input = models.TextField()
    output = models.TextField()
    
    def __str__(self):
        return f'TestCase{self.ordinal} for {self.problem.title}'

class Submission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='submissions', on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, related_name='submissions', on_delete=models.CASCADE)
    src = models.TextField()
    lang = models.CharField(max_length=50)
    err = models.CharField(max_length=50, null=True, blank=True)
    error_reason = models.TextField(null=True, blank=True)
    # When compilation is failed, following data will be returned
    # {
    #     "err": "CompileError", 
    #     "data": "error resson"
    # }
    total_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Submission by {self.user.username} for {self.problem.title}'

class TestCaseResult(models.Model):
    class ResultCode:
        WRONG_ANSWER = -1  # This means the process exited normally, but the answer is wrong
        SUCCESS = 0  # This means the answer is accepted
        CPU_TIME_LIMIT_EXCEEDED = 1
        REAL_TIME_LIMIT_EXCEEDED = 2
        MEMORY_LIMIT_EXCEEDED = 3
        RUNTIME_ERROR = 4
        SYSTEM_ERROR = 5

    class ErrorCode:
        SUCCESS = 0
        INVALID_CONFIG = -1
        CLONE_FAILED = -2
        PTHREAD_FAILED = -3
        WAIT_FAILED = -4
        ROOT_REQUIRED = -5
        LOAD_SECCOMP_FAILED = -6
        SETRLIMIT_FAILED = -7
        DUP2_FAILED = -8
        SETUID_FAILED = -9
        EXECVE_FAILED = -10
        SPJ_ERROR = -11

    submission = models.ForeignKey(Submission, related_name='results', on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, related_name='results', on_delete=models.CASCADE)
    result = models.IntegerField()
    cpu_time = models.PositiveIntegerField()  # unit is ms
    real_time = models.PositiveIntegerField()  # unit is ms
    memory = models.PositiveIntegerField()  # unit is byte
    output = models.TextField(null=True, blank=True)
    exit_code = models.IntegerField()
    signal = models.IntegerField()
    error = models.IntegerField()

    def __str__(self):
        return f'Result for {self.submission} on {self.test_case}'

class ProblemConversation(models.Model):
    problem = models.ForeignKey(Problem, related_name='conversations', on_delete=models.CASCADE)
    conversation = models.ForeignKey('chat.Conversation', related_name='problem_conversations', on_delete=models.CASCADE)

    def __str__(self):
        return f'Conversation {self.conversation.id} for Problem {self.problem.title}'

    @classmethod
    def get_or_create_conversation(cls, problem_id, user):
        with transaction.atomic():
            problem_conversation = cls.objects.filter(problem_id=problem_id, conversation__user=user).first()
            if not problem_conversation:
                conversation = Conversation.objects.create(user=user)
                problem_conversation = cls.objects.create(problem_id=problem_id, conversation=conversation)
            return problem_conversation

class ProblemMessage(models.Model):
    problem_conversation = models.ForeignKey(ProblemConversation, related_name='messages', on_delete=models.CASCADE)
    message = models.OneToOneField(Message, related_name='problem_message', on_delete=models.CASCADE)
    src = models.TextField(null=True, blank=True)
    lang = models.CharField(max_length=50, null=True, blank=True)
    relevant_submission = models.ForeignKey(Submission, related_name='problem_messages', null=True, blank=True, on_delete=models.CASCADE)
    start_question = models.ForeignKey('ProblemMessage', related_name='successive_questions', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'Message {self.message.id} in Problem {self.problem_conversation.problem.title}'
    
    @classmethod
    def create_message(cls, problem_conversation, role, content, tokens=0, src=None, lang=None, relevant_submission=None, start_question=None):
        with transaction.atomic():
            message = Message.objects.create(
                conversation=problem_conversation.conversation,
                role=role,
                content=content,
                tokens=tokens
            )
            problem_message = cls.objects.create(
                problem_conversation=problem_conversation,
                message=message,
                src=src,
                lang=lang,
                relevant_submission=relevant_submission,
                start_question=start_question
            )
            return problem_message