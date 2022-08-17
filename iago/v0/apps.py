from django.apps import AppConfig

class v0Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'v0'
    def ready(self):
        """ Run any code that needs to be run when the app is ready. """
        from v0.index import ready
        ready()
