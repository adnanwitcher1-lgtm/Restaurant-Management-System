from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.cashier, name="cashier"),
    path("pay/<int:pk>/", views.pay, name="pay"),
    path("receipt/<int:pk>/", views.receipt, name="receipt"),
]
