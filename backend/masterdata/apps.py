from django.apps import AppConfig


class MasterdataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "masterdata"

    def ready(self):
        # Import signal supaya terdaftar saat app ready
        from . import signals  # noqa: F401
