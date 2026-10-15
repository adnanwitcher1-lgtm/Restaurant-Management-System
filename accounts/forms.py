from django import forms
from django.contrib.auth.password_validation import validate_password

from branches.models import Branch

from .models import Role, User


class StaffForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "cnic", "address", "role", "branch"]

    def __init__(self, *args, requester=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].required = True
        if self.instance.pk:
            self.fields["password"].help_text = "Leave blank to keep the current password."
        else:
            self.fields["password"].required = True

        # Managers cannot assign the Owner role and can only add staff to their own branch
        is_owner = bool(requester and requester.role and requester.role.name == "Owner")
        if requester is not None and not is_owner:
            self.fields["role"].queryset = Role.objects.exclude(name="Owner")
            self.fields["branch"].queryset = Branch.objects.filter(pk=requester.branch_id)
            self.fields["branch"].required = True
            self.fields["branch"].empty_label = None

        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user