from django.shortcuts import render

# Create your views here.
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from branches.utils import get_current_branch

from .forms import InventoryItemForm, StockAdjustForm
from .models import InventoryItem, StockMovement

INVENTORY_ROLES = ("Owner", "Manager")


def _require_branch(request):
    branch = get_current_branch(request)
    if branch is None:
        raise Http404("No branch selected.")
    return branch


def _render_modal(request, form):
    html = render_to_string("inventory/form_modal.html", {"form": form}, request=request)
    return HttpResponse(html, status=400 if request.method == "POST" else 200)


@role_required(*INVENTORY_ROLES)
def inventory_list(request):
    branch = get_current_branch(request)
    context = {"branch": branch, "items": [], "low_only": False, "low_count": 0}
    if branch:
        all_items = InventoryItem.objects.filter(branch=branch)
        low_items = all_items.filter(is_active=True, quantity__lte=F("low_stock_level"))
        low_only = request.GET.get("low") == "1"
        context.update(
            {
                "items": low_items if low_only else all_items,
                "low_only": low_only,
                "low_count": low_items.count(),
            }
        )
    return render(request, "inventory/inventory_list.html", context)


@role_required(*INVENTORY_ROLES)
def inventory_add(request):
    branch = _require_branch(request)
    form = InventoryItemForm(request.POST or None, branch=branch)
    if request.method == "POST" and form.is_valid():
        opening = form.cleaned_data.get("opening_quantity") or Decimal("0")
        with transaction.atomic():
            item = form.save(commit=False)
            item.branch = branch
            item.quantity = opening
            item.save()
            if opening > 0:
                StockMovement.objects.create(
                    item=item,
                    movement_type=StockMovement.IN,
                    quantity=opening,
                    note="Opening stock",
                    created_by=request.user,
                )
        messages.success(request, "Inventory item created successfully.")
        return JsonResponse({"ok": True})
    return _render_modal(request, form)


@role_required(*INVENTORY_ROLES)
def inventory_edit(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(InventoryItem, pk=pk, branch=branch)
    form = InventoryItemForm(request.POST or None, instance=item, branch=branch)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Inventory item updated successfully.")
        return JsonResponse({"ok": True})
    return _render_modal(request, form)


@role_required(*INVENTORY_ROLES)
def inventory_adjust(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(InventoryItem, pk=pk, branch=branch)
    form = StockAdjustForm(request.POST or None, item=item)
    if request.method == "POST" and form.is_valid():
        if form.apply(request.user):
            messages.success(request, f"Stock updated for {item.name}.")
            return JsonResponse({"ok": True})
    return _render_modal(request, form)


@require_POST
@role_required(*INVENTORY_ROLES)
def inventory_toggle(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(InventoryItem, pk=pk, branch=branch)
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    state = "activated" if item.is_active else "deactivated"
    messages.success(request, f"{item.name} has been {state}.")
    return redirect("inventory:list")


@role_required(*INVENTORY_ROLES)
def inventory_history(request, pk):
    branch = _require_branch(request)
    item = get_object_or_404(InventoryItem, pk=pk, branch=branch)
    movements = item.movements.select_related("created_by")[:100]
    return render(
        request, "inventory/history.html", {"item": item, "movements": movements}
    )