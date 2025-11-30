from django.contrib import admin

from .models import Announcement, FrequentlyAskedQuestion


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "judul",
        "tanggal_mulai",
        "tanggal_selesai",
        "is_published",
    )
    list_filter = ("is_published",)
    search_fields = ("judul", "konten")
    prepopulated_fields = {"slug": ("judul",)}


@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(admin.ModelAdmin):
    list_display = ("pertanyaan", "urutan", "aktif")
    list_filter = ("aktif",)
    search_fields = ("pertanyaan", "jawaban")
