from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Max
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth import logout
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone
import csv


from masterdata.models import Dosen, Mahasiswa, PendaftaranPKL
from logbook.models import LogbookEntry
from guidance.models import GuidanceSession
from .forms import (
    GuidanceSessionCreateForm,
    LogbookReviewForm,
    MahasiswaLogbookForm,
    PendaftaranPKLMahasiswaForm,
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

    context = {
        "dosen": dosen,
        "summary": {
            "total_dikirim": total_dikirim,
            "total_disetujui": total_disetujui,
            "total_ditolak": total_ditolak,
        },
        "latest": latest,
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

    # ambil parameter filter periode dari query string (?periode=ID)
    periode_id = request.GET.get("periode")

    logbook_qs = LogbookEntry.objects.filter(mahasiswa=mhs)
    if periode_id:
        logbook_qs = logbook_qs.filter(periode_id=periode_id)

    logbooks = logbook_qs.order_by("-tanggal", "-dibuat_pada")

    guidances = (
        GuidanceSession.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal", "-dibuat_pada")
    )

    # daftar periode yang pernah muncul di logbook mahasiswa
    periode_list = (
        LogbookEntry.objects.filter(mahasiswa=mhs, periode__isnull=False)
        .values("periode__id", "periode__nama_periode")
        .distinct()
        .order_by("periode__tanggal_mulai")
    )

    context = {
        "mahasiswa": mhs,
        "logbooks": logbooks,
        "guidances": guidances,
        "periode_list": periode_list,
        "periode_aktif_id": int(periode_id) if periode_id else None,
    }
    return render(request, "portal/mahasiswa_dashboard.html", context)



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
    if not hasattr(request.user, "mahasiswa_profile"):
        return HttpResponseForbidden("Akun ini tidak terhubung dengan data Mahasiswa.")

    mhs = request.user.mahasiswa_profile

    # Ambil pendaftaran terakhir (jika ada)
    pendaftaran = (
        PendaftaranPKL.objects.filter(mahasiswa=mhs)
        .order_by("-tanggal_pengajuan")
        .first()
    )

    # Dikunci kalau sudah diproses
    is_locked = bool(pendaftaran and pendaftaran.status in ("DISETUJUI", "DITOLAK"))

    if request.method == "POST":
        if is_locked:
            messages.error(
                request,
                "Pendaftaran PKL Anda sudah diproses dan tidak dapat diubah lagi.",
            )
            return redirect("portal:mahasiswa_pendaftaran_pkl")

        form = PendaftaranPKLMahasiswaForm(
            request.POST,
            request.FILES,
            instance=pendaftaran,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.mahasiswa = mhs
            obj.status = "DIKIRIM"
            try:
                obj.save()
            except IntegrityError:
                messages.error(
                    request,
                    "Anda sudah memiliki pendaftaran aktif pada periode ini.",
                )
                return redirect("portal:mahasiswa_pendaftaran_pkl")

            messages.success(
                request,
                "Pendaftaran PKL berhasil dikirim. Menunggu verifikasi koordinator.",
            )
            return redirect("portal:mahasiswa_pendaftaran_pkl")
        else:
            messages.error(request, "Silakan periksa kembali data pendaftaran.")
    else:
        form = PendaftaranPKLMahasiswaForm(instance=pendaftaran)

    context = {
        "mahasiswa": mhs,
        "form": form,
        "pendaftaran": pendaftaran,
        "is_locked": is_locked,
    }
    return render(request, "portal/mahasiswa_pendaftaran_pkl.html", context)

