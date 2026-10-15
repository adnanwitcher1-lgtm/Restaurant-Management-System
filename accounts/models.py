from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    permissions_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    cnic = models.CharField("CNIC", max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    role = models.ForeignKey(
        Role, null=True, blank=True, on_delete=models.SET_NULL
    )
    branch = models.ForeignKey(
        "branches.Branch", null=True, blank=True, on_delete=models.SET_NULL
    )
