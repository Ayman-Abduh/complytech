from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "scope",
            "budget",
            "estimated_finish_date",
            "domains",
        ]
        widgets = {
            "estimated_finish_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),  # Date picker
            "domains": forms.CheckboxSelectMultiple(),  # Checkbox selection for domains
        }
