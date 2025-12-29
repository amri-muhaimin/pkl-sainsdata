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

    # kalau user dosen
    if hasattr(user, "dosen_profile"):
        dosen = user.dosen_profile

        # aman: support beberapa nama field
        is_koor = (
            getattr(dosen, "is_koordinator_pkl", None)
            if getattr(dosen, "is_koordinator_pkl", None) is not None
            else getattr(dosen, "is_koordinator", False)
        )

        if is_koor:
            return redirect("portal:koordinator_dashboard")
        return redirect("portal:dosen_dashboard")

    # kalau user mahasiswa
    if hasattr(user, "mahasiswa_profile"):
        return redirect("portal:mahasiswa_dashboard")

    # fallback
    return redirect("portal:login")

