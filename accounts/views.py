from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from branches.utils import get_current_branch

from .decorators import role_required
from .forms import StaffForm
from .models import User

ROLE_HOME = {
    "Owner": "analytics:dashboard",
    "Manager": "analytics:dashboard",
    "Cashier": "billing:cashier",
    "Waiter": "orders:waiter",
    "Kitchen": "kitchen:display",
}


@login_required
def role_redirect(request):
    role = request.user.role
    if role and role.name in ROLE_HOME:
        return redirect(ROLE_HOME[role.name])
    raise PermissionDenied


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _is_owner(user):
    return bool(user.role and user.role.name == "Owner")


def _staff_queryset(request):
    """Staff of the currently selected branch only.

    Owners also see users who have no branch (for example other Owners), so nobody gets lost.
    Managers see only staff of their own branch, never Owners.
    """
    qs = User.objects.select_related("role", "branch")
    branch = get_current_branch(request)
    if _is_owner(request.user):
        if branch is None:
            return qs
        return qs.filter(Q(branch=branch) | Q(branch__isnull=True))
    if branch is None:
        return qs.none()
    return qs.filter(branch=branch).exclude(role__name="Owner")


def _handle_staff_form(request, form, title, success_message, edited_user=None):
    if request.method == "POST" and form.is_valid():
        form.save()
        if edited_user is not None and edited_user == request.user:
            update_session_auth_hash(request, edited_user)
        messages.success(request, success_message)
        if _is_ajax(request):
            return JsonResponse({"ok": True})
        return redirect("accounts:staff_list")
    if _is_ajax(request):
        html = render_to_string(
            "accounts/staff_form_modal.html", {"form": form}, request=request
        )
        return HttpResponse(html, status=400 if request.method == "POST" else 200)
    return render(request, "accounts/staff_form.html", {"form": form, "title": title})


@role_required("Owner", "Manager")
def staff_list(request):
    users = _staff_queryset(request).order_by("username")
    return render(
        request,
        "accounts/staff_list.html",
        {"users": users, "branch": get_current_branch(request)},
    )


@role_required("Owner", "Manager")
def staff_add(request):
    branch = get_current_branch(request)
    initial = {"branch": branch.pk} if branch else {}
    form = StaffForm(request.POST or None, requester=request.user, initial=initial)
    return _handle_staff_form(request, form, "Add Staff", "Staff member created successfully.")


@role_required("Owner", "Manager")
def staff_edit(request, pk):
    staff_user = get_object_or_404(_staff_queryset(request), pk=pk)
    form = StaffForm(request.POST or None, instance=staff_user, requester=request.user)
    return _handle_staff_form(
        request, form, "Edit Staff", "Staff member updated successfully.", edited_user=staff_user
    )


@require_POST
@role_required("Owner", "Manager")
def staff_toggle(request, pk):
    staff_user = get_object_or_404(_staff_queryset(request), pk=pk)
    if staff_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        staff_user.is_active = not staff_user.is_active
        staff_user.save(update_fields=["is_active"])
        state = "activate" if staff_user.is_active else "deactivate"
        messages.success(request, f"{staff_user.username} has been {state}d.")
    return redirect("accounts:staff_list")