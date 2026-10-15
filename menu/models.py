from django.db import models
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image


def shrink_image(field, max_px=800):
    if not field or getattr(field, "_committed", True):
        return
    img = Image.open(field).convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=80, optimize=True)
    field.save(field.name.rsplit(".", 1)[0] + ".jpg", ContentFile(buf.getvalue()), save=False)
# Create your models here.
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, related_name="menu_categories"
    )
    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu/categories/", blank=True)
    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], name="unique_category_name_per_branch"
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        shrink_image(self.image)
        super().save(*args, **kwargs)

class MenuItem(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, related_name="menu_items"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category__sort_order", "category__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], name="unique_item_name_per_branch"
            )
        ]

    def __str__(self):
        return self.name
    def save(self, *args, **kwargs):
        shrink_image(self.image)
        super().save(*args, **kwargs)