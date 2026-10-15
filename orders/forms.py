from django import forms

from .models import Table


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ["name", "capacity", "is_active"]

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = Table.objects.filter(branch=self.branch, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A table with this name already exists in this branch.")
        return name