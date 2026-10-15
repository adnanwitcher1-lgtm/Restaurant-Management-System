from .models import Branch
from .utils import get_current_branch


def current_branch(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    data = {"current_branch": get_current_branch(request)}
    if user.role and user.role.name == "Owner":
        data["nav_branches"] = Branch.objects.filter(is_active=True)
    return data