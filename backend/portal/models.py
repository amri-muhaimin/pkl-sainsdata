from django.db import models


class Announcement(models.Model):
    judul = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    konten = models.TextField()
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diupdate_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pengumuman"
        verbose_name_plural = "Pengumuman"
        ordering = ["-tanggal_mulai", "-dibuat_pada"]

    def __str__(self) -> str:  # pragma: no cover - representasi sederhana
        return self.judul


class FrequentlyAskedQuestion(models.Model):
    pertanyaan = models.CharField(max_length=255)
    jawaban = models.TextField()
    urutan = models.PositiveIntegerField(default=1)
    aktif = models.BooleanField(default=True)

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diupdate_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"
        ordering = ["urutan", "-dibuat_pada"]

    def __str__(self) -> str:  # pragma: no cover - representasi sederhana
        return self.pertanyaan
