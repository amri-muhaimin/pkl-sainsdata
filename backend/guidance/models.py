from django.db import models

from masterdata.models import Mahasiswa, Dosen, PeriodePKL


class GuidanceSession(models.Model):
    STATUS_CHOICES = (
        ("PLANNED", "Terjadwal"),
        ("DONE", "Selesai"),
        ("CANCELLED", "Dibatalkan"),
    )

    METODE_CHOICES = (
        ("ONLINE", "Online"),
        ("OFFLINE", "Offline"),
        ("HYBRID", "Hybrid"),
    )

    mahasiswa = models.ForeignKey(
        Mahasiswa,
        on_delete=models.CASCADE,
        related_name="guidance_sessions",
    )

    dosen_pembimbing = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guidance_sessions",
        help_text="Biasanya otomatis mengikuti dosen pembimbing mahasiswa.",
    )

    periode = models.ForeignKey(
        PeriodePKL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guidance_sessions",
    )

    pertemuan_ke = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Nomor pertemuan, misalnya 1, 2, 3, ..."
    )

    tanggal = models.DateField()
    jam_mulai = models.TimeField(blank=True, null=True)
    jam_selesai = models.TimeField(blank=True, null=True)

    metode = models.CharField(
        max_length=10,
        choices=METODE_CHOICES,
        default="ONLINE",
    )

    platform = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Misalnya: Zoom, GMeet, WhatsApp Call, Ruang Dosen 3.4, dsb."
    )

    topik = models.CharField(
        max_length=200,
        help_text="Judul/topik utama bimbingan. Misal: Review proposal, revisi laporan, dsb."
    )

    ringkasan_diskusi = models.TextField(
        help_text="Ringkasan poin-poin yang dibahas dalam bimbingan."
    )

    tindak_lanjut = models.TextField(
        blank=True,
        null=True,
        help_text="Action item/tugas yang harus dikerjakan mahasiswa setelah bimbingan."
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PLANNED",
    )

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diupdate_pada = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-fill dosen & periode dari Mahasiswa kalau belum diisi
        if self.mahasiswa:
            if self.dosen_pembimbing is None:
                self.dosen_pembimbing = self.mahasiswa.dosen_pembimbing
            if self.periode is None:
                self.periode = self.mahasiswa.periode

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Sesi Bimbingan"
        verbose_name_plural = "Sesi Bimbingan"
        ordering = ["-tanggal", "-dibuat_pada"]

    def __str__(self):
        return f"{self.mahasiswa.nama} - Pertemuan {self.pertemuan_ke or '-'} ({self.tanggal})"
