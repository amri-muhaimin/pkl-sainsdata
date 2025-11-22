from django.db import models

from masterdata.models import Mahasiswa, Dosen, PeriodePKL


class LogbookEntry(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "Draft oleh mahasiswa"),
        ("SUBMIT", "Diajukan ke dosen"),
        ("REVIEWED", "Sudah ditinjau dosen"),
    )

    mahasiswa = models.ForeignKey(
        Mahasiswa,
        on_delete=models.CASCADE,
        related_name="logbook_entries",
    )

    dosen_pembimbing = models.ForeignKey(
        Dosen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logbook_bimbingan",
        help_text="Biasanya otomatis mengikuti dosen pembimbing mahasiswa.",
    )

    periode = models.ForeignKey(
        PeriodePKL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logbook_entries",
    )

    tanggal = models.DateField()
    jam_mulai = models.TimeField(blank=True, null=True)
    jam_selesai = models.TimeField(blank=True, null=True)

    aktivitas = models.TextField(
        help_text="Deskripsikan kegiatan utama yang dilakukan pada hari tersebut."
    )

    tools_yang_digunakan = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Contoh: Python, SQL, Power BI, Excel, dsb."
    )

    output = models.TextField(
        blank=True,
        null=True,
        help_text="Hasil kerja: laporan, dashboard, script, dsb."
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    catatan_dosen = models.TextField(
        blank=True,
        null=True,
        help_text="Komentar/feedback dosen pembimbing terhadap aktivitas hari ini."
    )

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diupdate_pada = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # kalau mahasiswa sudah dipilih tapi dosen pembimbing belum diisi,
        # otomatis ambil dari mahasiswa.dosen_pembimbing
        if self.mahasiswa and self.dosen_pembimbing is None:
            self.dosen_pembimbing = self.mahasiswa.dosen_pembimbing

        if self.mahasiswa and self.periode is None:
            self.periode = self.mahasiswa.periode

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Entri Logbook"
        verbose_name_plural = "Entri Logbook"
        ordering = ["-tanggal", "-dibuat_pada"]

    def __str__(self):
        return f"{self.mahasiswa.nama} - {self.tanggal} ({self.status})"
