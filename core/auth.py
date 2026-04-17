from __future__ import annotations

from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse

from .models import Account, AccountSession

SESSION_ACCOUNT_ID_KEY = "account_id"


def get_current_account(request):
    account_id = request.session.get(SESSION_ACCOUNT_ID_KEY)
    if not account_id:
        return AccountSession()

    account = Account.objects.filter(id=account_id).first()
    if account is None:
        request.session.pop(SESSION_ACCOUNT_ID_KEY, None)
        return AccountSession()

    account.sync_daily_credits()
    return account


def login_account(request, account):
    request.session.cycle_key()
    request.session[SESSION_ACCOUNT_ID_KEY] = account.id
    request.session.modified = True
    request.session.save()  # Explicitly save session to ensure persistence
    request.user = account


def logout_account(request):
    request.session.flush()
    request.user = AccountSession()


def account_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            return redirect(f"{reverse('login')}?next={request.path}")
        return view_func(request, *args, **kwargs)

    return wrapped_view
