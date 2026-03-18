from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """
    Allows access only to users with the ADMIN role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')


class IsExaminerOrAdmin(permissions.BasePermission):
    """
    Allows access to users with EXAMINER or ADMIN role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['ADMIN', 'EXAMINER'])


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Allows reading for everyone, but creating/updating only for TEACHER role ( Candidates ).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == 'TEACHER')
