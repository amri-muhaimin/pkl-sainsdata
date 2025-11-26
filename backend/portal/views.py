from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Max, Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth import logout
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone
import csv
from logbook.models import LogbookEntry
from guidance.models import GuidanceSession
from .pdf_utils import render_to_pdf
from masterdata.models import (
    Dosen,
    Mahasiswa,
    PendaftaranPKL,
    Mitra,
    SeminarHasilPKL,
    SeminarAssessment,
)
from .forms import (
    GuidanceSessionCreateForm,
    LogbookReviewForm,
    MahasiswaLogbookForm,
    PendaftaranPKLMahasiswaForm,
    SeminarHasilMahasiswaForm,
    SeminarPenjadwalanForm,
    MahasiswaGuidanceForm,
    DosenGuidanceValidationForm,
    SeminarAssessmentForm,
)

def portal_logout(request):
    logout(request)
    return redirect("portal:login")

@login_required
def after_login(request):
    user = request.user
    if hasattr(user, "dosen_profile"):
        dosen = user.dosen_profile
        if dosen.is_koordinator_pkl:
            return redirect("portal:koordinator_dashboard")
        return redirect("portal:dosen_dashboard")
    elif hasattr(user, "mahasiswa_profile"):
        return redirect("portal:mahasiswa_dashboard")
    else:
        return HttpResponseForbidden("Akun ini belum dihubungkan ke Dosen atau Mahasiswa.")

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
    # pastikan user punya profil Dosen
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    mahasiswa_list = (
        Mahasiswa.objects.filter(dosen_pembimbing=dosen)
        .annotate(
            total_logbook=Count("logbook_entries"),
            total_bimbingan=Count("guidance_sessions"),
            last_logbook=Max("logbook_entries__tanggal"),
            last_guidance=Max("guidance_sessions__tanggal"),
        )
        .order_by("angkatan", "nim")
    )

    # 10 logbook & bimbingan terbaru
    recent_logbooks = (
        LogbookEntry.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa")
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )

    recent_guidances = (
        GuidanceSession.objects.filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa")
        .order_by("-tanggal", "-dibuat_pada")[:10]
    )

    # Ringkasan untuk kartu
    total_mahasiswa = mahasiswa_list.count()
    total_logbooks = LogbookEntry.objects.filter(dosen_pembimbing=dosen).count()
    total_guidances = GuidanceSession.objects.filter(dosen_pembimbing=dosen).count()
    total_mitra = (
        Mahasiswa.objects.filter(dosen_pembimbing=dosen, mitra__isnull=False)
        .values("mitra")
        .distinct()
        .count()
    )

    summary = {
        "total_mahasiswa": total_mahasiswa,
        "total_logbooks": total_logbooks,
        "total_guidances": total_guidances,
        "total_mitra": total_mitra,
    }

    context = {
        "dosen": dosen,
        "mahasiswa_list": mahasiswa_list,
        "recent_logbooks": recent_logbooks,
        "recent_guidances": recent_guidances,
        "summary": summary,
    }
    return render(request, "portal/dosen_dashboard.html", context)


@login_required
def dosen_mahasiswa_detail(request, mahasiswa_id: int):
    # pastikan user punya profil Dosen
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    mahasiswa = get_object_or_404(Mahasiswa, pk=mahasiswa_id)

    # cegah akses ke mahasiswa yang bukan bimbingannya
    if mahasiswa.dosen_pembimbing != dosen:
        return HttpResponseForbidden("Mahasiswa ini bukan bimbingan Anda.")

    if request.method == "POST":
        form = GuidanceSessionCreateForm(request.POST)
        if form.is_valid():
            sess = form.save(commit=False)
            sess.mahasiswa = mahasiswa
            sess.dosen_pembimbing = dosen
            sess.periode = mahasiswa.periode
            sess.save()
            messages.success(request, "Sesi bimbingan berhasil ditambahkan.")
            return redirect("portal:dosen_mahasiswa_detail", mahasiswa_id=mahasiswa.id)
        else:
            messages.error(request, "Silakan periksa kembali data sesi bimbingan.")
    else:
        form = GuidanceSessionCreateForm()

    logbooks = (
        LogbookEntry.objects.filter(mahasiswa=mahasiswa)
        .order_by("-tanggal", "-dibuat_pada")
    )

    guidances = (
        GuidanceSession.objects.filter(mahasiswa=mahasiswa)
        .order_by("-tanggal", "-dibuat_pada")
    )

    context = {
        "dosen": dosen,
        "mahasiswa": mahasiswa,
        "logbooks": logbooks,
        "guidances": guidances,
        "form": form,
    }
    return render(request, "portal/dosen_mahasiswa_detail.html", context)


