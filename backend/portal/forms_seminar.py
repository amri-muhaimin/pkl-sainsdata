# backend/portal/forms_seminar.py

from django import forms
from django.core.exceptions import ValidationError

from masterdata.models import SeminarHasilPKL, Dosen, SeminarAssessment


class SeminarAssessmentForm(forms.ModelForm):
    """
    Diisi oleh dosen penguji (1 atau 2).
    Sistem otomatis menghitung rata-rata & huruf nilai.
    """

    class Meta:
        model = SeminarAssessment
        fields = [
            "pemahaman_materi",
            "kualitas_laporan",
            "presentasi",
            "penguasaan_lapangan",
            "sikap_profesional",
            "catatan",
        ]
        widgets = {
            "pemahaman_materi": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 100}
            ),
            "kualitas_laporan": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 100}
            ),
            "presentasi": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 100}
            ),
            "penguasaan_lapangan": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 100}
            ),
            "sikap_profesional": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 100}
            ),
            "catatan": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Catatan penguji (opsional)",
                }
            ),
        }
        labels = {
            "pemahaman_materi": "Pemahaman materi & tujuan PKL",
            "kualitas_laporan": "Kualitas & kerapian laporan",
            "presentasi": "Kemampuan presentasi",
            "penguasaan_lapangan": "Penguasaan hasil & proses di lapangan",
            "sikap_profesional": "Sikap profesional & etika",
        }


class PembimbingAssessmentForm(SeminarAssessmentForm):
    """Form penilaian PKL khusus untuk dosen pembimbing."""

    class Meta(SeminarAssessmentForm.Meta):
        labels = {
            **SeminarAssessmentForm.Meta.labels,
            "pemahaman_materi": "Pemahaman perkembangan mahasiswa selama PKL",
            "kualitas_laporan": "Kualitas dokumen & kedisiplinan bimbingan",
        }


class SeminarHasilMahasiswaForm(forms.ModelForm):
    class Meta:
        model = SeminarHasilPKL
        fields = ["judul_laporan", "file_laporan"]
        widgets = {
            "judul_laporan": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "file_laporan": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }


RUANG_SEMINAR_CHOICES = [
    ("Ruang Rapat Prodi", "Ruang Rapat Prodi"),
    ("10.2 Twin Tower", "10.2 Twin Tower"),
    ("10.3 Twin Tower", "10.3 Twin Tower"),
    ("Ruang 108 FIK 2", "Ruang 108 FIK 2"),
    ("Ruang Lab Sains Data", "Ruang Lab Sains Data"),
    ("Ruang 202 FIK 1", "Ruang 202 FIK 1"),
    ("Ruang 304 FIK 1", "Ruang 304 FIK 1"),
]


class SeminarPenjadwalanForm(forms.ModelForm):
    # Ruang dibatasi ke pilihan tertentu
    ruang = forms.ChoiceField(
        choices=RUANG_SEMINAR_CHOICES,
        required=True,
        label="Ruang Seminar",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = SeminarHasilPKL
        fields = ["dosen_penguji", "jadwal", "ruang"]
        widgets = {
            "dosen_penguji": forms.Select(attrs={"class": "form-select"}),
            "jadwal": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            # ruang pakai field di atas
        }

    def __init__(self, *args, **kwargs):
        seminar = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)

        self.fields["dosen_penguji"].required = True

        # Kalau sudah ada pembimbing → exclude dari pilihan penguji
        if seminar and seminar.dosen_pembimbing_id:
            qs = Dosen.objects.exclude(pk=seminar.dosen_pembimbing_id)
            self.fields["dosen_penguji"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        raw_dosen = str(self.data.get("dosen_penguji") or "")

        dosen_penguji = cleaned.get("dosen_penguji")
        jadwal = cleaned.get("jadwal")
        ruang = cleaned.get("ruang")
        seminar = self.instance

        errors: list[str] = []

        if not dosen_penguji:
            errors.append("Dosen penguji wajib dipilih.")

        # Tidak boleh dosen pembimbing
        if seminar and seminar.dosen_pembimbing_id:
            pembimbing_id = seminar.dosen_pembimbing_id

            if str(pembimbing_id) in (raw_d1, raw_d2):
                errors.append("Dosen pembimibng tidak boleh menjadi dosen penguji.")

        if not jadwal:
            errors.append("Jadwal seminar wajib diisi.")

        if not ruang:
            errors.append("Ruang seminar wajib dipilih")

        if errors:
            raise ValidationError(errors)

        return cleaned
