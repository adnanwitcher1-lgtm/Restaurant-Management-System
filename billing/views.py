from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from branches.utils import get_current_branch
from orders.models import Order

from .models import Bill, Payment

BILLING_ROLES = ("Owner", "Manager", "Cashier", "Waiter")
CENT = Decimal("0.01")


def _decimal(value):
    try:
        return Decimal(value or "0").quantize(CENT)
    except InvalidOperation:
        raise ValueError("Enter valid numbers.")


@role_required(*BILLING_ROLES)
def cashier(request):
    branch = get_current_branch(request)
    tab = "paid" if request.GET.get("tab") == "paid" else "unpaid"
    context = {"branch": branch, "tab": tab, "methods": Payment.METHOD_CHOICES}
    if branch and tab == "paid":
        bills = (
            Bill.objects.filter(branch=branch, paid_at__date=timezone.localdate())
            .select_related("order", "order__table")
            .prefetch_related("payments")
        )
        context["bills"] = bills
        context["today_total"] = bills.aggregate(t=Sum("total"))["t"] or 0
    elif branch:
        context["orders"] = (
            Order.objects.filter(branch=branch, status=Order.SERVED)
            .filter(Q(bill__isnull=True) | Q(bill__paid_at__isnull=True))
            .select_related("table", "bill")
            .prefetch_related("items", "bill__payments")
            .order_by("created_at", "id")
        )
    return render(request, "billing/cashier.html", context)


@require_POST
@role_required(*BILLING_ROLES)
def pay(request, pk):
    branch = get_current_branch(request)
    order = get_object_or_404(Order, pk=pk, branch=branch, status=Order.SERVED)
    try:
        method = request.POST.get("method")
        if method not in dict(Payment.METHOD_CHOICES):
            raise ValueError("Choose a payment method.")
        raw_amount = (request.POST.get("amount") or "").strip()

        with transaction.atomic():
            bill = Bill.objects.select_for_update().filter(order=order).first()
            if bill is None:
                subtotal = order.total.quantize(CENT)
                discount = _decimal(request.POST.get("discount"))
                tax_percent = _decimal(request.POST.get("tax_percent"))
                if discount < 0 or discount > subtotal:
                    raise ValueError("Discount must be between 0 and the subtotal.")
                if tax_percent < 0 or tax_percent > 100:
                    raise ValueError("Tax must be between 0 and 100.")
                taxable = subtotal - discount
                tax = (taxable * tax_percent / 100).quantize(CENT)
                bill = Bill.objects.create(
                    branch=branch,
                    order=order,
                    subtotal=subtotal,
                    discount=discount,
                    tax_percent=tax_percent,
                    tax=tax,
                    total=taxable + tax,
                )

            balance = bill.balance
            if balance <= 0:
                raise ValueError("This bill is already fully paid.")
            amount = _decimal(raw_amount) if raw_amount else balance
            if amount <= 0:
                raise ValueError("Amount must be more than 0.")
            if amount > balance:
                raise ValueError(
                    f"Amount cannot be more than the balance (Rs. {balance})."
                )

            Payment.objects.create(
                bill=bill, amount=amount, method=method, cashier=request.user
            )
            if bill.balance <= 0:
                bill.paid_at = timezone.now()
                bill.save(update_fields=["paid_at"])
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("billing:cashier")

    if bill.paid_at:
        return redirect("billing:receipt", pk=bill.pk)
    messages.success(
        request,
        f"Rs. {amount} received for order #{order.pk}. Balance: Rs. {bill.balance}.",
    )
    return redirect("billing:cashier")


@role_required(*BILLING_ROLES)
def receipt(request, pk):
    branch = get_current_branch(request)
    bill = get_object_or_404(
        Bill.objects.select_related("order", "order__table").prefetch_related(
            "payments__cashier"
        ),
        pk=pk,
        branch=branch,
    )
    return render(request, "billing/receipt.html", {"bill": bill})
