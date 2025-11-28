# backend/portal/forms_guidance.py

from django import forms

from guidance.models import GuidanceSession
from .forms_base import DateInput, TimeInput


class GuidanceSessionCreateForm(forms.ModelForm):
    class Meta:
        model = GuidanceSession
        fields = [
            "tanggal",
            "pertemuan_ke",
            "jam_mulai",
            "jam_selesai",
            "metode",
            "platform",
            "topik",
            "ringkasan_diskusi",
            "tindak_lanjut",
            "status",
        ]
        widgets = {
            "tanggal": DateInput(attrs={"class": "form-control"}),
            "pertemuan_ke": forms.NumberInput(attrs={"class": "form-control"}),
            "jam_mulai": TimeInput(attrs={"class": "form-control"}),
            "jam_selesai": TimeInput(attrs={"class": "form-control"}),
            "metode": forms.Select(attrs={"class": "form-select"}),
            "platform": forms.TextInput(attrs={"class": "form-control"}),
            "topik": forms.TextInput(attrs={"class": "form-control"}),
            "ringkasan_diskusi": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "tindak_lanjut": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class MahasiswaGuidanceForm(forms.ModelForm):
    """
    Form yang dipakai MAHASISWA untuk mengisi/mengajukan sesi bimbingan.
    Field yang muncul hanya yang memang perlu diisi mahasiswa.
    """

    class Meta:
        model = GuidanceSession
        fields = [
            "pertemuan_ke",
            "tanggal",
            "jam_mulai",
            "jam_selesai",
            "metode",
            "platform",
            "topik",
            "ringkasan_diskusi",
            "tindak_lanjut",
        ]
        widgets = {
            "pertemuan_ke": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nomor pertemuan, misalnya 1, 2, 3, ...",
                }
            ),
            "tanggal": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "jam_mulai": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "jam_selesai": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "metode": forms.Select(attrs={"class": "form-select"}),
            "platform": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ruang / link meeting",
                }
            ),
            "topik": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Topik bimbingan",
                }
            ),
            "ringkasan_diskusi": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Ringkasan diskusi bimbingan",
                }
            ),
            "tindak_lanjut": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tugas / tindak lanjut setelah bimbingan",
                }
            ),
        }


class DosenGuidanceValidationForm(forms.ModelForm):
    """
    Dipakai dosen untuk memvalidasi sesi bimbingan.
    Dosen cukup mengubah status (PLANNED -> DONE / CANCELLED).
    Kalau nanti ingin ada catatan_dosen, tinggal tambah field-nya.
    """

    class Meta:
        model = GuidanceSession
        fields = ["status"]  # atau ["status", "catatan_dosen"] kalau field itu ada
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }
