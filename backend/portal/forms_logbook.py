# backend/portal/forms_logbook.py

from django import forms

from logbook.models import LogbookEntry
from .forms_base import DateInput, TimeInput


class LogbookReviewForm(forms.ModelForm):
    class Meta:
        model = LogbookEntry
        fields = ["status", "catatan_dosen"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "catatan_dosen": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }


class MahasiswaLogbookForm(forms.ModelForm):
    class Meta:
        model = LogbookEntry
        fields = [
            "tanggal",
            "jam_mulai",
            "jam_selesai",
            "aktivitas",
            "tools_yang_digunakan",
            "output",
        ]
        widgets = {
            "tanggal": DateInput(attrs={"class": "form-control"}),
            "jam_mulai": TimeInput(attrs={"class": "form-control"}),
            "jam_selesai": TimeInput(attrs={"class": "form-control"}),
            "aktivitas": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "tools_yang_digunakan": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "output": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }
