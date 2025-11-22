from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = "portal"

urlpatterns = [
    # Auth
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="portal/login.html"
        ),
        name="login",
    ),
    path(
        "logout/",
        views.portal_logout,
        name="logout",
    ),

    path("after-login/", views.after_login, name="after_login"),

    # Dosen
    path("dosen/", views.dosen_list, name="dosen_list"),
    path("dosen/dashboard/", views.dosen_dashboard, name="dosen_dashboard"),
    path(
        "dosen/mahasiswa/<int:mahasiswa_id>/",
        views.dosen_mahasiswa_detail,
        name="dosen_mahasiswa_detail",
    ),
    path(
        "dosen/logbook/<int:logbook_id>/review/",
        views.dosen_logbook_review,
        name="dosen_logbook_review",
    ),
    path(
        "dosen/logbook/export/",
        views.dosen_logbook_export,
        name="dosen_logbook_export",
    ),
    path(
        "dosen/guidance/export/",
        views.dosen_guidance_export,
        name="dosen_guidance_export",
    ),

    # Mahasiswa
    path(
        "mhs/dashboard/",
        views.mahasiswa_dashboard,
        name="mahasiswa_dashboard",
    ),
    path(
        "mhs/logbook/add/",
        views.mahasiswa_logbook_add,
        name="mahasiswa_logbook_add",
    ),
    path(
        "mhs/logbook/export/",
        views.mahasiswa_logbook_export,
        name="mahasiswa_logbook_export",
    ),
    path(
        "mhs/dashboard/",
        views.mahasiswa_dashboard,
        name="mahasiswa_dashboard",
    ),
    path(
        "mhs/logbook/add/",
        views.mahasiswa_logbook_add,
        name="mahasiswa_logbook_add",
    ),
    path(
        "mhs/logbook/export/",
        views.mahasiswa_logbook_export,
        name="mahasiswa_logbook_export",
    ),
    path(
        "mhs/pendaftaran/",
        views.mahasiswa_pendaftaran_pkl,
        name="mahasiswa_pendaftaran_pkl",
    ),    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
