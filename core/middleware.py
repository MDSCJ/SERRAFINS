from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect

from .auth import get_current_account


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Keep local development on a single host to avoid split session cookies.
        if settings.DEBUG and request.get_host().startswith("localhost"):
            target = request.build_absolute_uri().replace("localhost", "127.0.0.1", 1)
            return redirect(target)
        return self.get_response(request)


class AccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = get_current_account(request)
        return self.get_response(request)
