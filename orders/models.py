from django.db import models

# Create your models here.
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Table(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="tables")
    name = models.CharField(max_length=30, help_text="For example: T1, T2 or Window 1.")
    capacity = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="unique_table_name_per_branch")
        ]

    def __str__(self):
        return self.name


# status -> list of (next status, button label, roles allowed to do it)
STATUS_ACTIONS = {
    "pending": [
        ("preparing", "Start preparing", ("Owner", "Manager", "Kitchen")),
        ("cancelled", "Cancel", ("Owner", "Manager", "Waiter")),
    ],
    "preparing": [
        ("ready", "Mark ready", ("Owner", "Manager", "Kitchen")),
    ],
    "ready": [
        ("served", "Mark served", ("Owner", "Manager", "Waiter")),
    ],
}


class Order(models.Model):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    TYPE_CHOICES = [(DINE_IN, "Dine-in"), (TAKEAWAY, "Takeaway")]

    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PREPARING, "Preparing"),
        (READY, "Ready"),
        (SERVED, "Served"),
        (CANCELLED, "Cancelled"),
    ]
    ACTIVE_STATUSES = (PENDING, PREPARING, READY)
    DONE_STATUSES = (SERVED, CANCELLED)

    BADGE_CLASSES = {
        PENDING: "bg-warning text-dark",
        PREPARING: "bg-info text-dark",
        READY: "bg-success",
        SERVED: "bg-secondary",
        CANCELLED: "bg-danger",
    }

    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="orders")
    table = models.ForeignKey(
        Table, null=True, blank=True, on_delete=models.PROTECT, related_name="orders"
    )
    order_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DINE_IN)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders_taken",
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Order #{self.pk}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))

    @property
    def status_badge(self):
        return self.BADGE_CLASSES.get(self.status, "bg-secondary")

    def actions_for(self, role_name):
        """Status changes the given role may make on this order: [(status, label), ...]."""
        return [
            (status, label)
            for status, label, roles in STATUS_ACTIONS.get(self.status, [])
            if role_name in roles
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "menu.MenuItem", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Name and price are copied from the menu so old orders never change when the menu does
    name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity