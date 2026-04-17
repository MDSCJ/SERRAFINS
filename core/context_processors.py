from .models import AccountSession


def auth_profile(request):
    request_user = getattr(request, "user", None)
    if request_user is None:
        request_user = AccountSession()

    account = request_user if getattr(request_user, "is_authenticated", False) else None

    return {
        "user": request_user,
        "auth_profile": account,
    }
