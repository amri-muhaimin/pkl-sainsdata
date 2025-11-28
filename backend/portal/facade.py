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

