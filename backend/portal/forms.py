from django import forms
from guidance.models import GuidanceSession
from logbook.models import LogbookEntry
from masterdata.models import PendaftaranPKL


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


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

class PendaftaranPKLMahasiswaForm(forms.ModelForm):
    class Meta:
        model = PendaftaranPKL
        fields = ["periode", "mitra", "jenis_pkl", "anggota_kelompok", "surat_penerimaan"]
        widgets = {
            "periode": forms.Select(attrs={"class": "form-select"}),
            "mitra": forms.Select(attrs={"class": "form-select"}),
            "jenis_pkl": forms.Select(attrs={"class": "form-select"}),
            "anggota_kelompok": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }
