from django import forms

class DosenCSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="File CSV",
        help_text="Kolom minimal: nidn/nuptk,nip,nama,email,nomor hp (delimiter , atau ;).",
    )

    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label="Preview saja (dry-run, tidak menyimpan)",
        help_text="Centang untuk melihat hasil create/update/error tanpa menyimpan data.",
    )

    create_only = forms.BooleanField(
        required=False,
        initial=False,
        label="Create-only (skip jika dosen sudah ada)",
        help_text="Jika dosen (nidn/nuptk) sudah ada, baris akan dilewati (tidak update).",
    )

    reset_password = forms.BooleanField(
        required=False,
        initial=False,
        label="Reset password user menjadi NIDN/NUPTK",
        help_text="Hanya berlaku jika tidak dry-run.",
    )

class MahasiswaCSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="File CSV",
        help_text="Kolom: nama,npm,nomor_hp,email,angkatan,tanggal_lahir (delimiter , atau ;).",
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label="Preview saja (dry-run, tidak menyimpan)",
    )
    create_only = forms.BooleanField(
        required=False,
        initial=False,
        label="Create-only (skip jika mahasiswa sudah ada)",
        help_text="Jika NPM/NIM sudah ada, baris dilewati (tidak update).",
    )
    reset_password = forms.BooleanField(
        required=False,
        initial=False,
        label="Reset password menjadi tanggal lahir",
        help_text="Hanya berlaku jika tidak dry-run.",
    )