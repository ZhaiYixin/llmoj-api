import os

from django.shortcuts import get_object_or_404
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from .models import Problem, TestCase, Submission, TestCaseResult
from .serializers import ProblemSerializer, TestCaseSerializer, SubmissionSerializer, TestCaseResultSerializer
from .JudgeServer.client.Python.client import JudgeServerClient
from .JudgeServer.client.Python.languages import c_lang_config, cpp_lang_config, java_lang_config, c_lang_spj_config, c_lang_spj_compile, py2_lang_config, py3_lang_config, go_lang_config, php_lang_config, js_lang_config

# Load environment variables from .env file
load_dotenv(override=True)
CLIENT = JudgeServerClient(token=os.getenv("JUDGE_SERVER_TOKEN"), server_base_url=os.getenv("JUDGE_SERVER_BASE_URL"))

# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_problems(request):
    problems = Problem.objects.all()
    
    problem_id = request.query_params.get('problem_id', None)
    
    if problem_id:
        problems = problems.filter(id=problem_id)

    serializer = ProblemSerializer(problems, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_problem_testcases(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    testCases = TestCase.objects.filter(problem_id=problem_id)
    testCases = testCases.order_by('ordinal')
    serializer = TestCaseSerializer(testCases, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

def _get_lang_config(lang):
    lang_dict = {
        "C": c_lang_config,
        "C++": cpp_lang_config,
        "Java": java_lang_config,
        "Python2": py2_lang_config,
        "Python3": py3_lang_config,
        "Go": go_lang_config,
        "PHP": php_lang_config,
        "JavaScript": js_lang_config,
    }
    return lang_dict.get(lang)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_code(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    
    src = request.data.get('src')
    lang = request.data.get('lang')
    input_data = request.data.get('input', '')
    output_data = request.data.get('output', '')
    
    if not src or not lang:
        return Response({"error": "Source code and language are required"}, status=status.HTTP_400_BAD_REQUEST)
    
    lang_config = _get_lang_config(lang)
    if not lang_config:
        return Response({"error": "Unsupported language"}, status=status.HTTP_400_BAD_REQUEST)
    
    test = [{"input": input_data, "output": output_data}]
    
    judge = CLIENT.judge(
        src=src,
        language_config=lang_config,
        max_cpu_time=1000,
        max_memory=1024 * 1024 * 128,
        test_case=test,
        output=True
    )
    
    if judge.get("err"):
        return Response({"err": judge.get("err"), "data": judge.get("data")}, status=status.HTTP_200_OK)
    
    r = judge.get("data")[0]
    
    return Response({
        "err": None,
        "data": {
            "status": TestCaseResultSerializer.to_status(r.get("result")),
            "message": TestCaseResultSerializer.to_message(r.get("result"), r.get("output"), r.get("cpu_time"), r.get("real_time"), r.get("memory"), r.get("exit_code"), r.get("signal"), r.get("error")),
            "output": r.get("output"),
        }
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_code(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    
    serializer = SubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    src = serializer.validated_data['src']
    lang = serializer.validated_data['lang']
    
    lang_config = _get_lang_config(lang)
    if not lang_config:
        return Response({"error": "Unsupported language"}, status=status.HTTP_400_BAD_REQUEST)
    
    test_cases = TestCase.objects.filter(problem_id=problem_id).order_by('ordinal')
    test = [{"input": case.input, "output": case.output} for case in test_cases]
    
    judge = CLIENT.judge(
        src=src,
        language_config=lang_config,
        max_cpu_time=1000,
        max_memory=1024 * 1024 * 128,
        test_case=test,
        output=True
    )
    
    with transaction.atomic():
        total_count = len(test_cases)
        success_count = 0 if judge.get("err") else sum(result.get("result") == TestCaseResult.ResultCode.SUCCESS for result in judge.get("data", []))
        
        submission = Submission.objects.create(
            user=request.user,
            problem=problem,
            src=src,
            lang=lang,
            err=judge.get("err"),
            error_reason=judge.get("data") if judge.get("err") else None,
            total_count=total_count,
            success_count=success_count,
        )
        
        if not judge.get("err"):
            test_case_results = [
                TestCaseResult(
                    submission=submission,
                    test_case=case,
                    result=result.get("result"),
                    cpu_time=result.get("cpu_time"),
                    real_time=result.get("real_time"),
                    memory=result.get("memory"),
                    output=result.get("output"),
                    exit_code=result.get("exit_code"),
                    signal=result.get("signal"),
                    error=result.get("error"),
                )
                for case, result in zip(test_cases, judge.get("data", []))
            ]
            TestCaseResult.objects.bulk_create(test_case_results)
    
    return Response({"submission_id": submission.id}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submissions(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    submissions = Submission.objects.filter(problem_id=problem_id)
    
    submission_id = request.query_params.get('submission_id', None)
    username = request.query_params.get('username', request.user.username)
    order_by = request.query_params.get('order_by', '-created_at')
    
    if submission_id:
        submissions = submissions.filter(id=submission_id)
    
    if username:
        submissions = submissions.filter(user__username=username)
    
    if order_by.lstrip('-') in ['created_at']:
        submissions = submissions.order_by(order_by)
    
    serializer = SubmissionSerializer(submissions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_results(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    results = TestCaseResult.objects.filter(submission__problem_id=problem_id)
    
    submission_id = request.query_params.get('submission_id', None)
    order_by = request.query_params.get('order_by', 'test_case__ordinal')
    
    if submission_id:
        results = results.filter(submission_id=submission_id)
    
    if order_by.lstrip('-') in ['test_case__ordinal']:
        results = results.order_by(order_by)
    
    serializer = TestCaseResultSerializer(results, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
