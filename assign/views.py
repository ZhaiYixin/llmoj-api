from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ClassGroup, ClassMember, Assignment, AssignmentPdf, Homework
from .serializers import ClassGroupSerializer, ClassMemberSerializer, AssignmentSerializer, AssignmentPdfSerializer, HomeworkSerializer
from judge.models import Submission
from design.models import ProblemListItem
from chat.models import ConversationTemplate, Conversation

# Create your views here.
class ClassGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_group_id=None):
        if class_group_id:
            class_group = get_object_or_404(ClassGroup, id=class_group_id)
            data = {
                "class_group": ClassGroupSerializer(class_group).data,
                "students": ClassMemberSerializer(class_group.members.all(), many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            class_groups = ClassGroup.objects.filter(teacher=request.user)
            class_groups = class_groups.order_by('-created_at')
            data = [
                {
                    "class_group": ClassGroupSerializer(class_group).data,
                    "students_count": class_group.members.count(),
                }
                for class_group in class_groups
            ]
            return Response(data, status=status.HTTP_200_OK)


class AssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id=None):
        if assignment_id:
            assignment = get_object_or_404(Assignment, id=assignment_id)
            data = {
                "assignment": AssignmentSerializer(assignment).data,
                "homeworks": HomeworkSerializer(assignment.homeworks.all(), many=True).data,
                "pdfs": AssignmentPdfSerializer(assignment.pdfs.all(), many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            assignments = Assignment.objects.filter(class_group__teacher=request.user).order_by('-created_at')
            
            if request.query_params.get('class_group_id'):
                assignments = assignments.filter(class_group_id=request.query_params.get('class_group_id'))
            
            data = [
                {
                    "assignment": AssignmentSerializer(assignment).data,
                    "homeworks_count": assignment.homeworks.count(),
                    "completed_count": assignment.homeworks.filter(done_count=models.F('todo_count')).count(),
                }
                for assignment in assignments
            ]
            return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                assignment = serializer.save()
                pdf_ids = request.data.get('pdfs', [])
                for pdf_id in pdf_ids:
                    AssignmentPdf.objects.create(assignment=assignment, pdf_id=pdf_id)
            return Response(AssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        serializer = AssignmentSerializer(assignment, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                assignment = serializer.save()
                pdf_ids = request.data.get('pdfs', [])
                if pdf_ids:
                    AssignmentPdf.objects.filter(assignment=assignment).delete()
                    for pdf_id in pdf_ids:
                        AssignmentPdf.objects.create(assignment=assignment, pdf_id=pdf_id)
            return Response(AssignmentSerializer(assignment).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# AssignmentView负责教师端，HomeworkView则负责学生端
class HomeworkView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id=None):
        if assignment_id:
            assignment = get_object_or_404(Assignment, id=assignment_id)
            class_member = get_object_or_404(ClassMember, class_group=assignment.class_group, student=request.user)
            try:
                homework = Homework.objects.get(assignment=assignment, class_member=class_member)
            except Homework.DoesNotExist:
                homework = None
                       
            data = {
                "assignment": AssignmentSerializer(assignment).data,
                "homework": HomeworkSerializer(homework).data if homework else None,
                "pdfs": AssignmentPdfSerializer(assignment.pdfs.all(), many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            assignments = Assignment.objects.filter(class_group__members__student=request.user).prefetch_related('homeworks').order_by('-created_at')
            
            if request.query_params.get('class_group_id'):
                assignments = assignments.filter(class_group_id=request.query_params.get('class_group_id'))
            
            homeworks = Homework.objects.filter(assignment__in=assignments, class_member__student=request.user).select_related('assignment')
            homework_map = {hw.assignment_id: hw for hw in homeworks}
            
            data = [
                {
                    "assignment": AssignmentSerializer(assignment).data,
                    "homework": HomeworkSerializer(homework_map.get(assignment.id)).data if homework_map.get(assignment.id) else None,
                    "pdfs": AssignmentPdfSerializer(assignment.pdfs.all(), many=True).data,
                }
                for assignment in assignments
            ]
            
            return Response(data, status=status.HTTP_200_OK)
        
    def post(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        class_member = get_object_or_404(ClassMember, class_group=assignment.class_group, student=request.user)
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({"error": "Submission ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        problem_list_item_id = request.data.get('problem_list_item_id')
        if not problem_list_item_id:
            return Response({"error": "Problem List Item ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        problem_list_item = get_object_or_404(ProblemListItem, id=problem_list_item_id, problem_list=assignment.problem_list)
        submission = get_object_or_404(Submission, id=submission_id, user=request.user, problem=problem_list_item.problem)

        try:
            with transaction.atomic():
                homework, _ = Homework.objects.get_or_create(assignment=assignment, class_member=class_member)
                homework.update_problems(problem_list_item_id, submission)
                homework.save()
        
        except Exception as e:
            return Response({"error": "Failed to create homework submission", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(HomeworkSerializer(homework).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_conversation(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    class_member = get_object_or_404(ClassMember, class_group=assignment.class_group, student=request.user)
    conversation_id = request.data.get('conversation_id')
    if not conversation_id:
        return Response({"error": "Conversation ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    conversation = get_object_or_404(Conversation, id=conversation_id, user=class_member.student, template=assignment.conversation_template)
    
    try:
        with transaction.atomic():
            homework, _ = Homework.objects.get_or_create(assignment=assignment, class_member=class_member)
            homework.conversation = conversation
            homework.save()
    
    except Exception as e:
        return Response({"error": "Failed to start conversation", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(HomeworkSerializer(homework).data, status=status.HTTP_201_CREATED)
