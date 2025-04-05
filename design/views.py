from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from accounts.permissions import IsTeacher
from .models import Problem, TestCase, ProblemDesign, ProblemList, ProblemListItem
from .serializers import ProblemSerializer, TestCaseSerializer, ProblemDesignSerializer, ProblemListSerializer, ProblemListItemSerializer

# Create your views here.
class ProblemView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, problem_id=None):
        if problem_id:
            problem = get_object_or_404(Problem, id=problem_id)
            design = ProblemDesign.objects.filter(problem=problem).first()
            data = {
                "problem": ProblemSerializer(problem).data,
                "design": ProblemDesignSerializer(design).data if design else None,
                "testcases": TestCaseSerializer(TestCase.objects.filter(problem=problem).order_by('ordinal'), many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            problems = Problem.objects.filter(models.Q(design__isnull=True) | models.Q(design__is_public=True) | models.Q(design__designer=request.user))

            if 'public' in request.query_params:
                problems = problems.filter(models.Q(design__is_public=True))
            
            if 'private' in request.query_params:
                problems = problems.filter(models.Q(design__is_public=False))
            
            if 'designed_by_me' in request.query_params:
                problems = problems.filter(design__designer=request.user)
            
            search = request.query_params.get('search')
            if search:
                problems = problems.filter(models.Q(title__icontains=search) | models.Q(description__icontains=search))
            
            problems = problems.order_by('-updated_at')

            paginator = PageNumberPagination()
            paginator.page_size_query_param = 'page_size'
            paginator.max_page_size = 100
            paginated_problems = paginator.paginate_queryset(problems, request, view=self)

            data = [
                {
                    "problem": ProblemSerializer(problem).data,
                    "design": ProblemDesignSerializer(
                        ProblemDesign.objects.filter(problem=problem).first()
                    ).data if ProblemDesign.objects.filter(problem=problem).exists() else None,
                    "testcases": TestCaseSerializer(
                        TestCase.objects.filter(problem=problem).order_by('ordinal'), many=True
                    ).data,
                }
                for problem in paginated_problems
            ]

            return paginator.get_paginated_response(data)

    def post(self, request):
        problem = request.data.get('problem')
        design = request.data.get('design')
        testcases_data = request.data.get('testcases')

        if not problem or not design:
            return Response({"error": "Both 'problem' and 'design' fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        problem_serializer = ProblemSerializer(data=problem)
        if not problem_serializer.is_valid():
            return Response({"error": "Invalid problem data.", "details": problem_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        design_serializer = ProblemDesignSerializer(data=design)
        if not design_serializer.is_valid():
            return Response({"error": "Invalid design data.", "details": design_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if testcases_data:
            testcases_serializer = TestCaseSerializer(data=testcases_data, many=True)
            if not testcases_serializer.is_valid():
                return Response({"error": "Invalid test cases data.", "details": testcases_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                problem_instance = problem_serializer.save()
                design_serializer.save(problem=problem_instance, designer=request.user)

                if testcases_data:
                    testcases = [
                        TestCase(problem=problem_instance, ordinal=index, **testcase_data)
                        for index, testcase_data in enumerate(testcases_serializer.validated_data, start=1)
                    ]
                    TestCase.objects.bulk_create(testcases)

        except Exception as e:
            return Response({"error": "An error occurred while creating problem, design, and test cases.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"problem_id": problem_instance.id, "message": "Problem, design, and test cases created successfully."}, status=status.HTTP_201_CREATED)

    def put(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        design = get_object_or_404(ProblemDesign, problem=problem)
        
        problem_data = request.data.get('problem')
        design_data = request.data.get('design')
        testcases_data = request.data.get('testcases')
        
        if design.designer != request.user and not request.user.is_superuser:
            return Response({"error": "You do not have permission to update this problem."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            with transaction.atomic():
                if problem_data:
                    problem_serializer = ProblemSerializer(problem, data=problem_data, partial=True)
                    if not problem_serializer.is_valid():
                        return Response({"error": "Invalid problem data.", "details": problem_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    problem_serializer.save()
                
                if design_data:
                    design_serializer = ProblemDesignSerializer(design, data=design_data, partial=True)
                    if not design_serializer.is_valid():
                        return Response({"error": "Invalid design data.", "details": design_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    design_serializer.save()
                
                if testcases_data:
                    testcases_serializer = TestCaseSerializer(data=testcases_data, many=True)
                    if not testcases_serializer.is_valid():
                        return Response({"error": "Invalid test cases data.", "details": testcases_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    
                    old_testcases = TestCase.objects.filter(problem=problem)
                    old_testcases.delete()
                    new_testcases = [
                        TestCase(problem=problem, ordinal=index, **testcase_data)
                        for index, testcase_data in enumerate(testcases_serializer.validated_data, start=1)
                    ]
                    TestCase.objects.bulk_create(new_testcases)
                
                problem.updated_at = timezone.now()
                problem.save()
            
        except Exception as e:
            return Response({"error": "An error occurred while updating the problem.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({"message": "Problem, design, and test cases updated successfully."}, status=status.HTTP_200_OK)
    
    def delete(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        design = get_object_or_404(ProblemDesign, problem=problem)
        
        if design.designer != request.user and not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this problem."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            with transaction.atomic():
                problem.delete()
        except Exception as e:
            return Response({"error": "An error occurred while deleting the problem.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({"message": "Problem deleted successfully."}, status=status.HTTP_200_OK)


class ProblemListView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, problem_list_id=None):
        if problem_list_id:
            problem_list = get_object_or_404(ProblemList, id=problem_list_id)
            data = {
                "problem_list": ProblemListSerializer(problem_list).data,
                "items": ProblemListItemSerializer(ProblemListItem.objects.filter(problem_list=problem_list).order_by('ordinal'), many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            problem_lists = ProblemList.objects.filter(models.Q(designer__isnull=True) | models.Q(is_public=True) | models.Q(designer=request.user))
            
            if 'public' in request.query_params:
                problem_lists = problem_lists.filter(models.Q(is_public=True))
            
            if 'private' in request.query_params:
                problem_lists = problem_lists.filter(models.Q(is_public=False))
            
            if 'designed_by_me' in request.query_params:
                problem_lists = problem_lists.filter(designer=request.user)
                
            
            search = request.query_params.get('search')
            if search:
                problem_lists = problem_lists.filter(models.Q(title__icontains=search) | models.Q(description__icontains=search))
            
            problem_lists = problem_lists.order_by('-updated_at')

            paginator = PageNumberPagination()
            paginator.page_size_query_param = 'page_size'
            paginator.max_page_size = 100
            paginated_problem_lists = paginator.paginate_queryset(problem_lists, request, view=self)

            data = [
                {
                    "problem_list": ProblemListSerializer(problem_list).data,
                    "items": ProblemListItemSerializer(ProblemListItem.objects.filter(problem_list=problem_list).order_by('ordinal'), many=True).data,
                }
                for problem_list in paginated_problem_lists
            ]

            return paginator.get_paginated_response(data)

    def post(self, request):
        problem_list_data = request.data.get('problem_list')
        items_data = request.data.get('items')

        if not problem_list_data:
            return Response({"error": "Problem list data is required."}, status=status.HTTP_400_BAD_REQUEST)

        problem_list_serializer = ProblemListSerializer(data=problem_list_data)
        if not problem_list_serializer.is_valid():
            return Response({"error": "Invalid problem list data.", "details": problem_list_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                problem_list = problem_list_serializer.save(designer=request.user)

                if items_data:
                    items_serializer = ProblemListItemSerializer(data=items_data, many=True)
                    if not items_serializer.is_valid():
                        return Response({"error": "Invalid problem list items data.", "details": items_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                    items = [
                        ProblemListItem(
                            problem_list=problem_list,
                            ordinal=index,
                            **item_data,
                        )
                        for index, item_data in enumerate(items_data, start=1)
                    ]
                    ProblemListItem.objects.bulk_create(items)

        except Exception as e:
            return Response({"error": "An error occurred while creating the problem list.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"problem_list_id": problem_list.id, "message": "Problem list created successfully."}, status=status.HTTP_201_CREATED)

    def put(self, request, problem_list_id):
        problem_list = get_object_or_404(ProblemList, id=problem_list_id)

        if problem_list.designer != request.user and not request.user.is_superuser:
            return Response({"error": "You do not have permission to update this problem list."}, status=status.HTTP_403_FORBIDDEN)

        problem_list_data = request.data.get('problem_list')
        item_data = request.data.get('items')

        try:
            with transaction.atomic():
                if problem_list_data:
                    problem_list_serializer = ProblemListSerializer(problem_list, data=problem_list_data, partial=True)
                    if not problem_list_serializer.is_valid():
                        return Response({"error": "Invalid problem list data.", "details": problem_list_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    problem_list_serializer.save()

                if item_data:
                    items_serializer = ProblemListItemSerializer(data=item_data, many=True)
                    if not items_serializer.is_valid():
                        return Response({"error": "Invalid problem list items data.", "details": items_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                    old_items = ProblemListItem.objects.filter(problem_list=problem_list)
                    old_items.delete()
                    new_items = [
                        ProblemListItem(
                            problem_list=problem_list,
                            ordinal=index,
                            **item_data,
                        )
                        for index, item_data in enumerate(item_data, start=1)
                    ]
                    ProblemListItem.objects.bulk_create(new_items)

                problem_list.updated_at = timezone.now()
                problem_list.save()

        except Exception as e:
            return Response({"error": "An error occurred while updating the problem list.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Problem list and problems updated successfully."}, status=status.HTTP_200_OK)

    def delete(self, request, problem_list_id):
        problem_list = get_object_or_404(ProblemList, id=problem_list_id)

        if problem_list.designer != request.user and not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this problem list."}, status=status.HTTP_403_FORBIDDEN)

        try:
            with transaction.atomic():
                problem_list.delete()
        except Exception as e:
            return Response({"error": "An error occurred while deleting the problem list.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Problem list deleted successfully."}, status=status.HTTP_200_OK)
