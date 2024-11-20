from django import forms
from .models import Project, ProjectControl, Evidence


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


class ProjectControlForm(forms.ModelForm):
    class Meta:
        model = ProjectControl
        fields = ["notes", "risk", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "risk": forms.Textarea(attrs={"rows": 3}),
        }


class EvidenceForm(forms.Form):
    uploaded_file = forms.FileField(
        required=False,
        label="Upload Evidence",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
