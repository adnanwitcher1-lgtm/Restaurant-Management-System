from django.contrib import admin

from .models import Order, OrderItem, Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "capacity", "is_active")
    list_filter = ("branch", "is_active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "branch", "table", "order_type", "status", "waiter", "created_at")
    list_filter = ("branch", "status", "order_type")
    inlines = [OrderItemInline]