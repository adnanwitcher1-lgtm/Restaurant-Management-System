from django.db import models

# Create your models here.
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ("kg", "Kilogram (kg)"),
        ("g", "Gram (g)"),
        ("l", "Litre (l)"),
        ("ml", "Millilitre (ml)"),
        ("pcs", "Pieces"),
        ("pack", "Pack / Box"),
    ]

    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, related_name="inventory_items"
    )
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="kg")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    low_stock_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Warn when the stock is at or below this level.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], name="unique_inventory_item_per_branch"
            )
        ]

    def __str__(self):
        return self.name

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return "out"
        if self.quantity <= self.low_stock_level:
            return "low"
        return "ok"


class StockMovement(models.Model):
    IN = "in"
    OUT = "out"
    TYPE_CHOICES = [(IN, "Stock in"), (OUT, "Stock out")]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} - {self.item.name}"