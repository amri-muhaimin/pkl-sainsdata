from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib import messages
from django.utils import timezone
import csv


from masterdata.models import PendaftaranPKL, PeriodePKL, SeminarHasilPKL

from logbook.models import LogbookEntry
from guidance.models import GuidanceSession
from .forms import (
    MahasiswaLogbookForm,
    PendaftaranPKLMahasiswaForm,
    SeminarHasilMahasiswaForm,
    MahasiswaGuidanceForm,
)


def _require_mahasiswa(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return None, HttpResponseForbidden(
            "Akun ini tidak terhubung dengan data Mahasiswa."
        )
    return request.user.mahasiswa_profile, None


# =========================
# Dashboard & export logbook
# =========================

@login_required
def mahasiswa_dashboard(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    total_logbook = LogbookEntry.objects.filter(mahasiswa=mhs).count()
    total_guidances = GuidanceSession.objects.filter(mahasiswa=mhs).count()

    last_logbook = (
        LogbookEntry.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")
        .first()
    )
    last_guidance = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")
        .first()
    )

    recent_logbooks = (
        LogbookEntry.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )
    recent_guidances = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )

    pendaftaran = (
        PendaftaranPKL.objects.filter(mahasiswa=mhs)
        .select_related("periode", "mitra", "dosen_pembimbing")
        .order_by("-tanggal_pengajuan")
        .first()
    )

    seminar = (
        SeminarHasilPKL.objects.filter(mahasiswa=mhs)
        .select_related("periode", "dosen_pembimbing")
        .order_by("-created_at")
        .first()
    )

    context = {
        "mahasiswa": mhs,
        "summary": {
            "total_logbook": total_logbook,
            "total_guidances": total_guidances,
            "last_logbook": last_logbook,
            "last_guidance": last_guidance,
        },
        "recent_logbooks": recent_logbooks,
        "recent_guidances": recent_guidances,
        "pendaftaran": pendaftaran,
        "seminar": seminar,
    }
    return render(request, "portal/mahasiswa_dashboard.html", context)


@login_required
def mahasiswa_logbook_export(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    entries = (
        LogbookEntry.objects.filter(mahasiswa=mhs)
        .select_related("periode")
        .order_by("tanggal")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"logbook_{mhs.nim}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Tanggal",
            "Jam Mulai",
            "Jam Selesai",
            "Periode",
            "Aktivitas",
            "Tools",
            "Output",
            "Status",
            "Catatan Dosen",
            "Dibuat Pada",
            "Diupdate Pada",
        ]
    )

    for e in entries:
        writer.writerow(
            [
                e.tanggal,
                e.jam_mulai or "",
                e.jam_selesai or "",
                e.periode.nama_periode if e.periode else "",
                (e.aktivitas or "").replace("\n", " "),
                e.tools_yang_digunakan or "",
                (e.output or "").replace("\n", " "),
                e.get_status_display(),
                (e.catatan_dosen or "").replace("\n", " "),
                e.dibuat_pada,
                e.diupdate_pada,
            ]
        )

    return response


# =========================
# Logbook – tambah oleh mahasiswa
# =========================

