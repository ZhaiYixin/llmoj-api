from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """
    只有教师用户才能访问。
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'is_teacher') and request.user.is_teacher

class WritableIfIsTeacher(BasePermission):
    """
    不限制读操作（GET 请求），
    但是只有教师用户才能进行写操作（非 GET 请求）。
    """
    def has_permission(self, request, view):
        if request.method == 'GET':
            return True
        return hasattr(request.user, 'is_teacher') and request.user.is_teacher