@login_required
def dosen_logbook_review(request, logbook_id: int):
    # pastikan user punya profil Dosen
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    entry = get_object_or_404(LogbookEntry, pk=logbook_id)

    # hanya dosen pembimbing yang boleh review
    if entry.mahasiswa.dosen_pembimbing != dosen:
        return HttpResponseForbidden("Logbook ini bukan mahasiswa bimbingan Anda.")

    if request.method == "POST":
        form = LogbookReviewForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Review logbook berhasil disimpan.")
            return redirect(
                "portal:dosen_mahasiswa_detail", mahasiswa_id=entry.mahasiswa.id
            )
        else:
            messages.error(request, "Silakan periksa kembali isian review.")
    else:
        form = LogbookReviewForm(instance=entry)

    context = {
        "dosen": dosen,
        "entry": entry,
        "form": form,
    }
    return render(request, "portal/dosen_logbook_review.html", context)

@login_required
def dosen_logbook_export(request):
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    entries = (
        LogbookEntry.objects
        .filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa", "periode", "mahasiswa__mitra")
        .order_by("mahasiswa__nim", "tanggal")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"logbook_dosen_{dosen.id}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "NIM",
        "Nama Mahasiswa",
        "Tanggal",
        "Jam Mulai",
        "Jam Selesai",
        "Periode",
        "Mitra",
        "Aktivitas",
        "Tools",
        "Output",
        "Status",
        "Catatan Dosen",
        "Dibuat Pada",
        "Diupdate Pada",
    ])

    for e in entries:
        writer.writerow([
            e.mahasiswa.nim,
            e.mahasiswa.nama,
            e.tanggal,
            e.jam_mulai or "",
            e.jam_selesai or "",
            e.periode.nama_periode if e.periode else "",
            e.mahasiswa.mitra.nama if getattr(e.mahasiswa, "mitra", None) else "",
            e.aktivitas.replace("\n", " ") if e.aktivitas else "",
            e.tools_yang_digunakan or "",
            e.output.replace("\n", " ") if e.output else "",
            e.get_status_display(),
            (e.catatan_dosen or "").replace("\n", " "),
            e.dibuat_pada,
            e.diupdate_pada,
        ])

    return response

@login_required
def dosen_guidance_list(request):
    """
    Dosen melihat semua sesi bimbingan dari mahasiswa bimbingannya.
    Tidak bisa membuat sesi baru dari sini.
    """
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    sessions = (
        GuidanceSession.objects
        .filter(dosen_pembimbing=dosen)   # sesuaikan nama FK kalau beda
        .select_related("mahasiswa")
        .order_by("-tanggal", "-id")      # pakai -id kalau tidak ada created_at
    )

    context = {
        "dosen": dosen,
        "sessions": sessions,
    }
    return render(request, "portal/dosen_guidance_list.html", context)


@login_required
def dosen_guidance_detail(request, pk: int):
    """
    Dosen membuka satu sesi bimbingan (yang dia bimbing) dan
    mem-validasi statusnya.
    """
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    session = get_object_or_404(
        GuidanceSession.objects.select_related("mahasiswa"),
        pk=pk,
        dosen_pembimbing=dosen,   # agar dosen hanya bisa akses miliknya sendiri
    )

    if request.method == "POST":
        form = DosenGuidanceValidationForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Status bimbingan berhasil diperbarui.")
            return redirect("portal:dosen_guidance_detail", pk=session.pk)
        else:
            messages.error(request, "Silakan periksa kembali isian formulir.")
    else:
        form = DosenGuidanceValidationForm(instance=session)

    context = {
        "dosen": dosen,
        "session": session,
        "form": form,
    }
    return render(request, "portal/dosen_guidance_detail.html", context)