@login_required
def mahasiswa_logbook_add(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    if request.method == "POST":
        form = MahasiswaLogbookForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.mahasiswa = mhs
            entry.dosen_pembimbing = mhs.dosen_pembimbing
            entry.periode = mhs.periode
            entry.status = "SUBMIT"
            entry.save()
            messages.success(request, "Logbook berhasil dikirim ke dosen pembimbing.")
            return redirect("portal:mahasiswa_dashboard")
        messages.error(request, "Silakan periksa kembali isian logbook.")
    else:
        form = MahasiswaLogbookForm(
            initial={"tanggal": timezone.now().date()}
        )

    context = {"mahasiswa": mhs, "form": form}
    return render(request, "portal/mahasiswa_logbook_add.html", context)


# =========================
# Bimbingan – mahasiswa
# =========================

@login_required
def mahasiswa_guidance_list(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    sessions = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .select_related("dosen_pembimbing")
        .order_by("-tanggal", "-dibuat_pada")
    )

    context = {"mahasiswa": mhs, "sessions": sessions}
    return render(request, "portal/mahasiswa_guidance_list.html", context)


@login_required
def mahasiswa_guidance_create(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    if mhs.dosen_pembimbing is None:
        messages.error(
            request,
            "Anda belum memiliki dosen pembimbing PKL. "
            "Silakan hubungi koordinator PKL terlebih dahulu.",
        )
        return redirect("portal:mahasiswa_guidance_list")

    if request.method == "POST":
        form = MahasiswaGuidanceForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.mahasiswa = mhs
            session.dosen_pembimbing = mhs.dosen_pembimbing
            session.periode = mhs.periode
            session.status = "PLANNED"
            session.save()
            messages.success(request, "Pengajuan bimbingan berhasil disimpan.")
            return redirect("portal:mahasiswa_guidance_list")
        messages.error(request, "Silakan periksa kembali data bimbingan.")
    else:
        form = MahasiswaGuidanceForm()

    context = {"mahasiswa": mhs, "form": form}
    return render(request, "portal/mahasiswa_guidance_create.html", context)


# =========================
# Pendaftaran PKL oleh mahasiswa
# =========================

@login_required
def mahasiswa_pendaftaran_pkl(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    pendaftaran = (
        PendaftaranPKL.objects.filter(mahasiswa=mhs)
        .select_related("periode", "mitra", "dosen_pembimbing")
        .order_by("-tanggal_pengajuan")
        .first()
    )

    # cek periode aktif dari tabel PeriodePKL, bukan dari mhs.periode
    today = timezone.localdate()
    periode_aktif = (
        PeriodePKL.objects
        .filter(aktif=True)   # jika ingin pakai rentang tanggal, lihat catatan di bawah
        .order_by("-tanggal_mulai")
        .first()
    )
    eligible = periode_aktif is not None

    is_locked = pendaftaran is not None and pendaftaran.status != "DIKIRIM"

    if request.method == "POST":
        if not eligible:
            messages.error(request, "Belum ada periode PKL yang aktif saat ini.")
            return redirect("portal:mahasiswa_pendaftaran_pkl")

        if is_locked:
            messages.error(request, "Pendaftaran sudah diproses sehingga tidak dapat diubah lagi.")
            return redirect("portal:mahasiswa_pendaftaran_pkl")

        form = PendaftaranPKLMahasiswaForm(request.POST, request.FILES, instance=pendaftaran)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs
            obj.status = "DIKIRIM"

            # kalau belum ada pembimbing di pendaftaran, ambil dari profil mahasiswa (jika ada)
            if obj.dosen_pembimbing is None:
                obj.dosen_pembimbing = mhs.dosen_pembimbing
                
            obj.save()
            messages.success(request, "Pendaftaran PKL berhasil dikirim.")
            return redirect("portal:mahasiswa_pendaftaran_pkl")

        messages.error(request, "Silakan periksa kembali isian pendaftaran.")
    else:
        # prefill periode aktif ketika pertama kali daftar (pendaftaran belum ada)
        if pendaftaran is None and periode_aktif is not None:
            form = PendaftaranPKLMahasiswaForm(initial={"periode": periode_aktif})
        else:
            form = PendaftaranPKLMahasiswaForm(instance=pendaftaran)

    context = {
        "mahasiswa": mhs,
        "pendaftaran": pendaftaran,
        "form": form,
        "eligible": eligible,
        "is_locked": is_locked,
    }
    return render(request, "portal/mahasiswa_pendaftaran_pkl.html", context)

# =========================
# Pendaftaran Seminar Hasil PKL
# =========================

@login_required
def mahasiswa_seminar_pendaftaran(request):
    mhs, error = _require_mahasiswa(request)
    if error:
        return error

    seminar = (
        SeminarHasilPKL.objects.filter(mahasiswa=mhs)
        .select_related("periode", "dosen_pembimbing")
        .order_by("-created_at")
        .first()
    )

    jumlah_bimbingan_selesai = GuidanceSession.objects.filter(
        mahasiswa=mhs, status="DONE"
    ).count()

    # Aturan bisa disesuaikan (di sini minimal 5 bimbingan selesai)
    minimal_bimbingan = 5
    eligible = jumlah_bimbingan_selesai >= minimal_bimbingan

    is_locked = seminar is not None and seminar.status != "DIKIRIM"

    if request.method == "POST":
        if not eligible:
            messages.error(
                request,
                f"Anda belum memenuhi syarat minimal {minimal_bimbingan} kali bimbingan "
                "untuk mendaftar seminar.",
            )
            return redirect("portal:mahasiswa_seminar_pendaftaran")

        if is_locked:
            messages.error(
                request,
                "Data seminar sudah diproses sehingga tidak dapat diubah lagi.",
            )
            return redirect("portal:mahasiswa_seminar_pendaftaran")

        form = SeminarHasilMahasiswaForm(
            request.POST, request.FILES, instance=seminar
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs
            obj.periode = mhs.periode
            obj.dosen_pembimbing = mhs.dosen_pembimbing
            obj.status = "DIKIRIM"
            obj.save()
            messages.success(request, "Pendaftaran seminar berhasil dikirim.")
            return redirect("portal:mahasiswa_seminar_pendaftaran")
        messages.error(request, "Silakan periksa kembali isian formulir.")
    else:
        form = SeminarHasilMahasiswaForm(instance=seminar)

    context = {
        "mahasiswa": mhs,
        "seminar": seminar,
        "form": form,
        "eligible": eligible,
        "jumlah_bimbingan_selesai": jumlah_bimbingan_selesai,
        "is_locked": is_locked,
    }
    return render(request, "portal/mahasiswa_seminar_pendaftaran.html", context)
