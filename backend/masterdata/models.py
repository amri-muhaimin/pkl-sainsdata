# backend/masterdata/models.py
# backend/masterdata/models.py
import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


def validate_surat_penerimaan_file(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    allowed_ext = [".pdf", ".jpg", ".jpeg", ".png"]
    if ext not in allowed_ext:
        raise ValidationError("File harus berformat PDF, JPG, JPEG, atau PNG.")

    max_size_mb = 2
    if file_obj.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Ukuran file maksimal {max_size_mb} MB.")


class Dosen(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dosen_profile",
        help_text="User akun untuk login sebagai dosen.",
    )
    nidn = models.CharField("NIDN", max_length=20, unique=True)
    nama = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    no_hp = models.CharField("No. HP/WA", max_length=20, blank=True, null=True)

    prodi = models.CharField(
        max_length=100,
        default="Sains Data",
        help_text="Misalnya: Sains Data, Sistem Informasi, Informatika",
    )

    kuota_bimbingan = models.PositiveIntegerField(
        default=10,
        help_text="Maksimal jumlah mahasiswa PKL yang dibimbing pada satu periode.",
    )

    is_koordinator_pkl = models.BooleanField(
        default=False,
        help_text="Centang jika dosen ini bertindak sebagai koordinator PKL.",
        )

    class Meta:
        verbose_name = "Dosen"
        verbose_name_plural = "Dosen"

    def __str__(self) -> str:
        return f"{self.nama} ({self.nidn})"



class Mitra(models.Model):
    nama = models.CharField(max_length=200)
    alamat = models.TextField(blank=True, null=True)
    kota = models.CharField(max_length=100, blank=True, null=True)
    pic_nama = models.CharField("Nama PIC", max_length=100, blank=True, null=True)
    pic_email = models.EmailField("Email PIC", blank=True, null=True)
    pic_no_hp = models.CharField("No. HP PIC", max_length=20, blank=True, null=True)

    bidang_usaha = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Contoh: Konsultan Data, Perbankan, Pemerintahan, dsb."
    )

    kuota_pkl = models.PositiveIntegerField(
        default=5,
        help_text="Perkiraan maksimal mahasiswa PKL yang dapat diterima per periode."
    )

    class Meta:
        verbose_name = "Mitra"
        verbose_name_plural = "Mitra"

    def __str__(self):
        return self.nama


class PeriodePKL(models.Model):
    SEMESTER_CHOICES = (
        ("GASAL", "Gasal"),
        ("GENAP", "Genap"),
        ("PENDEK", "Antara/Pendek"),
    )

    nama_periode = models.CharField(
        max_length=100,
        help_text="Misal: PKL 2025 Gasal"
    )
    tahun_ajaran = models.CharField(
        max_length=20,
        help_text="Misal: 2025/2026"
    )
    semester = models.CharField(
        max_length=10,
        choices=SEMESTER_CHOICES,
    )
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()

    aktif = models.BooleanField(
        default=True,
        help_text="Centang jika periode ini sedang berjalan."
    )

    class Meta:
        verbose_name = "Periode PKL"
        verbose_name_plural = "Periode PKL"

    def __str__(self):
        return f"{self.nama_periode} ({self.tahun_ajaran})"


class Mahasiswa(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null = True,
        blank = True,
        related_name = "mahasiswa_profile",
        help_text = "User akun untuk login mahasiswa",
    )

    STATUS_PKL_CHOICES = (
        ("BELUM", "Belum PKL"),
        ("SEDANG", "Sedang PKL"),
        ("SELESAI", "Selesai PKL"),
    )

    nim = models.CharField(max_length=20, unique=True)
    nama = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    no_hp = models.CharField("No. HP/WA", max_length=20, blank=True, null=True)
    angkatan = models.PositiveIntegerField(help_text="Tahun angkatan, misal: 2022")

    prodi = models.CharField(
        max_length=100,
        default="Sains Data",
        help_text="Untuk sekarang bisa diisi default Sains Data."
    )

    status_pkl = models.CharField(
        max_length=10,
        choices=STATUS_PKL_CHOICES,
        default="BELUM",
    )

    dosen_pembimbing = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mahasiswa_bimbingan",
    )

    mitra = models.ForeignKey(
        Mitra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mahasiswa_pkl",
    )

    periode = models.ForeignKey(
        PeriodePKL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mahasiswa_pkl",
    )

    class Meta:
        verbose_name = "Mahasiswa"
        verbose_name_plural = "Mahasiswa"

    def __str__(self):
        return f"{self.nama} ({self.nim})"
    

