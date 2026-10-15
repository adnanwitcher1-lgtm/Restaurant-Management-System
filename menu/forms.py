from django import forms
from django.db.models import Q

from .models import Category, MenuItem


def _style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "form-check-input"
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs["class"] = "form-select"
        else:
            field.widget.attrs["class"] = "form-control"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "sort_order", "image", "is_active"]

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        _style_fields(self)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = Category.objects.filter(branch=self.branch, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A category with this name already exists in this branch.")
        return name


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ["name", "category", "price", "description", "image", "is_available"]

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        # Only categories of this branch; keep the item's current category even if it is inactive
        self.fields["category"].queryset = Category.objects.filter(branch=branch).filter(
            Q(is_active=True) | Q(pk=self.instance.category_id)
        )
        self.fields["category"].empty_label = None
        _style_fields(self)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = MenuItem.objects.filter(branch=self.branch, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("An item with this name already exists in this branch.")
        return name