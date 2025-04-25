import json  # 添加导入
from django.conf import settings
from django.db import models

from design.models import ProblemList
from pdf.models import PDF
from chat.models import ConversationTemplate, Conversation

class ClassGroup(models.Model):
    title = models.CharField(max_length=255, default='')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='class_groups', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ClassMember(models.Model):
    class_group = models.ForeignKey(ClassGroup, related_name='members', on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='class_members', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} in {self.class_group.title}"

class Assignment(models.Model):
    class_group = models.ForeignKey(ClassGroup, related_name='assignments', on_delete=models.CASCADE)
    problem_list = models.ForeignKey(ProblemList, related_name='assignments', on_delete=models.CASCADE)
    conversation_template = models.ForeignKey(ConversationTemplate, related_name='assignments', on_delete=models.SET_NULL, null=True, blank=True)
    release_date = models.DateTimeField()
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Assignment for {self.class_group.title} - {self.problem_list.title}"

class AssignmentPdf(models.Model):
    assignment = models.ForeignKey(Assignment, related_name='pdfs', on_delete=models.CASCADE)
    pdf = models.ForeignKey(PDF, related_name='assignment_pdfs', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PDF for {self.assignment.problem_list.title} - {self.assignment.class_group.title}"

class Homework(models.Model):
    assignment = models.ForeignKey(Assignment, related_name='homeworks', on_delete=models.CASCADE)
    class_member = models.ForeignKey(ClassMember, related_name='homeworks', on_delete=models.CASCADE)
    todo_count = models.IntegerField(default=0)  # total number of problems in problem_list
    done_count = models.IntegerField(default=0)  # number of problems solved by the student
    problems = models.TextField(default='{}')  # {problem_list_item_id_1: { 'best_submission': {'id': 1, 'total_count': 5, 'success_count': 3}, 'submissions': [1, 2, 3] }, problem_list_item_id_2: ...}
    conversation = models.OneToOneField(Conversation, related_name='homework', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'class_member'],
                name='unique_homework'
            )
        ]

    def get_problems(self):
        if not self.problems or self.problems == '{}':
            return {}
        try:
            return json.loads(self.problems)
        except json.JSONDecodeError:
            return {}

    def set_problems(self, problems_dict):
        self.problems = json.dumps(problems_dict)

    def update_problems(self, problem_list_item_id, submission):
        problems = self.get_problems()
        if problem_list_item_id not in problems:
            problems[problem_list_item_id] = {
                'best_submission': None,
                'submissions': []
            }
        
        problems[problem_list_item_id]['submissions'].append(submission.id)
        
        best_submission = problems[problem_list_item_id]['best_submission']
        if best_submission is None or submission.success_count > best_submission.get('success_count', 0):
            problems[problem_list_item_id]['best_submission'] = {
                'id': submission.id,
                'total_count': submission.total_count,
                'success_count': submission.success_count,
            }
        
        self.set_problems(problems)
    
    def _update_todo_count(self):
        self.todo_count = self.assignment.problem_list.problems.count()
    
    def _update_done_count(self):
        self.done_count = sum( 1 for problem in self.get_problems().values() if problem.get('best_submission') and problem['best_submission'].get('success_count', 0) == problem['best_submission'].get('total_count', 0) )
    
    def save(self, *args, **kwargs):
        self._update_todo_count()
        self._update_done_count()
        super().save(*args, **kwargs)
