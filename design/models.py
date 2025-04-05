from django.conf import settings
from django.db import models

from judge.models import Problem, TestCase

# Create your models here.
class ProblemDesign(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE, related_name='design')
    designer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='problem_designs', on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.problem.title} - Design"

class ProblemList(models.Model):
    title = models.CharField(max_length=255, default='')
    description = models.TextField()
    designer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='problem_list_designs', on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ProblemListItem(models.Model):
    problem_list = models.ForeignKey(ProblemList, related_name='problems', on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, related_name='problem_lists', on_delete=models.SET_NULL, null=True, blank=True)
    ordinal = models.PositiveIntegerField()
    
    def __str__(self):
        return f"Problem {self.ordinal} in {self.problem_list.title}"
