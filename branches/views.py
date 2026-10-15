from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required

from .forms import BranchForm
from .models import Branch


def _handle_form(request, form, success_message):
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, success_message)
        return JsonResponse({"ok": True})
    html = render_to_string("branches/branch_form_modal.html", {"form": form}, request=request)
    return HttpResponse(html, status=400 if request.method == "POST" else 200)


@role_required("Owner")
def branch_list(request):
    branches = Branch.objects.order_by("name")
    return render(request, "branches/branch_list.html", {"branches": branches})


@role_required("Owner")
def branch_add(request):
    form = BranchForm(request.POST or None)
    return _handle_form(request, form, "Branch created successfully.")


@role_required("Owner")
def branch_edit(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    form = BranchForm(request.POST or None, instance=branch)
    return _handle_form(request, form, "Branch updated successfully.")


@require_POST
@role_required("Owner")
def branch_toggle(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    branch.is_active = not branch.is_active
    branch.save(update_fields=["is_active"])
    state = "activate" if branch.is_active else "deactivate"
    messages.success(request, f"{branch.name} has been {state}d.")
    return redirect("branches:list")


@require_POST
@role_required("Owner")
def branch_switch(request):
    branch = Branch.objects.filter(pk=request.POST.get("branch"), is_active=True).first()
    if branch:
        request.session["branch_id"] = branch.pk
    next_url = request.META.get("HTTP_REFERER", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    return redirect(next_url)