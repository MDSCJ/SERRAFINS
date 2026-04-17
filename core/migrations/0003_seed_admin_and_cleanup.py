import os

from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.utils import timezone


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "m.d.s.chamath@gmail.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "qwertyuiop")
ADMIN_CREDITS = 999999


def seed_admin_account(apps, schema_editor):
    Account = apps.get_model("core", "Account")
    account, created = Account.objects.get_or_create(
        email=ADMIN_EMAIL,
        defaults={
            "username": ADMIN_EMAIL.split("@")[0],
            "password": make_password(ADMIN_PASSWORD),
            "credits": ADMIN_CREDITS,
            "last_reset_date": timezone.localdate(),
            "auth_provider": "local",
            "is_staff": True,
            "is_superuser": True,
        },
    )

    if not created:
        account.username = account.username or ADMIN_EMAIL.split("@")[0]
        account.password = make_password(ADMIN_PASSWORD)
        account.credits = ADMIN_CREDITS
        account.last_reset_date = timezone.localdate()
        account.auth_provider = "local"
        account.is_staff = True
        account.is_superuser = True
        account.save()


def cleanup_legacy_tables(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table_name in [
            "django_admin_log",
            "auth_group_permissions",
            "auth_user_user_permissions",
            "auth_user_groups",
            "auth_permission",
            "auth_group",
            "auth_user",
            "core_userprofile",
            "django_content_type",
        ]:
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_account"),
    ]

    operations = [
        migrations.RunPython(seed_admin_account, migrations.RunPython.noop),
        migrations.RunPython(cleanup_legacy_tables, migrations.RunPython.noop),
    ]
