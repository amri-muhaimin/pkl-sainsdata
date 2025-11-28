from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def portal_logout(request):
    logout(request)
    return redirect("portal:login")


@login_required
def after_login(request):
    user = request.user

    # Jika akun dosen
    if hasattr(user, "dosen_profile"):
        dosen = user.dosen_profile
        if dosen.is_koordinator_pkl:
            return redirect("portal:koordinator_dashboard")
        return redirect("portal:dosen_dashboard")

    # Jika akun mahasiswa
    if hasattr(user, "mahasiswa_profile"):
        return redirect("portal:mahasiswa_dashboard")

    # Jika bukan keduanya
    return HttpResponseForbidden(
        "Akun ini belum dihubungkan ke data Dosen atau Mahasiswa."
    )
