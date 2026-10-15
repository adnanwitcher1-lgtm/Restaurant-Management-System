from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role and request.user.role.name in roles:
                return view(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return deco