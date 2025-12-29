from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import redirect

import csv
import io

from .models import Dosen, Mahasiswa, Mitra, PeriodePKL, PendaftaranPKL

# import dari app lain untuk kebutuhan dashboard dosen
from logbook.models import LogbookEntry
from guidance.models import GuidanceSession

from .admin_forms import DosenCSVImportForm, MahasiswaCSVImportForm


# =========================
# Helpers untuk import CSV
# =========================
def _norm(s: str) -> str:
    return (s or "").strip()


def _pick(row: dict, keys: list[str]) -> str:
    for k in keys:
        if k in row and row[k] is not None:
            return _norm(row[k])
    return ""

from datetime import datetime

def _parse_date(s: str):
    s = _norm(s)
    if not s:
        return None

    # format yang umum dari CSV/Excel
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValidationError(f"Format tanggal_lahir tidak dikenali: {s}. Pakai YYYY-MM-DD atau DD/MM/YYYY.")

def _password_from_dob(d):
    # password default: YYYYMMDD
    return d.strftime("%Y%m%d")


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

    # Tombol import di change list
    change_list_template = "admin/masterdata/dosen/change_list.html"

    # list_display jangan mengacu ke field yang mungkin tidak ada -> pakai wrapper method
    list_display = (
        "nama", "nidn", "nip", "no_hp", "email",
        "is_koordinator_pkl_display", "kuota_bimbingan_display",
        "jumlah_mahasiswa_bimbingan", "jumlah_logbook", "jumlah_sesi_bimbingan",
    )
    search_fields = ("nama", "nidn", "nip", "email")

    # Filter dinamis (biar system check tidak error)
    def get_list_filter(self, request):
        filters = []
        if hasattr(Dosen, "is_koordinator_pkl"):
            filters.append("is_koordinator_pkl")
        elif hasattr(Dosen, "is_koordinator"):
            filters.append("is_koordinator")
        return tuple(filters)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="masterdata_dosen_import_csv",
            ),
        ]
        return my_urls + urls

    # ===== wrapper kolom koordinator =====
    def is_koordinator_pkl_display(self, obj):
        if hasattr(obj, "is_koordinator_pkl"):
            return obj.is_koordinator_pkl
        if hasattr(obj, "is_koordinator"):
            return obj.is_koordinator
        return False

    is_koordinator_pkl_display.boolean = True
    is_koordinator_pkl_display.short_description = "Koordinator PKL"

    # ===== wrapper kolom kuota =====
    def kuota_bimbingan_display(self, obj):
        if hasattr(obj, "kuota_bimbingan"):
            return obj.kuota_bimbingan
        if hasattr(obj, "kuota"):
            return obj.kuota
        return "-"

    kuota_bimbingan_display.short_description = "Kuota Bimbingan"

    def import_csv(self, request):
        """
        Import Dosen via CSV (minimal kolom):
        - nidn/nuptk (wajib) -> Dosen.nidn
        - nip (wajib) -> Dosen.nip dan User.username
        - nama (wajib) -> Dosen.nama
        - email (opsional) -> User.email dan Dosen.email
        - nomor hp (opsional) -> Dosen.no_hp

        Fitur:
        - dry_run: preview tanpa menyimpan
        - create_only: jika dosen sudah ada -> skip
        - reset_password: set password user = nidn/nuptk (hanya saat real import)
        Password default user: NIDN/NUPTK
        Username user: NIP
        """
        if request.method == "POST":
            form = DosenCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]
                create_only = form.cleaned_data["create_only"]
                reset_password = form.cleaned_data["reset_password"]

                created, updated, skipped, failed = 0, 0, 0, 0
                errors: list[str] = []

                text = f.read().decode("utf-8-sig", errors="replace")
                stream = io.StringIO(text)

                # autodetect delimiter: ',' atau ';'
                sample = stream.read(2048)
                stream.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;")
                except csv.Error:
                    dialect = csv.excel

                reader = csv.DictReader(stream, dialect=dialect)
                if not reader.fieldnames:
                    messages.error(request, "CSV tidak memiliki header.")
                    return TemplateResponse(
                        request,
                        "admin/masterdata/dosen/import_csv.html",
                        dict(self.admin_site.each_context(request), title="Import Dosen (CSV)", form=form),
                    )

                # normalize header -> lower
                reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

                for line_no, raw in enumerate(reader, start=2):
                    row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}

                    nama = _pick(row, ["nama", "name"])
                    nidn_nuptk = _pick(row, ["nidn/nuptk", "nidn_nuptk", "nidn", "nuptk"])
                    nip = _pick(row, ["nip"])
                    no_hp = _pick(row, ["nomor hp", "nomor_hp", "no_hp", "hp", "phone", "no hp"])
                    email = _pick(row, ["email", "e-mail", "mail"])

                    # minimal wajib
                    if not (nama and nidn_nuptk and nip):
                        failed += 1
                        errors.append(f"Baris {line_no}: wajib isi nama + nidn/nuptk + nip.")
                        continue

                    # validasi email jika ada
                    if email:
                        try:
                            validate_email(email)
                        except ValidationError:
                            failed += 1
                            errors.append(f"Baris {line_no}: email tidak valid: {email}")
                            continue

                    try:
                        # ========== MODE PREVIEW (DRY RUN) ==========
                        if dry_run:
                            nip_conflict = Dosen.objects.filter(nip=nip).exclude(nidn=nidn_nuptk).exists()
                            if nip_conflict:
                                raise ValidationError(f"NIP {nip} sudah dipakai dosen lain.")

                            dosen_exists = Dosen.objects.filter(nidn=nidn_nuptk).exists()
                            if create_only and dosen_exists:
                                skipped += 1
                                continue

                            user_exists = User.objects.filter(username=nip).exists()
                            if user_exists:
                                user = User.objects.get(username=nip)
                                if hasattr(user, "dosen_profile") and user.dosen_profile.nidn != nidn_nuptk:
                                    raise ValidationError(
                                        f"User {nip} sudah terhubung ke dosen lain ({user.dosen_profile.nidn})."
                                    )

                            if not dosen_exists:
                                created += 1
                            else:
                                dosen = Dosen.objects.get(nidn=nidn_nuptk)
                                need_update = False
                                if getattr(dosen, "nip", None) != nip:
                                    need_update = True
                                if getattr(dosen, "nama", None) != nama:
                                    need_update = True
                                if no_hp and getattr(dosen, "no_hp", "") != no_hp:
                                    need_update = True
                                if email and getattr(dosen, "email", "") != email:
                                    need_update = True
                                if need_update:
                                    updated += 1
                            continue

                        # ========== MODE REAL IMPORT (SIMPAN) ==========
                        with transaction.atomic():
                            nip_conflict = Dosen.objects.filter(nip=nip).exclude(nidn=nidn_nuptk).exists()
                            if nip_conflict:
                                raise ValidationError(f"NIP {nip} sudah dipakai dosen lain.")

                            if create_only and Dosen.objects.filter(nidn=nidn_nuptk).exists():
                                skipped += 1
                                continue

                            # USER: username = NIP
                            user, user_created = User.objects.get_or_create(
                                username=nip,
                                defaults={"email": email or "", "is_active": True},
                            )

                            if email and user.email != email:
                                user.email = email
                                user.save(update_fields=["email"])

                            # Password default = NIDN/NUPTK
                            if user_created or reset_password:
                                user.set_password(nidn_nuptk)
                                user.save()

                            if hasattr(user, "dosen_profile"):
                                existing = user.dosen_profile
                                if existing.nidn != nidn_nuptk:
                                    raise ValidationError(
                                        f"User {nip} sudah terhubung ke dosen lain ({existing.nidn})."
                                    )

                            dosen, dosen_created = Dosen.objects.get_or_create(
                                nidn=nidn_nuptk,
                                defaults={
                                    "user": user,
                                    "nip": nip,
                                    "nama": nama,
                                    "no_hp": no_hp,
                                    "email": email or "",
                                },
                            )

                            if dosen_created:
                                created += 1
                            else:
                                # Update MINIMAL field saja
                                changed = False
                                if dosen.user_id != user.id:
                                    dosen.user = user
                                    changed = True
                                if dosen.nip != nip:
                                    dosen.nip = nip
                                    changed = True
                                if dosen.nama != nama:
                                    dosen.nama = nama
                                    changed = True
                                if no_hp and (dosen.no_hp != no_hp):
                                    dosen.no_hp = no_hp
                                    changed = True
                                if email and (dosen.email != email):
                                    dosen.email = email
                                    changed = True

                                if changed:
                                    dosen.save()
                                    updated += 1

                    except (ValidationError, IntegrityError) as e:
                        failed += 1
                        errors.append(f"Baris {line_no}: gagal import (NIP={nip}) - {e}")
                    except Exception as e:
                        failed += 1
                        errors.append(f"Baris {line_no}: error tak terduga (NIP={nip}) - {e}")

                context = dict(
                    self.admin_site.each_context(request),
                    title=("Preview Import Dosen (CSV)" if dry_run else "Hasil Import Dosen (CSV)"),
                    dry_run=dry_run,
                    create_only=create_only,
                    reset_password=reset_password,
                    created=created,
                    updated=updated,
                    skipped=skipped,
                    failed=failed,
                    errors=errors,
                )
                if dry_run:
                    messages.info(request, f"PREVIEW: Create={created}, Update~={updated}, Skipped={skipped}, Failed={failed}.")
                else:
                    if failed:
                        messages.warning(request, f"Import selesai. Created={created}, Updated={updated}, Skipped={skipped}, Failed={failed}.")
                    else:
                        messages.success(request, f"Import sukses. Created={created}, Updated={updated}, Skipped={skipped}.")

                return TemplateResponse(request, "admin/masterdata/dosen/import_result.html", context)

        else:
            form = DosenCSVImportForm()

        context = dict(
            self.admin_site.each_context(request),
            title="Import Dosen (CSV)",
            form=form,
            help_columns="nidn/nuptk,nip,nama,email,nomor hp",
        )
        return TemplateResponse(request, "admin/masterdata/dosen/import_csv.html", context)

    def jumlah_mahasiswa_bimbingan(self, obj):
        return obj.mahasiswa_bimbingan.count()
    jumlah_mahasiswa_bimbingan.short_description = "Jml. Mahasiswa"

    def jumlah_logbook(self, obj):
        return LogbookEntry.objects.filter(mahasiswa__dosen_pembimbing=obj).count()
    jumlah_logbook.short_description = "Jml. Logbook"

    def jumlah_sesi_bimbingan(self, obj):
        return GuidanceSession.objects.filter(mahasiswa__dosen_pembimbing=obj).count()
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

    # Tombol import di change list mahasiswa
    change_list_template = "admin/masterdata/mahasiswa/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="masterdata_mahasiswa_import_csv",
            ),
        ]
        return my_urls + urls

    def import_csv(self, request):
        """
        Import Mahasiswa via CSV:
        kolom: nama,npm,nomor_hp,email,angkatan,tanggal_lahir

        Default:
        - User.username = npm
        - Password = tanggal_lahir (YYYYMMDD)
        - npm disimpan ke Mahasiswa.nim
        """
        if request.method == "POST":
            form = MahasiswaCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]
                create_only = form.cleaned_data["create_only"]
                reset_password = form.cleaned_data["reset_password"]

                created, updated, skipped, failed = 0, 0, 0, 0
                errors: list[str] = []

                text = f.read().decode("utf-8-sig", errors="replace")
                stream = io.StringIO(text)

                # delimiter auto (koma/semicolon/tab) - lebih tahan dari Sniffer
                first_line = stream.readline()
                stream.seek(0)
                counts = {",": first_line.count(","), ";": first_line.count(";"), "\t": first_line.count("\t")}
                delimiter = max(counts, key=counts.get)
                if counts[delimiter] == 0:
                    delimiter = ","

                def _norm_key(k: str) -> str:
                    k = (k or "").replace("\ufeff", "").strip().lower()
                    k = k.replace("\xa0", " ")
                    k = " ".join(k.split())
                    return k

                reader = csv.DictReader(stream, delimiter=delimiter, skipinitialspace=True)
                if not reader.fieldnames:
                    messages.error(request, "CSV tidak memiliki header.")
                    return TemplateResponse(
                        request,
                        "admin/masterdata/mahasiswa/import_csv.html",
                        dict(self.admin_site.each_context(request), title="Import Mahasiswa (CSV)", form=form),
                    )

                reader.fieldnames = [_norm_key(h) for h in reader.fieldnames]

                for line_no, raw in enumerate(reader, start=2):
                    row = {_norm_key(k): (v or "").strip() for k, v in raw.items()}

                    nama = _pick(row, ["nama", "name"])
                    npm = _pick(row, ["npm", "nim"])
                    no_hp = _pick(row, ["nomor_hp", "nomor hp", "no_hp", "hp", "phone"])
                    email = _pick(row, ["email", "e-mail", "mail"])
                    angkatan_raw = _pick(row, ["angkatan", "tahun_angkatan"])
                    tgl_raw = _pick(row, ["tanggal_lahir", "tgl_lahir", "tgl lahir", "dob"])

                    if not (nama and npm and angkatan_raw and tgl_raw):
                        failed += 1
                        errors.append(f"Baris {line_no}: wajib isi nama + npm + angkatan + tanggal_lahir.")
                        continue

                    # parse angkatan
                    try:
                        angkatan = int(angkatan_raw)
                    except ValueError:
                        failed += 1
                        errors.append(f"Baris {line_no}: angkatan harus angka: {angkatan_raw}")
                        continue

                    # parse tanggal lahir
                    try:
                        dob = _parse_date(tgl_raw)
                    except ValidationError as e:
                        failed += 1
                        errors.append(f"Baris {line_no}: {e}")
                        continue

                    if email:
                        try:
                            validate_email(email)
                        except ValidationError:
                            failed += 1
                            errors.append(f"Baris {line_no}: email tidak valid: {email}")
                            continue

                    try:
                        if dry_run:
                            mhs_exists = Mahasiswa.objects.filter(nim=npm).exists()
                            if create_only and mhs_exists:
                                skipped += 1
                                continue
                            if not mhs_exists:
                                created += 1
                            else:
                                # estimasi update minimal
                                m = Mahasiswa.objects.get(nim=npm)
                                need_update = False
                                if getattr(m, "nama", "") != nama:
                                    need_update = True
                                if no_hp and getattr(m, "no_hp", "") != no_hp:
                                    need_update = True
                                if email and getattr(m, "email", "") != email:
                                    need_update = True
                                if getattr(m, "angkatan", None) != angkatan:
                                    need_update = True
                                if hasattr(m, "tanggal_lahir") and getattr(m, "tanggal_lahir", None) != dob:
                                    need_update = True
                                if need_update:
                                    updated += 1
                            continue

                        with transaction.atomic():
                            if create_only and Mahasiswa.objects.filter(nim=npm).exists():
                                skipped += 1
                                continue

                            # USER: username = npm
                            user, user_created = User.objects.get_or_create(
                                username=npm,
                                defaults={"email": email or "", "is_active": True},
                            )

                            if email and user.email != email:
                                user.email = email
                                user.save(update_fields=["email"])

                            if user_created or reset_password:
                                user.set_password(_password_from_dob(dob))
                                user.save()

                            # MAHASISWA: create/update by nim
                            mhs, mhs_created = Mahasiswa.objects.get_or_create(
                                nim=npm,
                                defaults={
                                    "user": user,
                                    "nama": nama,
                                    "angkatan": angkatan,
                                    "no_hp": no_hp,
                                    "email": email or "",
                                    # kalau model kamu ada tanggal_lahir:
                                    **({"tanggal_lahir": dob} if hasattr(Mahasiswa, "tanggal_lahir") else {}),
                                },
                            )

                            if mhs_created:
                                created += 1
                            else:
                                changed = False
                                if getattr(mhs, "user_id", None) != user.id:
                                    mhs.user = user
                                    changed = True
                                if mhs.nama != nama:
                                    mhs.nama = nama
                                    changed = True
                                if mhs.angkatan != angkatan:
                                    mhs.angkatan = angkatan
                                    changed = True
                                if no_hp and (mhs.no_hp != no_hp):
                                    mhs.no_hp = no_hp
                                    changed = True
                                if email and (mhs.email != email):
                                    mhs.email = email
                                    changed = True
                                if hasattr(mhs, "tanggal_lahir") and (mhs.tanggal_lahir != dob):
                                    mhs.tanggal_lahir = dob
                                    changed = True

                                if changed:
                                    mhs.save()
                                    updated += 1

                    except (ValidationError, IntegrityError) as e:
                        failed += 1
                        errors.append(f"Baris {line_no}: gagal import (NPM={npm}) - {e}")
                    except Exception as e:
                        failed += 1
                        errors.append(f"Baris {line_no}: error tak terduga (NPM={npm}) - {e}")

                context = dict(
                    self.admin_site.each_context(request),
                    title=("Preview Import Mahasiswa (CSV)" if dry_run else "Hasil Import Mahasiswa (CSV)"),
                    dry_run=dry_run,
                    create_only=create_only,
                    reset_password=reset_password,
                    created=created,
                    updated=updated,
                    skipped=skipped,
                    failed=failed,
                    errors=errors,
                )
                if dry_run:
                    messages.info(request, f"PREVIEW: Create={created}, Update~={updated}, Skipped={skipped}, Failed={failed}.")
                else:
                    if failed:
                        messages.warning(request, f"Import selesai. Created={created}, Updated={updated}, Skipped={skipped}, Failed={failed}.")
                    else:
                        messages.success(request, f"Import sukses. Created={created}, Updated={updated}, Skipped={skipped}.")

                return TemplateResponse(request, "admin/masterdata/mahasiswa/import_result.html", context)

        else:
            form = MahasiswaCSVImportForm()

        context = dict(
            self.admin_site.each_context(request),
            title="Import Mahasiswa (CSV)",
            form=form,
            help_columns="nama,npm,nomor_hp,email,angkatan,tanggal_lahir",
        )
        return TemplateResponse(request, "admin/masterdata/mahasiswa/import_csv.html", context)


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
