from django.urls import path

from . import views

app_name = "branches"

urlpatterns = [
    path("", views.branch_list, name="list"),
    path("add/", views.branch_add, name="add"),
    path("<int:pk>/edit/", views.branch_edit, name="edit"),
    path("<int:pk>/toggle/", views.branch_toggle, name="toggle"),
    path("switch/", views.branch_switch, name="switch"),
]