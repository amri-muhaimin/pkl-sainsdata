from .views_auth import portal_logout, after_login
from .views_dosen import (
    dosen_list,
    dosen_dashboard,
    dosen_mahasiswa_detail,
    dosen_logbook_review,
    dosen_logbook_export,
    dosen_guidance_list,
    dosen_guidance_detail,
    dosen_guidance_export,
    dosen_seminar_list,
    dosen_seminar_detail,
    dosen_seminar_penilaian
    dosen_pembimbing_penilaian,
    seminar_penilaian_pdf,
    koordinator_dashboard,
    koordinator_pendaftaran_list,
    koordinator_pendaftaran_detail,
    koordinator_pemetaan,
    koordinator_seminar_list,
    koordinator_seminar_detail,
    koordinator_dosen_kuota,
)
from .views_mahasiswa import (
    mahasiswa_dashboard,
    mahasiswa_logbook_add,
    mahasiswa_logbook_export,
    mahasiswa_guidance_list,
    mahasiswa_guidance_create,
    mahasiswa_pendaftaran_pkl,
    mahasiswa_seminar_pendaftaran,
)

__all__ = [
    # Auth
    "portal_logout",
    "after_login",
    # Dosen
    "dosen_list",
    "dosen_dashboard",
    "dosen_mahasiswa_detail",
    "dosen_logbook_review",
    "dosen_logbook_export",
    "dosen_guidance_list",
    "dosen_guidance_detail",
    "dosen_guidance_export",
    "dosen_seminar_list",
    "dosen_seminar_detail",
    "dosen_seminar_penilaian",
    "dosen_pembimbing_penilaian",
    "seminar_penilaian_pdf",
    # Koordinator
    "koordinator_dashboard",
    "koordinator_pendaftaran_list",
    "koordinator_pendaftaran_detail",
    "koordinator_pemetaan",
    "koordinator_seminar_list",
    "koordinator_seminar_detail",
    "koordinator_dosen_kuota",
    # Mahasiswa
    "mahasiswa_dashboard",
    "mahasiswa_logbook_add",
    "mahasiswa_logbook_export",
    "mahasiswa_guidance_list",
    "mahasiswa_guidance_create",
    "mahasiswa_pendaftaran_pkl",
    "mahasiswa_seminar_pendaftaran",
]
