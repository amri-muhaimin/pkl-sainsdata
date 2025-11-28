# backend/portal/forms_pendaftaran.py

from django import forms

from masterdata.models import PendaftaranPKL


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
