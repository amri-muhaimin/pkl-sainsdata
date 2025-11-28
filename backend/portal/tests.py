# backend/masterdata/tests.py

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from masterdata.models import (
    Dosen,
    Mahasiswa,
    Mitra,
    PeriodePKL,
    PendaftaranPKL,
    SeminarAssessment,
    SeminarHasilPKL,
)





class PendaftaranPKLModelTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs1", password="test"
        )
        self.user_dsn = User.objects.create_user(
            username="dsn1", password="test"
        )

        self.dosen = Dosen.objects.create(
            user=self.user_dsn,
            nidn="1234",
            nama="Dosen 1",
        )
        self.mitra = Mitra.objects.create(nama="Mitra A")
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081010001",
            nama="Mahasiswa 1",
            angkatan=2022,
        )

    def test_sinkron_ke_mahasiswa_dipanggil_saat_status_disetujui(self):
        file_obj = SimpleUploadedFile(
            "surat.pdf", b"dummy", content_type="application/pdf"
        )

        PendaftaranPKL.objects.create(
            mahasiswa=self.mhs,
            periode=self.periode,
            mitra=self.mitra,
            jenis_pkl="INDIVIDU",
            anggota_kelompok="",
            surat_penerimaan=file_obj,
            status="DISETUJUI",
            dosen_pembimbing=self.dosen,
        )

        # reload mahasiswa dari DB
        self.mhs.refresh_from_db()
        self.assertEqual(self.mhs.periode, self.periode)
        self.assertEqual(self.mhs.mitra, self.mitra)
        self.assertEqual(self.mhs.dosen_pembimbing, self.dosen)
        self.assertEqual(self.mhs.status_pkl, "SEDANG")


class SeminarAssessmentTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs2", password="test"
        )
        self.user_dsn = User.objects.create_user(
            username="dsn2", password="test"
        )

        self.dosen = Dosen.objects.create(
            user=self.user_dsn,
            nidn="5678",
            nama="Dosen 2",
        )
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081010002",
            nama="Mahasiswa 2",
            angkatan=2022,
        )
        self.seminar = SeminarHasilPKL.objects.create(
            mahasiswa=self.mhs,
            periode=self.periode,
            dosen_pembimbing=self.dosen,
            judul_laporan="Judul",
            file_laporan=SimpleUploadedFile(
                "laporan.pdf", b"dummy", content_type="application/pdf"
            ),
        )

    def test_konversi_nilai_huruf_boundary(self):
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(81), "A")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(80), "A-")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(76), "A-")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(72), "B+")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(68), "B")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(64), "B-")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(58), "C+")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(54), "C")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(50), "C-")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(46), "D+")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(42), "D")
        self.assertEqual(SeminarAssessment.konversi_nilai_huruf(40), "E")

    def test_save_mengisi_nilai_angka_dan_nilai_huruf(self):
        assessment = SeminarAssessment.objects.create(
            seminar=self.seminar,
            penguji=self.dosen,
            pemahaman_materi=80,
            kualitas_laporan=70,
            presentasi=75,
            penguasaan_lapangan=85,
            sikap_profesional=90,
        )

        assessment.refresh_from_db()
        expected = round((80 + 70 + 75 + 85 + 90) / 5, 2)
        self.assertEqual(float(assessment.nilai_angka), expected)
        self.assertEqual(
            assessment.nilai_huruf,
            SeminarAssessment.konversi_nilai_huruf(expected),
        )

# backend/portal/tests.py

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from masterdata.models import (
    Mahasiswa,
    Dosen,
    Mitra,
    PeriodePKL,
    SeminarHasilPKL,
)
from guidance.models import GuidanceSession
from .forms import (
    PendaftaranPKLMahasiswaForm,
    SeminarPenjadwalanForm,
    MahasiswaGuidanceForm,
)


