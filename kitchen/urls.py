from django.urls import path

from . import views

app_name = "kitchen"

urlpatterns = [
    path("", views.display, name="display"),
    path("cards/", views.cards, name="cards"),
    path("<int:pk>/status/", views.set_status, name="set_status"),
]
