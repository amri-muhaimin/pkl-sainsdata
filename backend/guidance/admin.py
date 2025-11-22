from django.contrib import admin
from django import forms

from .models import GuidanceSession
from masterdata.models import PeriodePKL


class GuidanceSessionAdminForm(forms.ModelForm):
    class Meta:
        model = GuidanceSession
        fields = "__all__"
        widgets = {
            "jam_mulai": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time", "step": "900"},
            ),
            "jam_selesai": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time", "step": "900"},
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


@admin.action(description="Tandai sebagai selesai (DONE)")
def mark_done(modeladmin, request, queryset):
    updated = queryset.update(status="DONE")
    modeladmin.message_user(
        request, f"{updated} sesi bimbingan ditandai sebagai DONE."
    )


@admin.action(description="Tandai sebagai dibatalkan (CANCELLED)")
def mark_cancelled(modeladmin, request, queryset):
    updated = queryset.update(status="CANCELLED")
    modeladmin.message_user(
        request, f"{updated} sesi bimbingan ditandai sebagai CANCELLED."
    )


@admin.register(GuidanceSession)
class GuidanceSessionAdmin(admin.ModelAdmin):
    form = GuidanceSessionAdminForm

    list_display = (
        "tanggal",
        "mahasiswa",
        "dosen_pembimbing",
        "pertemuan_ke",
        "metode",
        "platform",
        "status",
    )
    list_filter = (
        "status",
        "metode",
        "periode",
        "dosen_pembimbing",
        PeriodeAktifFilter,
    )
    search_fields = (
        "mahasiswa__nama",
        "mahasiswa__nim",
        "dosen_pembimbing__nama",
        "topik",
    )
    autocomplete_fields = ("mahasiswa", "dosen_pembimbing", "periode")
    date_hierarchy = "tanggal"
    readonly_fields = ("dosen_pembimbing", "periode")

    actions = [mark_done, mark_cancelled]
