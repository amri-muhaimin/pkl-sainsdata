from django import forms
from guidance.models import GuidanceSession
from logbook.models import LogbookEntry
from django.core.exceptions import ValidationError

from masterdata.models import (
    PendaftaranPKL,
    SeminarHasilPKL,
    Dosen,
    Mitra,
    SeminarAssessment,
)



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
                    "placeholder": "Nomor pertemuan, misalnya 1, 2, 3, ..."
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
                    "placeholder": "Ruang / link meeting"
                }
            ),
            "topik": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Topik bimbingan"}
            ),
            "ringkasan_diskusi": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Ringkasan diskusi bimbingan"
                }
            ),
            "tindak_lanjut": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tugas / tindak lanjut setelah bimbingan"
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


class PendaftaranPKLMahasiswaForm(forms.ModelForm):
    mitra_baru_nama = forms.CharField(
        required=False,
        label="Nama Mitra/Perusahaan (baru)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Isi jika mitra belum ada di daftar",
            }
        ),
    )
    mitra_baru_alamat = forms.CharField(
        required=False,
        label="Alamat Mitra/Perusahaan",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Alamat lengkap mitra",
            }
        ),
    )

    class Meta:
        model = PendaftaranPKL
        fields = [
            "periode",
            "mitra",
            "jenis_pkl",
            "anggota_kelompok",
            "surat_penerimaan",
        ]
        widgets = {
            "periode": forms.Select(attrs={"class": "form-select"}),
            "mitra": forms.Select(attrs={"class": "form-select"}),
            "jenis_pkl": forms.Select(attrs={"class": "form-select"}),
            "anggota_kelompok": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        mitra = cleaned.get("mitra")
        mitra_baru_nama = cleaned.get("mitra_baru_nama")

        # Wajib: pilih mitra yang ada ATAU isi mitra baru
        if not mitra and not mitra_baru_nama:
            raise forms.ValidationError(
                "Silakan pilih mitra yang sudah ada atau isi nama mitra baru."
            )
        return cleaned


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
                attrs={"class": "form-control", "rows": 3, "placeholder": "Catatan penguji (opsional)"}
            ),
        }
        labels = {
            "pemahaman_materi": "Pemahaman materi & tujuan PKL",
            "kualitas_laporan": "Kualitas & kerapian laporan",
            "presentasi": "Kemampuan presentasi",
            "penguasaan_lapangan": "Penguasaan hasil & proses di lapangan",
            "sikap_profesional": "Sikap profesional & etika",
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
        fields = ["dosen_penguji_1", "dosen_penguji_2", "jadwal", "ruang"]
        widgets = {
            "dosen_penguji_1": forms.Select(attrs={"class": "form-select"}),
            "dosen_penguji_2": forms.Select(attrs={"class": "form-select"}),
            "jadwal": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            # ruang pakai field di atas
        }

    def __init__(self, *args, **kwargs):
        seminar = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)

        # Kedua penguji wajib
        self.fields["dosen_penguji_1"].required = True
        self.fields["dosen_penguji_2"].required = True

        # Kalau sudah ada pembimbing → exclude dari pilihan penguji
        if seminar and seminar.dosen_pembimbing_id:
            qs = Dosen.objects.exclude(pk=seminar.dosen_pembimbing_id)
            self.fields["dosen_penguji_1"].queryset = qs
            self.fields["dosen_penguji_2"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        d1 = cleaned.get("dosen_penguji_1")
        d2 = cleaned.get("dosen_penguji_2")
        jadwal = cleaned.get("jadwal")
        ruang = cleaned.get("ruang")
        seminar = self.instance

        # Wajib dua penguji
        if not d1 or not d2:
            raise ValidationError("Dua dosen penguji wajib dipilih.")

        # Tidak boleh sama
        if d1 == d2:
            raise ValidationError("Dosen penguji 1 dan 2 tidak boleh orang yang sama.")

        # Tidak boleh dosen pembimbing
        if seminar and seminar.dosen_pembimbing_id:
            if d1.pk == seminar.dosen_pembimbing_id or d2.pk == seminar.dosen_pembimbing_id:
                raise ValidationError("Dosen pembimbing tidak boleh menjadi dosen penguji.")

        if not jadwal:
            raise ValidationError("Jadwal seminar wajib diisi.")

        if not ruang:
            raise ValidationError("Ruang seminar wajib dipilih.")

        return cleaned


