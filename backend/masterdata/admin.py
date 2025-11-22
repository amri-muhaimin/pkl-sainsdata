from django.contrib import admin
from .models import Dosen, Mahasiswa, Mitra, PeriodePKL, PendaftaranPKL

# import dari app lain untuk kebutuhan dashboard dosen
from logbook.models import LogbookEntry
from guidance.models import GuidanceSession

class MahasiswaInline(admin.TabularInline):
    model = Mahasiswa
    extra = 0
    fields = ("nim", "nama", "angkatan", "status_pkl", "mitra", "periode")
    readonly_fields = ("nim", "nama", "angkatan", "status_pkl", "mitra", "periode")
    can_delete = False
    show_change_link = True


@admin.register(Dosen)
class DosenAdmin(admin.ModelAdmin):
    inlines = [MahasiswaInline]

    list_display = (
        "nama",
        "nidn",
        "prodi",
        "kuota_bimbingan",
        "jumlah_mahasiswa_bimbingan",
        "jumlah_logbook",
        "jumlah_sesi_bimbingan",
    )
    search_fields = ("nama", "nidn", "email")
    list_filter = ("prodi",)

    def jumlah_mahasiswa_bimbingan(self, obj):
        return obj.mahasiswa_bimbingan.count()
    jumlah_mahasiswa_bimbingan.short_description = "Jml. Mahasiswa"

    def jumlah_logbook(self, obj):
        return LogbookEntry.objects.filter(
            mahasiswa__dosen_pembimbing=obj
        ).count()
    jumlah_logbook.short_description = "Jml. Logbook"

    def jumlah_sesi_bimbingan(self, obj):
        return GuidanceSession.objects.filter(
            mahasiswa__dosen_pembimbing=obj
        ).count()
    jumlah_sesi_bimbingan.short_description = "Jml. Sesi Bimbingan"



@admin.register(Mahasiswa)
class MahasiswaAdmin(admin.ModelAdmin):
    list_display = (
        "nama",
        "nim",
        "angkatan",
        "status_pkl",
        "dosen_pembimbing",
        "mitra",
        "total_logbook",
        "total_sesi_bimbingan",
        "last_logbook",
        "last_guidance",
    )
    search_fields = ("nama", "nim", "email")
    list_filter = (
        "angkatan",
        "status_pkl",
        "prodi",
        "periode",
        "dosen_pembimbing",
        "mitra",
    )
    autocomplete_fields = ("dosen_pembimbing", "mitra", "periode")

    def total_logbook(self, obj):
        return obj.logbook_entries.count()
    total_logbook.short_description = "Logbook"

    def total_sesi_bimbingan(self, obj):
        return obj.guidance_sessions.count()
    total_sesi_bimbingan.short_description = "Bimbingan"

    def last_logbook(self, obj):
        entry = obj.logbook_entries.order_by("-tanggal").first()
        return entry.tanggal if entry else "-"
    last_logbook.short_description = "Logbook terakhir"

    def last_guidance(self, obj):
        sess = obj.guidance_sessions.order_by("-tanggal").first()
        return sess.tanggal if sess else "-"
    last_guidance.short_description = "Bimbingan terakhir"


@admin.register(Mitra)
class MitraAdmin(admin.ModelAdmin):
    list_display = ("nama", "kota", "bidang_usaha", "kuota_pkl")
    search_fields = ("nama", "kota", "bidang_usaha", "pic_nama")
    list_filter = ("kota", "bidang_usaha")


@admin.register(PeriodePKL)
class PeriodePKLAdmin(admin.ModelAdmin):
    list_display = ("nama_periode", "tahun_ajaran", "semester", "tanggal_mulai", "tanggal_selesai", "aktif")
    list_filter = ("tahun_ajaran", "semester", "aktif")
    search_fields = ("nama_periode", "tahun_ajaran")

@admin.register(PendaftaranPKL)
class PendaftaranPKLAdmin(admin.ModelAdmin):
    list_display = (
        "mahasiswa",
        "periode",
        "mitra",
        "jenis_pkl",
        "status",
        "dosen_pembimbing",
        "tanggal_pengajuan",
    )
    list_filter = ("status", "periode", "mitra", "jenis_pkl")
    search_fields = ("mahasiswa__nim", "mahasiswa__nama", "mitra__nama")
    autocomplete_fields = ("mahasiswa", "periode", "mitra", "dosen_pembimbing")
