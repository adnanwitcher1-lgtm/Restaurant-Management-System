from django.contrib import admin

from .models import Bill, Payment

admin.site.register(Bill)
admin.site.register(Payment)
