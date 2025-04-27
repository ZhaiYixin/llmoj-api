import os

from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from openai import OpenAI

from .models import Problem, ProblemConversation, ProblemMessage, TestCase, Submission, TestCaseResult
from .serializers import ProblemSerializer, TestCaseSerializer, SubmissionSerializer, TestCaseResultSerializer
from .JudgeServer.client.Python.client import JudgeServerClient
from .JudgeServer.client.Python.languages import c_lang_config, cpp_lang_config, java_lang_config, c_lang_spj_config, c_lang_spj_compile, py2_lang_config, py3_lang_config, go_lang_config, php_lang_config, js_lang_config
from chat.models import Conversation, Message

# Load environment variables from .env file
load_dotenv(override=True)
CLIENT = JudgeServerClient(token=os.getenv("JUDGE_SERVER_TOKEN"), server_base_url=os.getenv("JUDGE_SERVER_BASE_URL"))
LLM_CLIENT = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
MODEL = os.getenv("MODEL")

with open(os.path.join(os.path.dirname(__file__), './prompts/answer.txt'), 'r', encoding='utf-8') as file:
    PROMPT_ANSWER = file.read()
    PROMPT_ANSWER_TOKENS = Message.count_tokens(PROMPT_ANSWER)

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


class ProblemAskQuestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, problem_id):
        MAX_QUESTION_LENGTH = 1024
        
        problem = get_object_or_404(Problem, id=problem_id)
        
        data = request.data
        user_content = data.get("content")
        if not user_content:
            return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)
        tokens = Message.count_tokens(user_content)
        if tokens > MAX_QUESTION_LENGTH:
            return Response({"error": "Content exceeds maximum length"}, status=status.HTTP_400_BAD_REQUEST)
        src = data.get("src")
        lang = data.get("lang")
        if not src or not lang:
            return Response({"error": "Source code and language are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            problem_conversation = ProblemConversation.get_or_create_conversation(problem_id=problem_id, user=request.user)
            problem_messages = ProblemMessage.objects.filter(problem_conversation=problem_conversation).order_by('-message__created_at')
            problem_questions = problem_messages.filter(message__role='user')
            last_question = problem_questions.first()
            start_question = None
            if last_question and last_question.src == src:
                start_question = last_question
            if last_question and last_question.start_question and last_question.start_question.src == src:
                start_question = last_question.start_question
            last_submission = Submission.objects.filter(user=request.user, problem=problem).order_by('-created_at').first()
            relevant_submission = None
            if last_submission and last_submission.src == src:
                if start_question:
                    start_question.relevant_submission = last_submission
                    start_question.save()
                else:
                    relevant_submission = last_submission
            ProblemMessage.create_message(
                problem_conversation=problem_conversation,
                role='user',
                content=user_content,
                tokens=tokens,
                src=None if start_question else src,
                lang=None if start_question else lang,
                relevant_submission= relevant_submission,
                start_question=start_question
            )
            return Response({"status": "Message added successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProblemGetAnswerView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id):
        CONTEXT_WINDOW = 8192
        RESERVED_ANSWER_LENGTH = 1024
        
        problem = get_object_or_404(Problem, id=problem_id)
        problem_conversation = get_object_or_404(ProblemConversation, problem=problem, conversation__user=request.user)
        last_problem_message = ProblemMessage.objects.filter(problem_conversation=problem_conversation).order_by('-message__created_at').first()
        if not last_problem_message:
            return Response({"error": "No messages found for this problem conversation"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            messages = self._get_context(problem_conversation, CONTEXT_WINDOW - RESERVED_ANSWER_LENGTH)
            response = LLM_CLIENT.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True
            )

            def stream_response():
                chunks = []
                for chunk in response:
                    chunks.append(chunk)
                    yield chunk.choices[0].delta.content

                assistant_content = "".join([chunk.choices[0].delta.content for chunk in chunks])
                last_chunk = chunks[-1]
                usage = last_chunk.usage
                ProblemMessage.create_message(
                    problem_conversation=problem_conversation,
                    role='assistant',
                    content=assistant_content,
                    tokens=usage.completion_tokens
                )

            return StreamingHttpResponse(stream_response(), content_type='text/plain')
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def _get_context(problem_conversation, available_tokens):
        # system prompt
        available_tokens -= PROMPT_ANSWER_TOKENS
        if available_tokens < 0:
            raise ValueError("Not enough tokens available for system prompt")
        system_prompt = [{"role": "system", "content": PROMPT_ANSWER}]
        
        # 问题描述
        problem = problem_conversation.problem
        problem_description = f"我正在做着`{problem.title}`这道编程题，题目描述如下：\n" + f'```\n{problem.description}\n```\n'
        problem_description_tokens = Message.count_tokens(problem_description)
        available_tokens -= problem_description_tokens
        if available_tokens < 0:
            raise ValueError("Not enough tokens available for problem description")
        problem_prompt = [{"role": "user", "content": problem_description}]
        
        # 提问，及其代码和结果（如果有）
        message_prompts = []
        problem_messages = ProblemMessage.objects.filter(problem_conversation=problem_conversation).order_by('-message__created_at')
        for m in problem_messages:
            message_prompt = []
            if m.message.role == "assistant":
                available_tokens -= m.message.tokens
                if available_tokens < 0:
                    break
                else:
                    message_prompt.append({"role": m.message.role, "content": m.message.content})
            elif m.message.role == "user":
                # 提问
                available_tokens -= m.message.tokens
                if available_tokens < 0:
                    break
                question_prompt = [{"role": m.message.role, "content": m.message.content}]
                
                # 代码（如果有）
                code_prompt = []
                if m.lang and m.src:
                    current_code = f"我现在的代码如下：\n" + f'```{ProblemGetAnswerView._get_lang_name(m.lang)}\n{m.src}\n```\n'
                    current_code_tokens = Message.count_tokens(current_code)
                    available_tokens -= current_code_tokens
                    if available_tokens >= 0:
                        code_prompt.append({"role": "user", "content": current_code})
                
                # 运行结果（如果有）
                result_prompt = []
                if m.relevant_submission:
                    submission = m.relevant_submission
                    if submission.err:
                        current_result = f"但是编译失败了，错误信息：\n" + f'```\n{submission.error_reason}\n```\n'
                    elif submission.success_count < submission.total_count:
                        current_result = f"但是有{submission.total_count - submission.success_count}个测试用例没有通过。\n"
                        testcase_results = TestCaseResult.objects.filter(submission=submission).exclude(result=TestCaseResult.ResultCode.SUCCESS).order_by('test_case__ordinal')
                        for result in testcase_results:
                            if result.result == TestCaseResult.ResultCode.WRONG_ANSWER:
                                current_result += f"\n## 测试用例{result.test_case.ordinal}的实际输出与预期不符\n" + "输入：\n" + f"```\n{result.test_case.input}\n```\n" + "预期输出：\n" + f"```\n{result.test_case.output}\n```\n" + "实际输出：\n" + f"```\n{result.output}\n```\n"
                            else:
                                data = TestCaseResultSerializer(result).data
                                current_result += f"\n## 测试用例{result.test_case.ordinal}运行出错\n" + "输入：\n" + f"```\n{result.test_case.input}\n```\n" + f"出现错误：`{data['status']}`\n" + "错误信息：\n" + f"```\n{data['message']}\n```\n"
                    else:
                        current_result = f"运行成功，并且所有的测试用例都通过了。"
                    current_result_tokens = Message.count_tokens(current_result)
                    available_tokens -= current_result_tokens
                    if available_tokens >= 0:
                        result_prompt.append({"role": "user", "content": current_result})
                message_prompt = code_prompt + result_prompt + question_prompt
            else:
                pass
            message_prompts += message_prompt[::-1]
        if len(message_prompts) == 0:
            raise ValueError("Not enough tokens available for question")
        
        return system_prompt + problem_prompt + message_prompts[::-1]

    @staticmethod
    def _get_lang_name(lang):
        lang_dict = {
            "C": "c",
            "C++": "cpp",
            "Java": "java",
            "Python2": "python",
            "Python3": "python",
            "Go": "go",
            "PHP": "php",
            "JavaScript": "javascript",
        }
        return lang_dict.get(lang, "")

