from decimal import Decimal

from django import forms
from django.db import transaction

from .models import InventoryItem, StockMovement


def _style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "form-check-input"
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs["class"] = "form-select"
        else:
            field.widget.attrs["class"] = "form-control"


class InventoryItemForm(forms.ModelForm):
    opening_quantity = forms.DecimalField(
        label="Opening stock",
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=0,
        help_text="How much you have right now. Later changes are made with Adjust stock.",
    )

    field_order = ["name", "unit", "opening_quantity", "low_stock_level", "is_active"]

    class Meta:
        model = InventoryItem
        fields = ["name", "unit", "low_stock_level", "is_active"]

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        if self.instance.pk:
            del self.fields["opening_quantity"]  # stock changes only through Adjust stock
        _style_fields(self)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = InventoryItem.objects.filter(branch=self.branch, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("An item with this name already exists in this branch.")
        return name


class StockAdjustForm(forms.Form):
    movement_type = forms.ChoiceField(label="Type", choices=StockMovement.TYPE_CHOICES)
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=10, decimal_places=2
    )
    note = forms.CharField(
        max_length=255, required=False, help_text="Optional, for example: delivery, wastage, used in kitchen."
    )

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item
        self.fields["quantity"].help_text = f"Current stock: {item.quantity:g} {item.unit}"
        _style_fields(self)

    def apply(self, user):
        """Apply the change and log it. Returns the movement, or None if the stock is too low."""
        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(pk=self.item.pk)
            quantity = self.cleaned_data["quantity"]
            movement_type = self.cleaned_data["movement_type"]
            if movement_type == StockMovement.OUT:
                if quantity > item.quantity:
                    self.add_error("quantity", f"Only {item.quantity:g} {item.unit} in stock.")
                    return None
                item.quantity -= quantity
            else:
                item.quantity += quantity
            item.save(update_fields=["quantity"])
            return StockMovement.objects.create(
                item=item,
                movement_type=movement_type,
                quantity=quantity,
                note=self.cleaned_data["note"].strip(),
                created_by=user,
            )