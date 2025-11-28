from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Max, Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib import messages
import csv

from logbook.models import LogbookEntry
from guidance.models import GuidanceSession
from .pdf_utils import render_to_pdf
from masterdata.models import (
    Dosen,
    Mahasiswa,
    Mitra,
    PendaftaranPKL,
    SeminarHasilPKL,
    SeminarAssessment,
)
from .forms import (
    GuidanceSessionCreateForm,
    LogbookReviewForm,
    MahasiswaGuidanceForm,      # boleh tidak dipakai, tidak apa-apa
    DosenGuidanceValidationForm,
    SeminarAssessmentForm,
    SeminarPenjadwalanForm,
)


# =========================
# Helper role
# =========================

def _require_dosen(request):
    if not hasattr(request.user, "dosen_profile"):
        return None, HttpResponseForbidden(
            "Akun ini tidak terhubung dengan data Dosen."
        )
    return request.user.dosen_profile, None


def _require_koordinator(request):
    dosen, error = _require_dosen(request)
    if error:
        return None, error
    if not dosen.is_koordinator_pkl:
        return None, HttpResponseForbidden("Anda bukan koordinator PKL.")
    return dosen, None


# =========================
# Dosen – umum & dashboard
# =========================

def dosen_list(request):
    dosen_list = (
        Dosen.objects.all()
        .annotate(
            total_mahasiswa=Count("mahasiswa_bimbingan"),
            total_logbook=Count("mahasiswa_bimbingan__logbook_entries"),
            total_bimbingan=Count("mahasiswa_bimbingan__guidance_sessions"),
        )
        .order_by("nama")
    )
    context = {"dosen_list": dosen_list}
    return render(request, "portal/dosen_list.html", context)


@login_required
def dosen_dashboard(request):
    dosen, error = _require_dosen(request)
    if error:
        return error

    # Mahasiswa bimbingan
    mahasiswa_list = (
        Mahasiswa.objects.filter(dosen_pembimbing=dosen)
        .select_related("periode", "mitra")
        .order_by("nim")
    )

    # Ringkasan logbook
    logbook_stats = (
        LogbookEntry.objects.filter(dosen_pembimbing=dosen)
        .values("status")
        .annotate(jumlah=Count("id"))
    )
    logbook_by_status = {row["status"]: row["jumlah"] for row in logbook_stats}

    # Ringkasan bimbingan
    guidance_stats = (
        GuidanceSession.objects.filter(dosen_pembimbing=dosen)
        .values("status")
        .annotate(jumlah=Count("id"))
    )
    guidance_by_status = {row["status"]: row["jumlah"] for row in guidance_stats}

    # Logbook terbaru
    recent_logbooks = (
        LogbookEntry.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa")
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )

    # Bimbingan terbaru
    recent_guidances = (
        GuidanceSession.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa")
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )

    context = {
        "dosen": dosen,
        "mahasiswa_list": mahasiswa_list,
        "logbook_by_status": logbook_by_status,
        "guidance_by_status": guidance_by_status,
        "recent_logbooks": recent_logbooks,
        "recent_guidances": recent_guidances,
    }
    return render(request, "portal/dosen_dashboard.html", context)


