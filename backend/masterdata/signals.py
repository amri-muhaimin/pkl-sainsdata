# backend/masterdata/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PendaftaranPKL


@receiver(post_save, sender=PendaftaranPKL)
def sync_mahasiswa_when_pendaftaran_approved(sender, instance, created, **kwargs):
    """
    Setelah PendaftaranPKL disimpan, jika status = DISETUJUI,
    sinkronkan informasi ke entitas Mahasiswa.
    """
    if instance.status == "DISETUJUI":
        instance.sinkron_ke_mahasiswa()
