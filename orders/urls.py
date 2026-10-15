from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("waiter/", views.waiter, name="waiter"),
    path("create/", views.order_create, name="create"),
    path("<int:pk>/status/", views.order_set_status, name="set_status"),
    path("<int:pk>/add-items/", views.order_add_items, name="add_items"),
    path("tables/", views.table_list, name="table_list"),
    path("tables/add/", views.table_add, name="table_add"),
    path("tables/qr/", views.table_qr_sheet, name="table_qr_sheet"),
    path("tables/<int:pk>/edit/", views.table_edit, name="table_edit"),
    path("tables/<int:pk>/toggle/", views.table_toggle, name="table_toggle"),
    path("tables/<int:pk>/qr.png", views.table_qr_image, name="table_qr"),
]