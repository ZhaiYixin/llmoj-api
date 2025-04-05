from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """
    只有教师用户才能访问。
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'is_teacher') and request.user.is_teacher
