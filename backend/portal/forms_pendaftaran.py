# backend/portal/forms_pendaftaran.py

from django import forms
from django.db import transaction

from masterdata.models import PendaftaranPKL, Mitra


class PendaftaranPKLMahasiswaForm(forms.ModelForm):
    mitra_baru_nama = forms.CharField(
        required=False,
        label="Nama Mitra/Perusahaan (baru)",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Isi jika mitra belum ada di daftar"}
        ),
    )
    mitra_baru_alamat = forms.CharField(
        required=False,
        label="Alamat Mitra/Perusahaan",
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 2, "placeholder": "Alamat lengkap mitra"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # KUNCI: dropdown mitra jangan wajib, supaya bisa kosong saat mitra baru diisi
        self.fields["mitra"].required = False

    class Meta:
        model = PendaftaranPKL
        fields = [
            "periode",
            "mitra",
            "tanggal_mulai_pkl",
            "tanggal_selesai_pkl",
            "jenis_pkl",
            "anggota_kelompok",
            "surat_penerimaan",
        ]
        widgets = {
            "periode": forms.Select(attrs={"class": "form-select"}),
            "mitra": forms.Select(attrs={"class": "form-select"}),
            "jenis_pkl": forms.Select(attrs={"class": "form-select"}),
            "anggota_kelompok": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tanggal_mulai_pkl": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tanggal_selesai_pkl": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        mulai = cleaned.get("tanggal_mulai_pkl")
        selesai = cleaned.get("tanggal_selesai_pkl")

        if not mulai or not selesai:
            raise forms.ValidationError("Tanggal mulai dan selesai PKL wajib diisi.")

        if mulai and selesai and mulai > selesai:
            self.add_error("tanggal_selesai_pkl", "Tanggal selesai harus setelah/sama dengan tanggal mulai.")


        mitra = cleaned.get("mitra")
        nama_baru = (cleaned.get("mitra_baru_nama") or "").strip()
        alamat_baru = (cleaned.get("mitra_baru_alamat") or "").strip()

        if mitra and nama_baru:
            raise forms.ValidationError("Pilih mitra yang sudah ada ATAU isi mitra baru. Jangan keduanya.")

        if not mitra and not nama_baru:
            raise forms.ValidationError("Silakan pilih mitra yang sudah ada atau isi nama mitra baru.")

        if nama_baru and not alamat_baru:
            self.add_error("mitra_baru_alamat", "Alamat mitra wajib diisi jika menambahkan mitra baru.")

        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=False)

        nama_baru = (self.cleaned_data.get("mitra_baru_nama") or "").strip()
        alamat_baru = (self.cleaned_data.get("mitra_baru_alamat") or "").strip()

        # JANGAN pakai instance.mitra di sini
        if not instance.mitra_id and nama_baru:
            mitra, created = Mitra.objects.get_or_create(
                nama=nama_baru,
                defaults={"alamat": alamat_baru},
            )
            if (not created) and alamat_baru and not (mitra.alamat or "").strip():
                mitra.alamat = alamat_baru
                mitra.save(update_fields=["alamat"])

            instance.mitra_id = mitra.id  # set FK pakai _id (paling aman)

        if commit:
            instance.save()
            self.save_m2m()
    
        return instance


