from rest_framework import serializers

from .models import Problem, TestCase, ProblemDesign, ProblemList, ProblemListItem
from judge.serializers import ProblemSerializer, TestCaseSerializer
from accounts.serializers import UserSerializer


class ProblemDesignSerializer(serializers.ModelSerializer):
    designer = UserSerializer(read_only=True)
    
    class Meta:
        model = ProblemDesign
        fields = ['id', 'problem', 'designer', 'is_public']
        read_only_fields = ['id', 'problem', 'designer']


class ProblemListSerializer(serializers.ModelSerializer):
    designer = UserSerializer(read_only=True)
    
    class Meta:
        model = ProblemList
        fields = ['id', 'title', 'description', 'designer', 'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'designer', 'created_at', 'updated_at']


class ProblemListItemSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)

    class Meta:
        model = ProblemListItem
        fields = ['id', 'problem_list', 'problem', 'ordinal']
        read_only_fields = ['id', 'problem_list', 'ordinal']

