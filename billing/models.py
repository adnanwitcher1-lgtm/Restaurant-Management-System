from decimal import Decimal

from django.conf import settings
from django.db import models


class Bill(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, related_name="bills"
    )
    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT, related_name="bill"
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    # Set only when the bill is fully paid
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Bill #{self.pk}"

    @property
    def paid_amount(self):
        return sum((p.amount for p in self.payments.all()), Decimal("0"))

    @property
    def balance(self):
        return self.total - self.paid_amount

    @property
    def is_paid(self):
        return self.balance <= 0


class Payment(models.Model):
    CASH = "cash"
    CARD = "card"
    ONLINE = "online"
    METHOD_CHOICES = [(CASH, "Cash"), (CARD, "Card"), (ONLINE, "Online")]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default=CASH)
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments_taken",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.amount} ({self.method})"
