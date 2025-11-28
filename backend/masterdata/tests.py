from django.test import TestCase
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from masterdata.models import (
    validate_surat_penerimaan_file,
)


# Create your tests here.
class ValidatorSuratPenerimaanTests(TestCase):
    def test_menolak_ekstensi_yang_tidak_diizinkan(self):
        file_obj = SimpleUploadedFile(
            "surat.exe", b"dummy", content_type="application/octet-stream"
        )
        with self.assertRaises(ValidationError):
            validate_surat_penerimaan_file(file_obj)

    def test_menolak_ukuran_lebih_dari_2_mb(self):
        big_content = b"x" * (3 * 1024 * 1024)  # ~3 MB
        file_obj = SimpleUploadedFile(
            "surat.pdf", big_content, content_type="application/pdf"
        )
        with self.assertRaises(ValidationError):
            validate_surat_penerimaan_file(file_obj)
            