@login_required
def dosen_seminar_list(request):
    """
    Daftar semua seminar PKL di mana dosen ini menjadi penguji
    (penguji 1 atau penguji 2).
    """
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    seminars = (
        SeminarHasilPKL.objects
        .filter(Q(dosen_penguji_1=dosen) | Q(dosen_penguji_2=dosen))
        .select_related("mahasiswa", "dosen_pembimbing")
        .order_by("jadwal")   # sesuaikan dengan field jadwal di model
    )

    context = {
        "dosen": dosen,
        "seminars": seminars,
    }
    return render(request, "portal/dosen_seminar_list.html", context)



@login_required
def dosen_seminar_detail(request, pk: int):
    """
    Halaman detail seminar untuk dosen (pembimbing atau penguji).
    Menampilkan info seminar + ringkasan penilaian.
    """
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile
    seminar = get_object_or_404(SeminarHasilPKL, pk=pk)

    # hanya pembimbing / penguji yang boleh lihat
    if (
        seminar.dosen_pembimbing != dosen
        and seminar.dosen_penguji_1 != dosen
        and seminar.dosen_penguji_2 != dosen
    ):
        return HttpResponseForbidden("Anda tidak berhak mengakses seminar ini.")

    assessments = (
        SeminarAssessment.objects
        .filter(seminar=seminar)
        .select_related("penguji")
    )

    final_score = None
    final_grade = None
    if assessments.exists():
        total = sum(float(a.nilai_angka) for a in assessments)
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
    """
    Halaman form penilaian seminar untuk dosen penguji.
    Dosen hanya boleh menilai seminar di mana ia penguji_1 atau penguji_2.
    """
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile
    seminar = get_object_or_404(SeminarHasilPKL, pk=pk)

    # hanya penguji 1/2 yang boleh masuk
    if seminar.dosen_penguji_1 != dosen and seminar.dosen_penguji_2 != dosen:
        return HttpResponseForbidden("Anda bukan dosen penguji pada seminar ini.")

    # cari penilaian yang sudah pernah dibuat oleh dosen ini (kalau ada)
    assessment = SeminarAssessment.objects.filter(
        seminar=seminar,
        penguji=dosen,
    ).first()

    if request.method == "POST":
        form = SeminarAssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.seminar = seminar
            obj.penguji = dosen
            obj.save()  # di sini baru disimpan / dibuat

            messages.success(
                request,
                f"Penilaian seminar untuk {seminar.mahasiswa.nama} berhasil disimpan."
            )
            return redirect("portal:dosen_seminar_detail", pk=seminar.pk)
        else:
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
    """
    Generate PDF rekap penilaian seminar (untuk arsip/berita acara).
    Hanya bisa diakses oleh dosen pembimbing atau penguji.
    """
    seminar = get_object_or_404(SeminarHasilPKL, pk=pk)

    # batasi akses: dosen terkait saja
    if hasattr(request.user, "dosen_profile"):
        dosen = request.user.dosen_profile
        if (
            seminar.dosen_pembimbing != dosen
            and seminar.dosen_penguji_1 != dosen
            and seminar.dosen_penguji_2 != dosen
        ):
            return HttpResponseForbidden("Anda tidak berhak mengakses dokumen ini.")

    assessments = (
        SeminarAssessment.objects
        .filter(seminar=seminar)
        .select_related("penguji")
    )

    final_score = None
    final_grade = None
    if assessments.exists():
        total = sum(float(a.nilai_angka) for a in assessments)
        final_score = round(total / assessments.count(), 2)
        final_grade = SeminarAssessment.konversi_nilai_huruf(final_score)

    context = {
        "seminar": seminar,
        "assessments": assessments,
        "final_score": final_score,
        "final_grade": final_grade,
    }
    return render_to_pdf("portal/seminar_penilaian_pdf.html", context)



@login_required
def dosen_guidance_export(request):
    if not hasattr(request.user, "dosen_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile

    sessions = (
        GuidanceSession.objects
        .filter(dosen_pembimbing=dosen)
        .select_related("mahasiswa", "periode", "mahasiswa__mitra")
        .order_by("mahasiswa__nim", "tanggal", "pertemuan_ke")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"bimbingan_dosen_{dosen.id}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "NIM",
        "Nama Mahasiswa",
        "Tanggal",
        "Pertemuan Ke",
        "Metode",
        "Platform/Ruang",
        "Periode",
        "Mitra",
        "Topik",
        "Ringkasan Diskusi",
        "Tindak Lanjut",
        "Status",
        "Dibuat Pada",
        "Diupdate Pada",
    ])

    for s in sessions:
        writer.writerow([
            s.mahasiswa.nim,
            s.mahasiswa.nama,
            s.tanggal,
            s.pertemuan_ke or "",
            s.get_metode_display(),
            s.platform or "",
            s.periode.nama_periode if s.periode else "",
            s.mahasiswa.mitra.nama if getattr(s.mahasiswa, "mitra", None) else "",
            s.topik.replace("\n", " ") if s.topik else "",
            (s.ringkasan_diskusi or "").replace("\n", " "),
            (s.tindak_lanjut or "").replace("\n", " "),
            s.get_status_display(),
            s.dibuat_pada,
            s.diupdate_pada,
        ])

    return response

