from django.apps import AppConfig


class v0Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'v0'
    def ready(self):
        pass
