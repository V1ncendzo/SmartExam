from django.contrib.auth.mixins import AccessMixin

class AdminRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated and has the ADMIN role."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'ADMIN':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class ExaminerRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated and is an EXAMINER or ADMIN."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['ADMIN', 'EXAMINER']:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class TeacherRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated and has the TEACHER (Candidate) role."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'TEACHER':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