@login_required
def _require_koordinator(request):
    """Helper kecil: memastikan user adalah dosen koordinator PKL."""
    if not hasattr(request.user, "dosen_profile"):
        return None, HttpResponseForbidden("Akun ini tidak terhubung dengan data Dosen.")

    dosen = request.user.dosen_profile
    if not dosen.is_koordinator_pkl:
        return None, HttpResponseForbidden("Akun ini bukan koordinator PKL.")
    return dosen, None


@login_required
def koordinator_dashboard(request):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    qs = PendaftaranPKL.objects.select_related("mahasiswa", "periode", "mitra")

    total_dikirim = qs.filter(status="DIKIRIM").count()
    total_disetujui = qs.filter(status="DISETUJUI").count()
    total_ditolak = qs.filter(status="DITOLAK").count()

    latest = qs.order_by("-tanggal_pengajuan")[:10]

    # === Tambahan: ringkasan seminar hasil PKL ===
    seminar_qs = SeminarHasilPKL.objects.select_related("mahasiswa", "periode")
    seminar_summary = {
        "menunggu": seminar_qs.filter(status="DIKIRIM").count(),
        "dijadwalkan": seminar_qs.filter(status="DIJADWALKAN").count(),
        "selesai": seminar_qs.filter(status="SELESAI").count(),
    }

    context = {
        "dosen": dosen,
        "summary": {
            "total_dikirim": total_dikirim,
            "total_disetujui": total_disetujui,
            "total_ditolak": total_ditolak,
        },
        "latest": latest,

        # kirim ke template
        "seminar_summary": seminar_summary,
    }
    return render(request, "portal/koordinator_dashboard.html", context)



@login_required
def koordinator_pendaftaran_list(request):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    status_filter = request.GET.get("status", "DIKIRIM")

    qs = PendaftaranPKL.objects.select_related("mahasiswa", "periode", "mitra")
    if status_filter:
        qs = qs.filter(status=status_filter)

    pendaftaran_list = qs.order_by("-tanggal_pengajuan")

    context = {
        "dosen": dosen,
        "pendaftaran_list": pendaftaran_list,
        "status_filter": status_filter,
    }
    return render(request, "portal/koordinator_pendaftaran_list.html", context)