@login_required
def dosen_mahasiswa_detail(request, mahasiswa_id: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    mahasiswa = get_object_or_404(
        Mahasiswa.objects.select_related("periode", "mitra"),
        pk=mahasiswa_id,
        dosen_pembimbing=dosen,
    )

    logbooks = LogbookEntry.objects.filter(mahasiswa=mahasiswa).order_by(
        "-tanggal", "-dibuat_pada"
    )
    guidances = GuidanceSession.objects.filter(mahasiswa=mahasiswa).order_by(
        "-tanggal", "-dibuat_pada"
    )

    context = {
        "dosen": dosen,
        "mahasiswa": mahasiswa,
        "logbooks": logbooks,
        "guidances": guidances,
    }
    return render(request, "portal/dosen_mahasiswa_detail.html", context)


# =========================
# Dosen – Logbook
# =========================

@login_required
def dosen_logbook_review(request, pk: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    entry = get_object_or_404(
        LogbookEntry.objects.select_related("mahasiswa"),
        pk=pk,
        dosen_pembimbing=dosen,
    )

    if request.method == "POST":
        form = LogbookReviewForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Review logbook berhasil disimpan.")
            return redirect("portal:dosen_mahasiswa_detail", mahasiswa_id=entry.mahasiswa.pk)
        messages.error(request, "Silakan periksa kembali isian form.")
    else:
        form = LogbookReviewForm(instance=entry)

    context = {"dosen": dosen, "entry": entry, "form": form}
    return render(request, "portal/dosen_logbook_review.html", context)


@login_required
def dosen_logbook_export(request):
    dosen, error = _require_dosen(request)
    if error:
        return error

    entries = (
        LogbookEntry.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa", "periode")
        .order_by("mahasiswa__nim", "tanggal")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"logbook_dosen_{dosen.nidn}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "NIM",
            "Nama Mahasiswa",
            "Periode",
            "Tanggal",
            "Jam Mulai",
            "Jam Selesai",
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
                e.mahasiswa.nim,
                e.mahasiswa.nama,
                e.periode.nama_periode if e.periode else "",
                e.tanggal,
                e.jam_mulai or "",
                e.jam_selesai or "",
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
# Dosen – Bimbingan
# =========================

@login_required
def dosen_guidance_list(request):
    dosen, error = _require_dosen(request)
    if error:
        return error

    sessions = (
        GuidanceSession.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa")
        .order_by("-tanggal", "-dibuat_pada")
    )

    context = {"dosen": dosen, "sessions": sessions}
    return render(request, "portal/dosen_guidance_list.html", context)


@login_required
def dosen_guidance_detail(request, pk: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    session = get_object_or_404(
        GuidanceSession.objects.select_related("mahasiswa"),
        pk=pk,
        dosen_pembimbing=dosen,
    )

    if request.method == "POST":
        form = DosenGuidanceValidationForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Status bimbingan berhasil diperbarui.")
            return redirect("portal:dosen_guidance_detail", pk=session.pk)
        messages.error(request, "Silakan periksa kembali isian formulir.")
    else:
        form = DosenGuidanceValidationForm(instance=session)

    context = {"dosen": dosen, "session": session, "form": form}
    return render(request, "portal/dosen_guidance_detail.html", context)


@login_required
def dosen_guidance_export(request):
    dosen, error = _require_dosen(request)
    if error:
        return error

    sessions = (
        GuidanceSession.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa", "periode")
        .order_by("mahasiswa__nim", "tanggal", "pertemuan_ke")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"bimbingan_dosen_{dosen.nidn}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "NIM",
            "Nama Mahasiswa",
            "Periode",
            "Pertemuan Ke",
            "Tanggal",
            "Jam Mulai",
            "Jam Selesai",
            "Metode",
            "Platform",
            "Topik",
            "Ringkasan Diskusi",
            "Tindak Lanjut",
            "Status",
            "Dibuat Pada",
            "Diupdate Pada",
        ]
    )

    for s in sessions:
        writer.writerow(
            [
                s.mahasiswa.nim,
                s.mahasiswa.nama,
                s.periode.nama_periode if s.periode else "",
                s.pertemuan_ke or "",
                s.tanggal,
                s.jam_mulai or "",
                s.jam_selesai or "",
                s.get_metode_display(),
                s.platform or "",
                (s.topik or "").replace("\n", " "),
                (s.ringkasan_diskusi or "").replace("\n", " "),
                (s.tindak_lanjut or "").replace("\n", " "),
                s.get_status_display(),
                s.dibuat_pada,
                s.diupdate_pada,
            ]
        )

    return response


# =========================
# Dosen – Seminar sebagai penguji/pembimbing
# =========================

@login_required
def dosen_seminar_list(request):
    dosen, error = _require_dosen(request)
    if error:
        return error

    seminars = (
        SeminarHasilPKL.objects.filter(
            Q(dosen_pembimbing=dosen)
            | Q(dosen_penguji_1=dosen)
            | Q(dosen_penguji_2=dosen)
        )
        .select_related("mahasiswa", "dosen_pembimbing", "periode")
        .order_by("jadwal", "mahasiswa__nim")
    )

    context = {"dosen": dosen, "seminars": seminars}
    return render(request, "portal/dosen_seminar_list.html", context)


@login_required
def dosen_seminar_detail(request, pk: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    seminar = get_object_or_404(
        SeminarHasilPKL.objects.select_related("mahasiswa", "periode", "dosen_pembimbing"),
        pk=pk,
    )

    if (
        seminar.dosen_pembimbing != dosen
        and seminar.dosen_penguji_1 != dosen
        and seminar.dosen_penguji_2 != dosen
    ):
        return HttpResponseForbidden("Anda tidak berhak mengakses seminar ini.")

    assessments = SeminarAssessment.objects.filter(seminar=seminar).select_related(
        "penguji"
    )

    final_score = None
    final_grade = None
    if assessments.exists():
        total = sum(float(a.nilai_angka) for a in assessments if a.nilai_angka is not None)
        if assessments.count():
            final_score = round(total / assessments.count(), 2)
            final_grade = SeminarAssessment.konversi_nilai_huruf(final_score)

    context = {
        "dosen": dosen,
        "seminar": seminar,
        "assessments": assessments,
        "final_score": final_score,
        "final_grade": final_grade,
    }
    return render(request, "portal/dosen_seminar_detail.html", context)


@login_required
def dosen_seminar_penilaian(request, pk: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    seminar = get_object_or_404(SeminarHasilPKL, pk=pk)

    if seminar.dosen_penguji_1 != dosen and seminar.dosen_penguji_2 != dosen:
        return HttpResponseForbidden("Anda bukan dosen penguji pada seminar ini.")

    assessment = SeminarAssessment.objects.filter(seminar=seminar, penguji=dosen).first()

    if request.method == "POST":
        form = SeminarAssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.seminar = seminar
            obj.penguji = dosen
            obj.save()
            messages.success(
                request,
                f"Penilaian seminar untuk {seminar.mahasiswa.nama} berhasil disimpan.",
            )
            return redirect("portal:dosen_seminar_detail", pk=seminar.pk)
        messages.error(request, "Silakan periksa kembali nilai yang diinput.")
    else:
        form = SeminarAssessmentForm(instance=assessment)

    context = {
        "dosen": dosen,
        "seminar": seminar,
        "assessment": assessment,
        "form": form,
    }
    return render(request, "portal/dosen_seminar_penilaian.html", context)


@login_required
def seminar_penilaian_pdf(request, pk: int):
    dosen, error = _require_dosen(request)
    if error:
        return error

    seminar = get_object_or_404(
        SeminarHasilPKL.objects.select_related("mahasiswa", "periode", "dosen_pembimbing"),
        pk=pk,
    )

    if (
        seminar.dosen_pembimbing != dosen
        and seminar.dosen_penguji_1 != dosen
        and seminar.dosen_penguji_2 != dosen
    ):
        return HttpResponseForbidden("Anda tidak berhak mengakses seminar ini.")

    assessments = SeminarAssessment.objects.filter(seminar=seminar).select_related(
        "penguji"
    )

    context = {"seminar": seminar, "assessments": assessments}
    pdf_bytes = render_to_pdf("portal/seminar_penilaian_pdf.html", context)
    return HttpResponse(pdf_bytes, content_type="application/pdf")


# =========================
# Koordinator – dashboard & pendaftaran PKL
# =========================

@login_required
def koordinator_dashboard(request):
    koor, error = _require_koordinator(request)
    if error:
        return error

    total_mahasiswa = Mahasiswa.objects.count()
    total_mitra = Mitra.objects.count()
    total_pendaftaran = PendaftaranPKL.objects.count()

    total_pendaftaran_dikirim = PendaftaranPKL.objects.filter(status="DIKIRIM").count()
    total_pendaftaran_disetujui = PendaftaranPKL.objects.filter(status="DISETUJUI").count()
    total_pendaftaran_ditolak = PendaftaranPKL.objects.filter(status="DITOLAK").count()

    total_seminar_dikirim = SeminarHasilPKL.objects.filter(status="DIKIRIM").count()
    total_seminar_dijadwalkan = SeminarHasilPKL.objects.filter(status="DIJADWALKAN").count()
    total_seminar_selesai = SeminarHasilPKL.objects.filter(status="SELESAI").count()

    recent_pendaftaran = (
        PendaftaranPKL.objects.select_related(
            "mahasiswa", "mitra", "periode", "dosen_pembimbing"
        )
        .order_by("-tanggal_pengajuan")[:10]
    )
    recent_seminar = (
        SeminarHasilPKL.objects.select_related(
            "mahasiswa", "periode", "dosen_pembimbing"
        )
        .order_by("-created_at")[:10]
    )

    context = {
        "koordinator": koor,
        "total_mahasiswa": total_mahasiswa,
        "total_mitra": total_mitra,
        "total_pendaftaran": total_pendaftaran,
        "total_pendaftaran_dikirim": total_pendaftaran_dikirim,
        "total_pendaftaran_disetujui": total_pendaftaran_disetujui,
        "total_pendaftaran_ditolak": total_pendaftaran_ditolak,
        "total_seminar_dikirim": total_seminar_dikirim,
        "total_seminar_dijadwalkan": total_seminar_dijadwalkan,
        "total_seminar_selesai": total_seminar_selesai,
        "recent_pendaftaran": recent_pendaftaran,
        "recent_seminar": recent_seminar,
    }
    return render(request, "portal/koordinator_dashboard.html", context)


@login_required
def koordinator_pendaftaran_list(request):
    koor, error = _require_koordinator(request)
    if error:
        return error

    status = request.GET.get("status")
    qs = PendaftaranPKL.objects.select_related(
        "mahasiswa", "mitra", "periode", "dosen_pembimbing"
    ).order_by("-tanggal_pengajuan")

    if status in {"DIKIRIM", "DISETUJUI", "DITOLAK"}:
        qs = qs.filter(status=status)

    context = {
        "koordinator": koor,
        "pendaftaran_list": qs,
        "filter_status": status,
    }
    return render(request, "portal/koordinator_pendaftaran_list.html", context)


@login_required
def koordinator_pendaftaran_detail(request, pk: int):
    koor, error = _require_koordinator(request)
    if error:
        return error

    pendaftaran = get_object_or_404(
        PendaftaranPKL.objects.select_related(
            "mahasiswa", "mitra", "periode", "dosen_pembimbing"
        ),
        pk=pk,
    )

    if request.method == "POST":
        status = request.POST.get("status")
        dosen_id = request.POST.get("dosen_pembimbing")
        catatan = request.POST.get("catatan_koordinator", "")

        if status in {"DIKIRIM", "DISETUJUI", "DITOLAK"}:
            pendaftaran.status = status

        if dosen_id:
            try:
                dosen = Dosen.objects.get(pk=int(dosen_id))
                pendaftaran.dosen_pembimbing = dosen
            except (Dosen.DoesNotExist, ValueError):
                messages.error(request, "Dosen pembimbing tidak ditemukan.")

        pendaftaran.catatan_koordinator = catatan
        pendaftaran.save()
        messages.success(request, "Pendaftaran PKL berhasil diperbarui.")
        return redirect("portal:koordinator_pendaftaran_detail", pk=pendaftaran.pk)

    dosen_list = Dosen.objects.order_by("nama")

    context = {
        "koordinator": koor,
        "pendaftaran": pendaftaran,
        "dosen_list": dosen_list,
    }
    return render(request, "portal/koordinator_pendaftaran_detail.html", context)


@login_required
def koordinator_pemetaan(request):
    koor, error = _require_koordinator(request)
    if error:
        return error

    dosen_list = (
        Dosen.objects.all()
        .annotate(
            jumlah_bimbingan=Count("mahasiswa_bimbingan"),
            jumlah_pendaftaran=Count("pendaftaran_pkl"),
        )
        .order_by("nama")
    )

    context = {"koordinator": koor, "dosen_list": dosen_list}
    return render(request, "portal/koordinator_pemetaan.html", context)


# =========================
# Koordinator – Seminar
# =========================

@login_required
def koordinator_seminar_list(request):
    koor, error = _require_koordinator(request)
    if error:
        return error

    status = request.GET.get("status")
    seminars = (
        SeminarHasilPKL.objects.select_related(
            "mahasiswa", "periode", "dosen_pembimbing"
        )
        .order_by("jadwal", "mahasiswa__nim")
    )

    if status in {"DIKIRIM", "DIJADWALKAN", "SELESAI", "DITOLAK"}:
        seminars = seminars.filter(status=status)

    context = {
        "koordinator": koor,
        "seminars": seminars,
        "filter_status": status,
    }
    return render(request, "portal/koordinator_seminar_list.html", context)


@login_required
def koordinator_seminar_detail(request, pk: int):
    koor, error = _require_koordinator(request)
    if error:
        return error

    seminar = get_object_or_404(
        SeminarHasilPKL.objects.select_related(
            "mahasiswa", "periode", "dosen_pembimbing"
        ),
        pk=pk,
    )

    if request.method == "POST":
        form = SeminarPenjadwalanForm(request.POST, instance=seminar)
        if form.is_valid():
            seminar = form.save(commit=False)
            seminar.status = "DIJADWALKAN"
            seminar.save()
            messages.success(request, "Jadwal seminar berhasil disimpan.")
            return redirect("portal:koordinator_seminar_detail", pk=seminar.pk)
        messages.error(request, "Silakan periksa kembali isian penjadwalan.")
    else:
        form = SeminarPenjadwalanForm(instance=seminar)

    assessments = SeminarAssessment.objects.filter(seminar=seminar).select_related(
        "penguji"
    )

    context = {
        "koordinator": koor,
        "seminar": seminar,
        "form": form,
        "assessments": assessments,
    }
    return render(request, "portal/koordinator_seminar_detail.html", context)


# =========================
# Koordinator – Kuota dosen
# =========================

@login_required
def koordinator_dosen_kuota(request):
    koor, error = _require_koordinator(request)
    if error:
        return error

    if request.method == "POST":
        dosen_id = request.POST.get("dosen_id")
        kuota = request.POST.get("kuota_bimbingan")

        try:
            dosen = Dosen.objects.get(pk=int(dosen_id))
            kuota_int = int(kuota)
            if kuota_int < 0:
                raise ValueError
            dosen.kuota_bimbingan = kuota_int
            dosen.save()
            messages.success(
                request,
                f"Kuota bimbingan untuk {dosen.nama} berhasil diperbarui.",
            )
        except (Dosen.DoesNotExist, ValueError, TypeError):
            messages.error(
                request,
                "Gagal memperbarui kuota. Pastikan dosen dan angka kuota valid.",
            )

        return redirect("portal:koordinator_dosen_kuota")

    dosen_list = (
        Dosen.objects.annotate(jumlah_bimbingan=Count("mahasiswa_bimbingan"))
        .order_by("nama")
    )

    context = {
        "koordinator": koor,
        "dosen_list": dosen_list,
    }
    return render(request, "portal/koordinator_dosen_kuota.html", context)
