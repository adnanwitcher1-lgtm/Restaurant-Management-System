from django.contrib import messages
from django.db.models import Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from branches.utils import get_current_branch

from .forms import CategoryForm, MenuItemForm
from .models import Category, MenuItem

MENU_ROLES = ("Owner", "Manager")


def _require_branch(request):
    branch = get_current_branch(request)
    if branch is None:
        raise Http404("No branch selected.")
    return branch


def _handle_form(request, form, success_message):
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.branch = form.branch
        obj.save()
        messages.success(request, success_message)
        return JsonResponse({"ok": True})
    html = render_to_string("menu/form_modal.html", {"form": form}, request=request)
    return HttpResponse(html, status=400 if request.method == "POST" else 200)


@role_required(*MENU_ROLES)
def menu_list(request):
    branch = get_current_branch(request)
    context = {"branch": branch, "categories": [], "items": [], "selected_id": None}
    if branch:
        categories = Category.objects.filter(branch=branch).annotate(item_count=Count("items"))
        items = MenuItem.objects.filter(branch=branch).select_related("category")
        selected = request.GET.get("category", "")
        selected_id = int(selected) if selected.isdigit() else None
        if selected_id:
            items = items.filter(category_id=selected_id)
        context.update(
            {
                "categories": categories,
                "items": items,
                "selected_id": selected_id,
                "has_active_category": categories.filter(is_active=True).exists(),
            }
        )
    return render(request, "menu/menu_list.html", context)


# ---------- Categories ----------

@role_required(*MENU_ROLES)
def category_add(request):
    branch = _require_branch(request)
    form = CategoryForm(request.POST or None, request.FILES or None, branch=branch)
    return _handle_form(request, form, "Category created successfully.")


@role_required(*MENU_ROLES)
def category_edit(request, pk):
    branch = _require_branch(request)
    category = get_object_or_404(Category, pk=pk, branch=branch)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category, branch=branch)
    return _handle_form(request, form, "Category updated successfully.")


@require_POST
@role_required(*MENU_ROLES)
def category_toggle(request, pk):
    branch = _require_branch(request)
    category = get_object_or_404(Category, pk=pk, branch=branch)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])
    state = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category {category.name} has been {state}.")
    return redirect("menu:list")


# ---------- Items ----------

@role_required(*MENU_ROLES)
def item_add(request):
    branch = _require_branch(request)
    form = MenuItemForm(request.POST or None, request.FILES or None, branch=branch)
    return _handle_form(request, form, "Menu item created successfully.")


@role_required(*MENU_ROLES)
def item_edit(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(MenuItem, pk=pk, branch=branch)
    form = MenuItemForm(request.POST or None, request.FILES or None, instance=item, branch=branch)
    return _handle_form(request, form, "Menu item updated successfully.")


@require_POST
@role_required(*MENU_ROLES)
def item_toggle(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(MenuItem, pk=pk, branch=branch)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    state = "available" if item.is_available else "unavailable"
    messages.success(request, f"{item.name} is now marked as {state}.")
    return redirect("menu:list")