@login_required
def koordinator_pendaftaran_detail(request, pk: int):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    pendaftaran = get_object_or_404(
        PendaftaranPKL.objects.select_related("mahasiswa", "periode", "mitra"),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if pendaftaran.status != "DIKIRIM":
            messages.warning(
                request,
                "Pendaftaran ini sudah diproses, tidak dapat diubah lagi.",
            )
            return redirect("portal:koordinator_pendaftaran_detail", pk=pendaftaran.pk)

        if action == "setujui":
            pendaftaran.status = "DISETUJUI"
            pendaftaran.save()
            messages.success(request, "Pendaftaran PKL berhasil disetujui.")
            return redirect("portal:koordinator_pendaftaran_list")
        elif action == "tolak":
            pendaftaran.status = "DITOLAK"
            pendaftaran.save()
            messages.success(request, "Pendaftaran PKL ditolak.")
            return redirect("portal:koordinator_pendaftaran_list")
        else:
            messages.error(request, "Aksi tidak dikenal.")

    context = {
        "dosen": dosen,
        "pendaftaran": pendaftaran,
    }
    return render(request, "portal/koordinator_pendaftaran_detail.html", context)

@login_required
def koordinator_pemetaan(request):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    # Daftar dosen dengan jumlah mahasiswa bimbingan saat ini
    dosen_list = (
        Dosen.objects.all()
        .annotate(jumlah_bimbingan=Count("mahasiswa_bimbingan"))
        .order_by("nama")
    )

    # Mahasiswa yang pendaftarannya DISETUJUI dan belum punya pembimbing
    mahasiswa_unassigned = (
        Mahasiswa.objects
        .filter(pendaftaran_pkl__status="DISETUJUI", dosen_pembimbing__isnull=True)
        .select_related("mitra", "periode")
        .distinct()
        .order_by("nim")
    )

    # (opsional) Mahasiswa yang sudah punya pembimbing, hanya untuk ditampilkan
    mahasiswa_assigned = (
        Mahasiswa.objects
        .filter(pendaftaran_pkl__status="DISETUJUI", dosen_pembimbing__isnull=False)
        .select_related("mitra", "periode", "dosen_pembimbing")
        .distinct()
        .order_by("dosen_pembimbing__nama", "nim")
    )

    if request.method == "POST":
        m_id = request.POST.get("mahasiswa_id")
        d_id = request.POST.get("dosen_id")

        if not m_id or not d_id:
            messages.error(request, "Mahasiswa dan dosen harus dipilih.")
            return redirect("portal:koordinator_pemetaan")

        try:
            mhs = Mahasiswa.objects.get(pk=m_id)
        except Mahasiswa.DoesNotExist:
            messages.error(request, "Mahasiswa tidak ditemukan.")
            return redirect("portal:koordinator_pemetaan")

        try:
            dosen_pembimbing = Dosen.objects.annotate(
                jumlah_bimbingan=Count("mahasiswa_bimbingan")
            ).get(pk=d_id)
        except Dosen.DoesNotExist:
            messages.error(request, "Dosen pembimbing tidak ditemukan.")
            return redirect("portal:koordinator_pemetaan")

        # (opsional) cek kuota, hanya peringatan soft
        if dosen_pembimbing.kuota_bimbingan and \
           dosen_pembimbing.jumlah_bimbingan >= dosen_pembimbing.kuota_bimbingan:
            messages.warning(
                request,
                f"Dosen {dosen_pembimbing.nama} sudah mencapai atau melebihi kuota "
                f"({dosen_pembimbing.jumlah_bimbingan}/{dosen_pembimbing.kuota_bimbingan}), "
                f"namun pemetaan tetap disimpan."
            )

        mhs.dosen_pembimbing = dosen_pembimbing
        # kalau mau, bisa update status PKL jadi SEDANG
        if mhs.status_pkl == "BELUM":
            mhs.status_pkl = "SEDANG"
        mhs.save()

        messages.success(
            request,
            f"Mahasiswa {mhs.nim} - {mhs.nama} berhasil dipetakan ke "
            f"dosen {dosen_pembimbing.nama}.",
        )
        return redirect("portal:koordinator_pemetaan")

    context = {
        "dosen": dosen,
        "dosen_list": dosen_list,
        "mahasiswa_unassigned": mahasiswa_unassigned,
        "mahasiswa_assigned": mahasiswa_assigned,
    }
    return render(request, "portal/koordinator_pemetaan.html", context)



@login_required
def mahasiswa_logbook_export(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    entries = (
        LogbookEntry.objects
        .filter(mahasiswa=mhs)
        .select_related("periode", "mahasiswa__mitra")
        .order_by("tanggal")
    )

    response = HttpResponse(content_type="text/csv")
    filename = f"logbook_mahasiswa_{mhs.nim}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Tanggal",
        "Jam Mulai",
        "Jam Selesai",
        "Periode",
        "Mitra",
        "Aktivitas",
        "Tools",
        "Output",
        "Status",
        "Catatan Dosen",
        "Dibuat Pada",
        "Diupdate Pada",
    ])

    for e in entries:
        writer.writerow([
            e.tanggal,
            e.jam_mulai or "",
            e.jam_selesai or "",
            e.periode.nama_periode if e.periode else "",
            mhs.mitra.nama if getattr(mhs, "mitra", None) else "",
            e.aktivitas.replace("\n", " ") if e.aktivitas else "",
            e.tools_yang_digunakan or "",
            e.output.replace("\n", " ") if e.output else "",
            e.get_status_display(),
            (e.catatan_dosen or "").replace("\n", " "),
            e.dibuat_pada,
            e.diupdate_pada,
        ])

    return response


