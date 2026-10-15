import io
import json

import qrcode
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.functions import Length
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from branches.utils import get_current_branch
from menu.models import Category, MenuItem

from . import services
from .forms import TableForm
from .models import Order, Table

ORDER_ROLES = ("Owner", "Manager", "Waiter")
TABLE_ROLES = ("Owner", "Manager")
MAX_PENDING_CUSTOMER_ORDERS = 3


def _require_branch(request):
    branch = get_current_branch(request)
    if branch is None:
        raise Http404("No branch selected.")
    return branch


def _role(request):
    return request.user.role.name if request.user.role else ""


def _error(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def _json_body(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        raise services.OrderError("Invalid request.")
    if not isinstance(data, dict):
        raise services.OrderError("Invalid request.")
    return data
def _occupied_table_ids(branch):
    busy = Order.objects.filter(branch=branch, table__isnull=False).filter(
        Q(status__in=Order.ACTIVE_STATUSES)
        | (Q(status=Order.SERVED) & (Q(bill__isnull=True) | Q(bill__paid_at__isnull=True)))
    )
    return set(busy.values_list("table_id", flat=True))

def _menu_context(branch):
    categories = Category.objects.filter(branch=branch, is_active=True)
    items = MenuItem.objects.filter(branch=branch, is_available=True, category__is_active=True)
    return {
        "categories": categories,
        "menu": [
            {
                "id": item.pk,
                "name": item.name,
                "price": float(item.price),
                "category": item.category_id,
                "image": item.image.url if item.image else "",
            }
            for item in items
        ],
    }


def _can_touch(request, order):
    """Waiters may only work on their own orders and on customer (QR) orders."""
    if _role(request) == "Waiter":
        return order.waiter_id in (None, request.user.pk)
    return True


# ---------- Waiter screen and order creation ----------

@role_required(*ORDER_ROLES)
def waiter(request):
    branch = get_current_branch(request)
    context = {"branch": branch, "mode": "new", "submit_url": reverse("orders:create")}
    if branch:
        context.update(_menu_context(branch))

        add_order = None
        add_to = request.GET.get("add_to", "")
        if add_to.isdigit():
            add_order = (
                Order.objects.filter(
                    pk=int(add_to), branch=branch, status__in=(Order.PENDING, Order.PREPARING)
                )
                .select_related("table")
                .first()
            )
            if add_order and not _can_touch(request, add_order):
                add_order = None
        if add_order:
            context.update(
                {
                    "mode": "add",
                    "add_order": add_order,
                    "submit_url": reverse("orders:add_items", args=[add_order.pk]),
                }
            )
        else:
            occupied = _occupied_table_ids(branch)
            tables = list(
                Table.objects.filter(branch=branch, is_active=True).order_by(Length("name"), "name")
            )
            for table in tables:
                table.occupied = table.pk in occupied
            context["tables"] = tables
    return render(request, "orders/waiter.html", context)


@require_POST
@role_required(*ORDER_ROLES)
def order_create(request):
    branch = _require_branch(request)
    try:
        data = _json_body(request)
        order_type = data.get("order_type")
        if order_type not in (Order.DINE_IN, Order.TAKEAWAY):
            raise services.OrderError("Please choose dine-in or takeaway.")

        table = None
        if order_type == Order.DINE_IN:
            try:
                table_id = int(data.get("table") or 0)
            except (TypeError, ValueError):
                raise services.OrderError("Please choose a table.")
            table = Table.objects.filter(pk=table_id, branch=branch, is_active=True).first()
            if table is None:
                raise services.OrderError("Please choose a table.")
            if table.pk in _occupied_table_ids(branch):
                raise services.OrderError("This table already has an open order. Use + Add items on that order.")

        lines = services.parse_items(branch, data.get("items"))
        order = services.create_order(branch, table, order_type, request.user, lines, str(data.get("note", ""))[:300].strip())
    except services.OrderError as exc:
        return _error(str(exc))
    messages.success(request, f"Order #{order.pk} sent to the kitchen.")
    return JsonResponse({"ok": True, "order_id": order.pk})


@require_POST
@role_required(*ORDER_ROLES)
def order_add_items(request, pk):
    branch = _require_branch(request)
    order = get_object_or_404(Order, pk=pk, branch=branch)
    if not _can_touch(request, order):
        raise PermissionDenied
    try:
        data = _json_body(request)
        lines = services.parse_items(branch, data.get("items"))
        services.add_items_to_order(order, lines)
    except services.OrderError as exc:
        return _error(str(exc))
    messages.success(request, f"Items added to order #{order.pk}.")
    return JsonResponse({"ok": True, "order_id": order.pk})


# ---------- Customer ordering (public, opened from the table QR code) ----------

def _customer_table(pk):
    return get_object_or_404(
        Table.objects.select_related("branch"), pk=pk, is_active=True, branch__is_active=True
    )


def customer_menu(request, pk):
    table = _customer_table(pk)
    context = {
        "mode": "customer",
        "branch": table.branch,
        "table": table,
        "submit_url": reverse("customer_submit", args=[table.pk]),
    }
    context.update(_menu_context(table.branch))
    return render(request, "orders/waiter.html", context)


@require_POST
def customer_order_create(request, pk):
    table = _customer_table(pk)
    waiting = Order.objects.filter(
        table=table, waiter__isnull=True, status=Order.PENDING
    ).count()
    if waiting >= MAX_PENDING_CUSTOMER_ORDERS:
        return _error("Your earlier orders are still waiting. Please call the waiter.")
    try:
        data = _json_body(request)
        lines = services.parse_items(table.branch, data.get("items"))
        order = services.create_order(table.branch, table, Order.DINE_IN, None, lines, str(data.get("note", ""))[:300].strip())
    except services.OrderError as exc:
        return _error(str(exc))
    return JsonResponse({"ok": True, "order_id": order.pk})


# ---------- Orders list and status changes ----------

@role_required(*ORDER_ROLES)
def order_list(request):
    branch = get_current_branch(request)
    tab = "done" if request.GET.get("tab") == "done" else "active"
    context = {"branch": branch, "tab": tab, "orders": []}
    if branch:
        orders = (
            Order.objects.filter(branch=branch)
            .select_related("table", "waiter")
            .prefetch_related("items")
        )
        role = _role(request)
        if role == "Waiter":
            orders = orders.filter(Q(waiter=request.user) | Q(waiter__isnull=True))
        if tab == "active":
            orders = orders.filter(status__in=Order.ACTIVE_STATUSES)
        else:
            orders = orders.filter(
                status__in=Order.DONE_STATUSES, created_at__date=timezone.localdate()
            )
        orders = list(orders[:100])
        for order in orders:
            order.actions = order.actions_for(role)
            order.can_add = order.status in (Order.PENDING, Order.PREPARING)
        context["orders"] = orders
    return render(request, "orders/order_list.html", context)


@require_POST
@role_required(*ORDER_ROLES)
def order_set_status(request, pk):
    branch = _require_branch(request)
    order = get_object_or_404(Order, pk=pk, branch=branch)
    if not _can_touch(request, order):
        raise PermissionDenied
    role = _role(request)
    new_status = request.POST.get("status")
    if new_status not in {status for status, _ in order.actions_for(role)}:
        messages.error(request, "That action is not available for this order.")
    else:
        try:
            services.change_status(order, new_status)
            messages.success(
                request, f"Order #{order.pk} is now {order.get_status_display().lower()}."
            )
        except services.OrderError as exc:
            messages.error(request, str(exc))
    return redirect("orders:list")


# ---------- Tables (Owner and Manager) ----------

def _table_modal(request, form):
    html = render_to_string("orders/form_modal.html", {"form": form}, request=request)
    return HttpResponse(html, status=400 if request.method == "POST" else 200)


@role_required(*TABLE_ROLES)
def table_list(request):
    branch = get_current_branch(request)
    tables = []
    if branch:
        tables = Table.objects.filter(branch=branch).order_by(Length("name"), "name")
    return render(request, "orders/table_list.html", {"branch": branch, "tables": tables})


@role_required(*TABLE_ROLES)
def table_add(request):
    branch = _require_branch(request)
    form = TableForm(request.POST or None, branch=branch)
    if request.method == "POST" and form.is_valid():
        table = form.save(commit=False)
        table.branch = branch
        table.save()
        messages.success(request, "Table created successfully.")
        return JsonResponse({"ok": True})
    return _table_modal(request, form)


@role_required(*TABLE_ROLES)
def table_edit(request, pk):
    branch = _require_branch(request)
    table = get_object_or_404(Table, pk=pk, branch=branch)
    form = TableForm(request.POST or None, instance=table, branch=branch)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Table updated successfully.")
        return JsonResponse({"ok": True})
    return _table_modal(request, form)


@require_POST
@role_required(*TABLE_ROLES)
def table_toggle(request, pk):
    branch = _require_branch(request)
    table = get_object_or_404(Table, pk=pk, branch=branch)
    table.is_active = not table.is_active
    table.save(update_fields=["is_active"])
    state = "activated" if table.is_active else "deactivated"
    messages.success(request, f"Table {table.name} has been {state}.")
    return redirect("orders:table_list")


@role_required(*TABLE_ROLES)
def table_qr_sheet(request):
    branch = get_current_branch(request)
    tables = []
    if branch:
        tables = Table.objects.filter(branch=branch, is_active=True).order_by(
            Length("name"), "name"
        )
    return render(request, "orders/qr_sheet.html", {"branch": branch, "tables": tables})


@role_required(*TABLE_ROLES)
def table_qr_image(request, pk):
    branch = _require_branch(request)
    table = get_object_or_404(Table, pk=pk, branch=branch)
    url = request.build_absolute_uri(reverse("customer_order", args=[table.pk]))
    buffer = io.BytesIO()
    qrcode.make(url).save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")