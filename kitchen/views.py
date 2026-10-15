from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from branches.utils import get_current_branch
from orders import services
from orders.models import Order

KITCHEN_ROLES = ("Owner", "Manager", "Kitchen")

# column key, title, status shown, next status, button label
COLUMNS = [
    ("new", "New", Order.PENDING, Order.PREPARING, "Start preparing"),
    ("preparing", "Preparing", Order.PREPARING, Order.READY, "Mark ready"),
    ("ready", "Ready", Order.READY, Order.SERVED, "Mark served"),
]


def _columns(branch):
    orders = list(
        Order.objects.filter(branch=branch, status__in=Order.ACTIVE_STATUSES)
        .select_related("table")
        .prefetch_related("items")
        .order_by("created_at", "id")
    )
    return [
        {
            "key": key,
            "title": title,
            "orders": [o for o in orders if o.status == status],
            "next": nxt,
            "button": button,
        }
        for key, title, status, nxt, button in COLUMNS
    ]


@role_required(*KITCHEN_ROLES)
def display(request):
    branch = get_current_branch(request)
    context = {"branch": branch}
    if branch:
        context["columns"] = _columns(branch)
    return render(request, "kitchen/display.html", context)


@role_required(*KITCHEN_ROLES)
def cards(request):
    branch = get_current_branch(request)
    columns = _columns(branch) if branch else []
    return render(request, "kitchen/_columns.html", {"columns": columns})


@require_POST
@role_required(*KITCHEN_ROLES)
def set_status(request, pk):
    branch = get_current_branch(request)
    order = get_object_or_404(Order, pk=pk, branch=branch)
    allowed = {Order.PENDING: Order.PREPARING, Order.PREPARING: Order.READY, Order.READY: Order.SERVED}
    if request.POST.get("status") != allowed.get(order.status):
        return JsonResponse({"ok": False, "error": "Not allowed."}, status=400)
    try:
        services.change_status(order, request.POST["status"])
    except services.OrderError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True})