@login_required
def mahasiswa_dashboard(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    periode_id = request.GET.get("periode")

    logbook_qs = LogbookEntry.objects.filter(mahasiswa=mhs)
    if periode_id:
        logbook_qs = logbook_qs.filter(periode_id=periode_id)

    logbooks = logbook_qs.order_by("-tanggal", "-dibuat_pada")

    guidances = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")
    )

    periode_list = (
        LogbookEntry.objects.filter(mahasiswa=mhs, periode__isnull=False)
        .values("periode__id", "periode__nama_periode")
        .distinct()
        .order_by("periode__tanggal_mulai")
    )

    # === TAMBAHAN: info seminar & jumlah bimbingan selesai ===
    seminar = None
    if mhs.periode:
        seminar = (
            SeminarHasilPKL.objects.filter(mahasiswa=mhs, periode=mhs.periode)
            .order_by("-created_at")
            .first()
        )

    jumlah_bimbingan_selesai = GuidanceSession.objects.filter(
        mahasiswa=mhs, status="DONE"
    ).count()

    context = {
        "mahasiswa": mhs,
        "logbooks": logbooks,
        "guidances": guidances,
        "periode_list": periode_list,
        "periode_aktif_id": int(periode_id) if periode_id else None,

        # kirim ke template
        "seminar": seminar,
        "jumlah_bimbingan_selesai": jumlah_bimbingan_selesai,
    }
    return render(request, "portal/mahasiswa_dashboard.html", context)


@login_required
def mahasiswa_guidance_list(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    sessions = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-id")   # ganti: hilangkan '-created_at'
    )

    jumlah_selesai = sessions.filter(status="DONE").count()

    context = {
        "mahasiswa": mhs,
        "sessions": sessions,
        "jumlah_selesai": jumlah_selesai,
    }
    return render(request, "portal/mahasiswa_guidance_list.html", context)


@login_required
def mahasiswa_guidance_create(request):
    """
    Mahasiswa mengisi data bimbingan: tanggal, topik, ringkasan, dll.
    Sistem akan otomatis mengisi mahasiswa, dosen_pembimbing, dan status awal PLANNED.
    """
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    if not mhs.dosen_pembimbing:
        messages.error(
            request,
            "Dosen pembimbing PKL belum ditetapkan. Silakan hubungi koordinator PKL."
        )
        return redirect("portal:mahasiswa_guidance_list")

    if request.method == "POST":
        form = MahasiswaGuidanceForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs
            obj.dosen_pembimbing = mhs.dosen_pembimbing  # SESUAIKAN nama field FK di model
            # jika GuidanceSession punya field periode dan mahasiswa punya periode aktif:
            if hasattr(mhs, "periode") and hasattr(obj, "periode"):
                obj.periode = mhs.periode
            obj.status = "PLANNED"  # status awal: diajukan / direncanakan
            obj.save()
            messages.success(
                request,
                "Data bimbingan berhasil diajukan dan menunggu validasi dosen."
            )
            return redirect("portal:mahasiswa_guidance_list")
        else:
            messages.error(request, "Silakan periksa kembali isian formulir.")
    else:
        form = MahasiswaGuidanceForm()

    context = {
        "mahasiswa": mhs,
        "form": form,
    }
    return render(request, "portal/mahasiswa_guidance_form.html", context)