class PendaftaranPKL(models.Model):
    JENIS_PKL_CHOICES = [
        ("INDIVIDU", "Individu"),
        ("KELOMPOK", "Kelompok"),
    ]

    STATUS_CHOICES = [
        ("DIKIRIM", "Diajukan"),
        ("DISETUJUI", "Disetujui"),
        ("DITOLAK", "Ditolak"),
    ]

    mahasiswa = models.ForeignKey(
        "Mahasiswa",
        on_delete=models.CASCADE,
        related_name="pendaftaran_pkl",
    )
    periode = models.ForeignKey(
        "PeriodePKL",
        on_delete=models.PROTECT,
        related_name="pendaftaran_pkl",
    )
    mitra = models.ForeignKey(
        "Mitra",
        on_delete=models.PROTECT,
        related_name="pendaftaran_pkl",
        help_text="Perusahaan/mitra tempat PKL",
    )
    jenis_pkl = models.CharField(
        max_length=10,
        choices=JENIS_PKL_CHOICES,
    )
    anggota_kelompok = models.TextField(
        blank=True,
        help_text="Jika PKL kelompok, tuliskan NIM dan nama anggota lain.",
    )
    surat_penerimaan = models.FileField(
        upload_to="surat_penerimaan/",
        validators=[validate_surat_penerimaan_file],
        help_text="Upload surat penerimaan (PDF/JPG/PNG, maks. 2 MB).",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="DIKIRIM",
    )
    dosen_pembimbing = models.ForeignKey(
        "Dosen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendaftaran_pkl",
        help_text="Diisi oleh koordinator PKL setelah pendaftaran disetujui.",
    )
    catatan_koordinator = models.TextField(
        blank=True,
        help_text="Catatan/pertimbangan koordinator PKL.",
    )
    tanggal_pengajuan = models.DateTimeField(auto_now_add=True)
    tanggal_update = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pendaftaran PKL"
        verbose_name_plural = "Pendaftaran PKL"
        unique_together = ("mahasiswa", "periode")

    def __str__(self):
        return f"Pendaftaran PKL {self.mahasiswa.nim} - {self.periode}"

    def sinkron_ke_mahasiswa(self):
        """
        Jika pendaftaran disetujui, sinkronkan data ke Mahasiswa:
        - periode
        - mitra
        - dosen_pembimbing
        - status_pkl = 'SEDANG'
        """
        m = self.mahasiswa
        if self.periode:
            m.periode = self.periode
        if self.mitra:
            m.mitra = self.mitra
        if self.dosen_pembimbing:
            m.dosen_pembimbing = self.dosen_pembimbing
        # asumsikan Mahasiswa punya field status_pkl
        try:
            m.status_pkl = "SEDANG"
        except Exception:
            pass
        m.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Jika sudah disetujui dan dosen pembimbing sudah diisi → sinkron ke Mahasiswa
        if self.status == "DISETUJUI" and self.dosen_pembimbing:
            self.sinkron_ke_mahasiswa()

class SeminarHasilPKL(models.Model):
    STATUS_CHOICES = [
        ("DIKIRIM", "Diajukan"),
        ("DIJADWALKAN", "Dijadwalkan"),
        ("SELESAI", "Selesai"),
        ("DITOLAK", "Ditolak"),
    ]

    mahasiswa = models.ForeignKey(
        Mahasiswa,
        on_delete=models.CASCADE,
        related_name="seminar_pkl",
    )
    periode = models.ForeignKey(
        PeriodePKL,
        on_delete=models.PROTECT,
        related_name="seminar_pkl",
    )
    dosen_pembimbing = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seminar_pkl_dibimbing",
        help_text="Biasanya otomatis mengikuti dosen pembimbing PKL.",
    )

    judul_laporan = models.CharField(max_length=255)
    file_laporan = models.FileField(
        upload_to="laporan_pkl/",
        help_text="Upload laporan PKL (PDF).",
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="DIKIRIM",
    )

    dosen_penguji_1 = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seminar_pkl_diuji_1",
    )
    dosen_penguji_2 = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seminar_pkl_diuji_2",
    )
    jadwal = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tanggal & jam seminar hasil PKL.",
    )
    ruang = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ruang ujian / link meeting.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seminar Hasil PKL"
        verbose_name_plural = "Seminar Hasil PKL"
        unique_together = ("mahasiswa", "periode")

    def __str__(self):
        return f"Seminar {self.mahasiswa.nim} - {self.periode}"
