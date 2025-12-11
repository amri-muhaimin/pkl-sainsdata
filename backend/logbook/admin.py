from django.contrib import admin
from django import forms

from .models import LogbookEntry
from masterdata.models import PeriodePKL


class LogbookEntryAdminForm(forms.ModelForm):
    class Meta:
        model = LogbookEntry
        fields = "__all__"
        widgets = {
            "jam_mulai": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
                    "step": "900",  # 15 menit
                },
            ),
            "jam_selesai": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
                    "step": "900",
                },
            ),
        }


class PeriodeAktifFilter(admin.SimpleListFilter):
    title = "Periode aktif"
    parameter_name = "periode_aktif"

    def lookups(self, request, model_admin):
        return (
            ("YA", "Hanya periode aktif"),
        )

    def queryset(self, request, queryset):
        if self.value() == "YA":
            return queryset.filter(periode__aktif=True)
        return queryset


@admin.action(description="Tandai sebagai disetujui (Disetujui)")
def mark_as_reviewed(modeladmin, request, queryset):
    updated = queryset.update(status="DISETUJUI")
    modeladmin.message_user(
        request,
        f"{updated} entri logbook ditandai sebagai DISETUJUI."
    )


@admin.action(description="Tandai sebagai diajukan (SUBMIT)")
def mark_as_submitted(modeladmin, request, queryset):
    updated = queryset.update(status="SUBMIT")
    modeladmin.message_user(
        request,
        f"{updated} entri logbook ditandai sebagai SUBMIT."
    )


@admin.register(LogbookEntry)
class LogbookEntryAdmin(admin.ModelAdmin):
    form = LogbookEntryAdminForm

    list_display = (
        "tanggal",
        "mahasiswa",
        "dosen_pembimbing",
        "periode",
        "jam_mulai",
        "jam_selesai",
        "status",
        "ada_catatan_dosen",
    )
    list_filter = (
        "status",
        "periode",
        "dosen_pembimbing",
        "mahasiswa__angkatan",
        PeriodeAktifFilter,
    )
    search_fields = (
        "mahasiswa__nama",
        "mahasiswa__nim",
        "dosen_pembimbing__nama",
        "aktivitas",
        "output",
    )
    autocomplete_fields = ("mahasiswa", "dosen_pembimbing", "periode")
    date_hierarchy = "tanggal"
    readonly_fields = ("dosen_pembimbing", "periode")

    actions = [mark_as_reviewed, mark_as_submitted]

    def ada_catatan_dosen(self, obj):
        return bool(obj.catatan_dosen)
    ada_catatan_dosen.boolean = True
    ada_catatan_dosen.short_description = "Cat. dosen?"