class PendaftaranPKLMahasiswaFormTests(TestCase):
    def setUp(self):
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mitra = Mitra.objects.create(nama="Mitra Ada")
        self.user_mhs = User.objects.create_user(
            username="mhs1", password="test"
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081019999",
            nama="Mahasiswa Test",
            angkatan=2022,
        )
        self.file_obj = SimpleUploadedFile(
            "surat.pdf", b"dummy", content_type="application/pdf"
        )

    def test_error_jika_tidak_pilih_mitra_dan_tidak_isi_mitra_baru(self):
        form = PendaftaranPKLMahasiswaForm(
            data={
                "periode": self.periode.pk,
                "mitra": "",
                "jenis_pkl": "INDIVIDU",
                "anggota_kelompok": "",
            },
            files={"surat_penerimaan": self.file_obj},
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Silakan pilih mitra yang sudah ada atau isi nama mitra baru.",
            form.non_field_errors(),
        )

    def test_valid_jika_memilih_mitra_yang_sudah_ada(self):
        form = PendaftaranPKLMahasiswaForm(
            data={
                "periode": self.periode.pk,
                "mitra": self.mitra.pk,
                "jenis_pkl": "INDIVIDU",
                "anggota_kelompok": "",
            },
            files={"surat_penerimaan": self.file_obj},
        )
        self.assertTrue(form.is_valid())

    def test_valid_jika_mengisi_mitra_baru(self):
        form = PendaftaranPKLMahasiswaForm(
            data={
                "periode": self.periode.pk,
                "mitra": "",
                "jenis_pkl": "INDIVIDU",
                "anggota_kelompok": "",
                "mitra_baru_nama": "Mitra Baru",
                "mitra_baru_alamat": "Alamat",
            },
            files={"surat_penerimaan": self.file_obj},
        )
        form.is_valid()  # jalankan dulu supaya form.non_field_errors terisi

        # yang kita cek: error custom tidak muncul
        self.assertNotIn(
            "Silakan pilih mitra yang sudah ada atau isi nama mitra baru.",
            form.non_field_errors(),
        )



class SeminarPenjadwalanFormTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs2", password="test"
        )
        self.user_dsn1 = User.objects.create_user(
            username="dsn1", password="test"
        )
        self.user_dsn2 = User.objects.create_user(
            username="dsn2", password="test"
        )

        self.dosen_pembimbing = Dosen.objects.create(
            user=self.user_dsn1,
            nidn="1234",
            nama="Dosen Pembimbing",
        )
        self.dosen_lain = Dosen.objects.create(
            user=self.user_dsn2,
            nidn="5678",
            nama="Dosen Penguji 1",
        )

        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081018888",
            nama="Mahasiswa Seminar",
            angkatan=2022,
        )
        self.seminar = SeminarHasilPKL.objects.create(
            mahasiswa=self.mhs,
            periode=self.periode,
            dosen_pembimbing=self.dosen_pembimbing,
            judul_laporan="Judul",
            file_laporan=SimpleUploadedFile(
                "laporan.pdf", b"dummy", content_type="application/pdf"
            ),
        )

    def test_error_jika_penguji_sama(self):
        form = SeminarPenjadwalanForm(
            data={
                "dosen_penguji_1": self.dosen_lain.pk,
                "dosen_penguji_2": self.dosen_lain.pk,
                "jadwal": "2025-01-10T08:00",
                "ruang": "Ruang Rapat Prodi",
            },
            instance=self.seminar,
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Dosen penguji 1 dan 2 tidak boleh orang yang sama.",
            form.non_field_errors(),
        )

    def test_error_jika_penguji_sama_dengan_pembimbing(self):
        form = SeminarPenjadwalanForm(
            data={
                "dosen_penguji_1": self.dosen_pembimbing.pk,
                "dosen_penguji_2": self.dosen_lain.pk,
                "jadwal": "2025-01-10T08:00",
                "ruang": "Ruang Rapat Prodi",
            },
            instance=self.seminar,
        )
        self.assertFalse(form.is_valid())
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Dua dosen penguji wajib dipilih.",
            form.non_field_errors(),
        )


    def test_valid_jika_input_benar(self):
        user_dsn3 = User.objects.create_user(
            username="dsn3", password="test"
        )
        dosen_lain2 = Dosen.objects.create(
            user=user_dsn3,
            nidn="9999",
            nama="Dosen Penguji 2",
        )

        form = SeminarPenjadwalanForm(
            data={
                "dosen_penguji_1": self.dosen_lain.pk,
                "dosen_penguji_2": dosen_lain2.pk,
                "jadwal": "2025-01-10T08:00",
                "ruang": "Ruang Rapat Prodi",
            },
            instance=self.seminar,
        )
        self.assertTrue(form.is_valid())


class MahasiswaGuidanceFormTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs3", password="test"
        )
        self.user_dsn = User.objects.create_user(
            username="dsn10", password="test"
        )
        self.dosen = Dosen.objects.create(
            user=self.user_dsn,
            nidn="1010",
            nama="Dosen",
        )
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081017777",
            nama="Mahasiswa Bimbingan",
            angkatan=2022,
            dosen_pembimbing=self.dosen,
            periode=self.periode,
        )

    def test_mahasiswa_guidance_form_valid_dan_bisa_disimpan(self):
        form = MahasiswaGuidanceForm(
            data={
                "pertemuan_ke": 1,
                "tanggal": "2025-01-05",
                "jam_mulai": "08:00",
                "jam_selesai": "09:00",
                "metode": "ONLINE",
                "platform": "Zoom",
                "topik": "Diskusi awal",
                "ringkasan_diskusi": "Isi diskusi",
                "tindak_lanjut": "Kerjakan bab 1",
            }
        )
        self.assertTrue(form.is_valid())

        session = form.save(commit=False)
        session.mahasiswa = self.mhs
        session.save()

        self.assertEqual(session.mahasiswa, self.mhs)
        self.assertEqual(session.dosen_pembimbing, self.dosen)
        self.assertEqual(session.periode, self.periode)


# backend/guidance/tests.py

from django.test import TestCase
from django.contrib.auth.models import User

from masterdata.models import Dosen, Mahasiswa, PeriodePKL
from guidance.models import GuidanceSession


class GuidanceSessionModelTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs4", password="test"
        )
        self.user_dsn = User.objects.create_user(
            username="dsn4", password="test"
        )

        self.dosen = Dosen.objects.create(
            user=self.user_dsn,
            nidn="2020",
            nama="Dosen",
        )
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081010004",
            nama="Mahasiswa Bimbingan",
            angkatan=2022,
            dosen_pembimbing=self.dosen,
            periode=self.periode,
        )

    def test_auto_fill_dosen_dan_periode_dari_mahasiswa(self):
        session = GuidanceSession.objects.create(
            mahasiswa=self.mhs,
            pertemuan_ke=1,
            tanggal="2025-01-05",
            topik="Topik",
            ringkasan_diskusi="Diskusi",
        )

        self.assertEqual(session.dosen_pembimbing, self.dosen)
        self.assertEqual(session.periode, self.periode)


# backend/logbook/tests.py

from django.test import TestCase
from django.contrib.auth.models import User

from masterdata.models import Dosen, Mahasiswa, PeriodePKL
from logbook.models import LogbookEntry


class LogbookEntryModelTests(TestCase):
    def setUp(self):
        self.user_mhs = User.objects.create_user(
            username="mhs5", password="test"
        )
        self.user_dsn = User.objects.create_user(
            username="dsn5", password="test"
        )

        self.dosen = Dosen.objects.create(
            user=self.user_dsn,
            nidn="3030",
            nama="Dosen Logbook",
        )
        self.periode = PeriodePKL.objects.create(
            nama_periode="PKL 2025 Gasal",
            tahun_ajaran="2025/2026",
            semester="GASAL",
            tanggal_mulai="2025-01-01",
            tanggal_selesai="2025-06-30",
        )
        self.mhs = Mahasiswa.objects.create(
            user=self.user_mhs,
            nim="20081010005",
            nama="Mahasiswa Logbook",
            angkatan=2022,
            dosen_pembimbing=self.dosen,
            periode=self.periode,
        )

    def test_str_menampilkan_nim_tanggal_dan_status(self):
        entry = LogbookEntry.objects.create(
            mahasiswa=self.mhs,
            dosen_pembimbing=self.dosen,
            periode=self.periode,
            tanggal="2025-01-10",
            aktivitas="Aktivitas",
            tools_yang_digunakan="Python",
            output="Output",
            status="SUBMIT",
        )
        s = str(entry)
        # cek NIM muncul
        self.assertIn(self.mhs.nim, s)
        # cek tanggal muncul
        self.assertIn(str(entry.tanggal), s)
        # cek status dalam bentuk label (mis. 'Diajukan ke dosen')
        self.assertIn(entry.get_status_display(), s)

