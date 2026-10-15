from .models import Branch


def get_current_branch(request):
    user = request.user
    if not user.is_authenticated:
        return None
    if user.role and user.role.name == "Owner":
        branches = Branch.objects.filter(is_active=True)
        branch_id = request.session.get("branch_id")
        branch = branches.filter(pk=branch_id).first() if branch_id else None
        return branch or branches.first()
    return user.branch