@login_required
def mahasiswa_logbook_add(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    if request.method == "POST":
        form = MahasiswaLogbookForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.mahasiswa = mhs
            entry.dosen_pembimbing = mhs.dosen_pembimbing
            entry.periode = mhs.periode

            # bedakan berdasarkan tombol yang diklik
            if "save_draft" in request.POST:
                entry.status = "DRAFT"
                messages.success(request, "Logbook disimpan sebagai draft.")
            else:
                entry.status = "SUBMIT"
                messages.success(
                    request, "Logbook berhasil disimpan dan diajukan ke dosen."
                )

            entry.save()
            return redirect("portal:mahasiswa_dashboard")
        else:
            messages.error(request, "Silakan periksa kembali isian logbook.")
    else:
        form = MahasiswaLogbookForm()

    context = {
        "mahasiswa": mhs,
        "form": form,
    }
    return render(request, "portal/mahasiswa_logbook_add.html", context)


@login_required
def mahasiswa_pendaftaran_pkl(request):
    """
    Halaman pendaftaran PKL untuk mahasiswa.
    - Menampilkan form pendaftaran.
    - Kalau sudah DISETUJUI / DITOLAK, form dikunci (hanya bisa lihat).
    """
    # pastikan user punya profil mahasiswa
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    # ambil pendaftaran terakhir milik mahasiswa ini (kalau ada)
    pendaftaran = (
        PendaftaranPKL.objects.filter(mahasiswa=mhs)
        .order_by("-id")
        .first()
    )

    # status yang membuat form terkunci
    locked_statuses = ["DISETUJUI", "DITOLAK"]
    is_locked = bool(pendaftaran and pendaftaran.status in locked_statuses)

    if request.method == "POST":
        # kalau sudah locked, jangan izinkan submit ulang
        if is_locked:
            messages.error(
                request,
                "Pendaftaran PKL Anda sudah dikunci "
                "karena telah berstatus {} dan tidak dapat diubah lagi."
                .format(pendaftaran.get_status_display() if pendaftaran else "-")
            )
            return redirect("portal:mahasiswa_pendaftaran_pkl")

        # proses form POST
        form = PendaftaranPKLMahasiswaForm(
            request.POST,
            request.FILES,
            instance=pendaftaran,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs

            # kalau model punya field periode & mahasiswa punya periode, isi otomatis
            if hasattr(mhs, "periode") and hasattr(obj, "periode") and obj.periode is None:
                obj.periode = mhs.periode

            obj.save()
            messages.success(request, "Pendaftaran PKL berhasil dikirim.")
            return redirect("portal:mahasiswa_pendaftaran_pkl")
        else:
            messages.error(request, "Silakan periksa kembali isian formulir pendaftaran PKL.")
    else:
        # GET: tampilkan form (diisi dengan data lama kalau ada)
        form = PendaftaranPKLMahasiswaForm(instance=pendaftaran)

    context = {
        "mahasiswa": mhs,
        "pendaftaran": pendaftaran,
        "is_locked": is_locked,
        "form": form,
    }
    return render(request, "portal/mahasiswa_pendaftaran_pkl.html", context)


@login_required
def mahasiswa_seminar_pendaftaran(request):
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    # Hitung jumlah bimbingan dengan status DONE
    jumlah_bimbingan_selesai = GuidanceSession.objects.filter(
        mahasiswa=mhs, status="DONE"
    ).count()

    # Syarat: minimal 6 bimbingan selesai + sudah punya pembimbing & periode PKL
    eligible = (
        jumlah_bimbingan_selesai >= 6
        and mhs.dosen_pembimbing is not None
        and mhs.periode is not None
    )

    seminar = None
    if mhs.periode:
        seminar = (
            SeminarHasilPKL.objects.filter(mahasiswa=mhs, periode=mhs.periode)
            .order_by("-created_at")
            .first()
        )

    is_locked = seminar is not None and seminar.status != "DIKIRIM"

    if request.method == "POST":
        if not eligible:
            messages.error(
                request,
                "Anda belum memenuhi syarat pendaftaran seminar hasil PKL "
                "(minimal 6x bimbingan selesai dan sudah ada dosen pembimbing & periode PKL).",
            )
            return redirect("portal:mahasiswa_seminar_pendaftaran")

        form = SeminarHasilMahasiswaForm(
            request.POST,
            request.FILES,
            instance=seminar,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs
            obj.periode = mhs.periode
            obj.dosen_pembimbing = mhs.dosen_pembimbing
            obj.status = "DIKIRIM"
            obj.save()

            messages.success(
                request,
                "Pendaftaran seminar hasil PKL berhasil dikirim. "
                "Menunggu penjadwalan oleh koordinator PKL.",
            )
            return redirect("portal:mahasiswa_seminar_pendaftaran")
        else:
            messages.error(request, "Silakan periksa kembali isian pendaftaran seminar.")
    else:
        form = SeminarHasilMahasiswaForm(instance=seminar)

    context = {
        "mahasiswa": mhs,
        "form": form,
        "seminar": seminar,
        "jumlah_bimbingan_selesai": jumlah_bimbingan_selesai,
        "eligible": eligible,
        "is_locked": is_locked,
    }
    return render(request, "portal/mahasiswa_seminar_pendaftaran.html", context)

@login_required
def koordinator_seminar_list(request):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    status_filter = request.GET.get("status", "")
    seminars = (
        SeminarHasilPKL.objects
        .select_related("mahasiswa", "dosen_pembimbing", "periode")
        .order_by("status", "jadwal", "mahasiswa__nim")
    )
    if status_filter:
        seminars = seminars.filter(status=status_filter)

    context = {
        "dosen": dosen,
        "seminars": seminars,
        "status_filter": status_filter,
    }
    return render(request, "portal/koordinator_seminar_list.html", context)


@login_required
def koordinator_seminar_detail(request, pk: int):
    dosen, error = _require_koordinator(request)
    if error:
        return error

    seminar = get_object_or_404(
        SeminarHasilPKL.objects.select_related(
            "mahasiswa",
            "mahasiswa__dosen_pembimbing",
            "mahasiswa__mitra",
            "periode",
            "dosen_pembimbing",
            "dosen_penguji_1",
            "dosen_penguji_2",
        ),
        pk=pk,
    )

    if request.method == "POST":
        form = SeminarPenjadwalanForm(request.POST, instance=seminar)
        if form.is_valid():
            cleaned = form.cleaned_data
            d1 = cleaned["dosen_penguji_1"]
            d2 = cleaned["dosen_penguji_2"]
            jadwal = cleaned["jadwal"]
            ruang = cleaned["ruang"]

            # --- Cek bentrok ruang ---
            conflict_ruang = SeminarHasilPKL.objects.filter(
                jadwal=jadwal,
                ruang=ruang,
            ).exclude(pk=seminar.pk).exists()

            # --- Cek bentrok dosen penguji ---
            conflict_dosen = SeminarHasilPKL.objects.filter(
                jadwal=jadwal,
            ).exclude(pk=seminar.pk).filter(
                Q(dosen_penguji_1__in=[d1, d2]) |
                Q(dosen_penguji_2__in=[d1, d2])
            ).exists()

            if conflict_ruang:
                form.add_error(
                    "ruang",
                    "Ruang ini sudah digunakan untuk seminar lain pada jam tersebut.",
                )

            if conflict_dosen:
                form.add_error(
                    None,
                    "Salah satu dosen penguji sudah dijadwalkan menguji mahasiswa lain "
                    "pada jam tersebut.",
                )

            if conflict_ruang or conflict_dosen:
                messages.error(
                    request,
                    "Penjadwalan tidak valid, silakan periksa pesan kesalahan di formulir.",
                )
            else:
                obj = form.save(commit=False)
                # Jika jadwal & dua penguji terisi → DIJADWALKAN
                obj.status = "DIJADWALKAN"
                obj.save()
                messages.success(request, "Penjadwalan seminar berhasil disimpan.")
                return redirect("portal:koordinator_seminar_detail", pk=seminar.pk)
        else:
            messages.error(request, "Silakan periksa kembali isian penjadwalan.")
    else:
        form = SeminarPenjadwalanForm(instance=seminar)

    context = {
        "dosen": dosen,
        "seminar": seminar,
        "form": form,
    }
    return render(request, "portal/koordinator_seminar_detail.html", context)

@login_required
def koordinator_dosen_kuota(request):
    dosen_koor, error = _require_koordinator(request)
    if error:
        return error

    qs = (
        Dosen.objects.all()
        .annotate(jumlah_bimbingan=Count("mahasiswa_bimbingan"))
        .order_by("nama")
    )

    if request.method == "POST":
        dosen_id = request.POST.get("dosen_id")
        kuota = request.POST.get("kuota_bimbingan")

        try:
            target = Dosen.objects.get(pk=dosen_id)
        except Dosen.DoesNotExist:
            messages.error(request, "Dosen tidak ditemukan.")
            return redirect("portal:koordinator_dosen_kuota")

        try:
            kuota_val = int(kuota)
            if kuota_val < 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Kuota harus berupa angka bulat >= 0.")
            return redirect("portal:koordinator_dosen_kuota")

        target.kuota_bimbingan = kuota_val
        target.save()
        messages.success(
            request,
            f"Kuota bimbingan untuk {target.nama} diubah menjadi {kuota_val} mahasiswa.",
        )
        return redirect("portal:koordinator_dosen_kuota")

    context = {
        "dosen_koor": dosen_koor,
        "dosen_list": qs,
    }
    return render(request, "portal/koordinator_dosen_kuota.html", context)

