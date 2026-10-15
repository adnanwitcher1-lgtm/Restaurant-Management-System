from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("TezPOS", {"fields": ("phone", "cnic", "address", "role", "branch")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("TezPOS", {"fields": ("phone", "cnic", "address", "role", "branch")}),
    )
    list_display = ("username", "email", "role", "branch", "is_active")
    list_filter = UserAdmin.list_filter + ("role", "branch")