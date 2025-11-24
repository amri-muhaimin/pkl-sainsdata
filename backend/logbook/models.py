# backend/logbook/models.py
from django.db import models
from masterdata.models import Mahasiswa, Dosen, PeriodePKL


class LogbookEntry(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft (belum dikirim ke dosen)"),
        ("SUBMIT", "Diajukan ke dosen"),
        ("REVISI", "Perlu revisi"),
        ("DISETUJUI", "Disetujui dosen"),
    ]

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
        related_name="logbook_entries",
    )
    periode = models.ForeignKey(
        PeriodePKL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logbook_entries",
    )

    tanggal = models.DateField()
    jam_mulai = models.TimeField(null=True, blank=True)
    jam_selesai = models.TimeField(null=True, blank=True)
    aktivitas = models.TextField()
    tools_yang_digunakan = models.CharField(max_length=200, blank=True)
    output = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )
    catatan_dosen = models.TextField(blank=True)

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diupdate_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Logbook"
        verbose_name_plural = "Logbook"

    def __str__(self) -> str:
        return f"{self.mahasiswa.nim} - {self.tanggal} ({self.get_status_display()})"
