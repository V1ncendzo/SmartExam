from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def admin_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is logged in and is an ADMIN.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'ADMIN',
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def examiner_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is logged in and is an EXAMINER or ADMIN.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role in ['ADMIN', 'EXAMINER'],
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def teacher_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is logged in and is a TEACHER (Candidate).
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'TEACHER',
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
