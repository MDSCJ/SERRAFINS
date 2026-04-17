from __future__ import annotations

import os

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "m.d.s.chamath@gmail.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "qwertyuiop")
DEFAULT_DAILY_CREDITS = 100
ADMIN_CREDITS = 999999
CNN_IMAGE_COST = 10


class Account(models.Model):
    AUTH_PROVIDER_LOCAL = "local"
    AUTH_PROVIDER_GOOGLE = "google"
    AUTH_PROVIDER_CHOICES = (
        (AUTH_PROVIDER_LOCAL, "Local username/password"),
        (AUTH_PROVIDER_GOOGLE, "Google"),
    )

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    credits = models.PositiveIntegerField(default=DEFAULT_DAILY_CREDITS)
    last_reset_date = models.DateField(default=timezone.localdate)
    auth_provider = models.CharField(max_length=20, choices=AUTH_PROVIDER_CHOICES, default=AUTH_PROVIDER_LOCAL)
    google_sub = models.CharField(max_length=128, blank=True, default="")
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def is_admin_email(self) -> bool:
        return (self.email or "").strip().lower() == ADMIN_EMAIL

    def set_password(self, raw_password: str | None) -> None:
        self.password = make_password(raw_password)

    def set_unusable_password(self) -> None:
        self.password = make_password(None)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def sync_daily_credits(self, force: bool = False) -> bool:
        today = timezone.localdate()

        if self.is_admin_email():
            if self.credits != ADMIN_CREDITS or self.last_reset_date != today:
                self.credits = ADMIN_CREDITS
                self.last_reset_date = today
                self.save(update_fields=["credits", "last_reset_date", "updated_at"])
            return True

        if force or self.last_reset_date != today:
            self.credits = DEFAULT_DAILY_CREDITS
            self.last_reset_date = today
            self.save(update_fields=["credits", "last_reset_date", "updated_at"])
            return True

        return False

    def set_initial_credits(self) -> None:
        if self.is_admin_email():
            self.credits = ADMIN_CREDITS
        else:
            self.credits = DEFAULT_DAILY_CREDITS
        self.last_reset_date = timezone.localdate()
        # New objects do not have a primary key yet, so defer DB update until first save.
        if self.pk:
            self.save(update_fields=["credits", "last_reset_date", "updated_at"])

    def can_spend(self, amount: int = CNN_IMAGE_COST) -> bool:
        if self.is_admin_email():
            return True
        return self.credits >= amount

    def spend(self, amount: int = CNN_IMAGE_COST) -> bool:
        self.sync_daily_credits()
        if not self.can_spend(amount):
            return False

        if not self.is_admin_email():
            self.credits = max(0, self.credits - amount)
            self.save(update_fields=["credits", "updated_at"])

        return True


class AccountSession:
    is_authenticated = False
    is_anonymous = True
    username = ""
    email = ""
    credits = 0
    id = None
