from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import InventoryItem, StockMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "quantity", "unit", "low_stock_level", "is_active")
    list_filter = ("branch", "is_active", "unit")
    search_fields = ("name",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("item", "movement_type", "quantity", "created_by", "created_at")
    list_filter = ("movement_type", "item__branch")