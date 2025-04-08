from django.conf import settings
from django.db import models

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