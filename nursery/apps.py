from django.apps import AppConfig
from django.db.models.signals import post_migrate


class NurseryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nursery'

    def ready(self):
        from .accesos import crear_grupos_y_permisos

        post_migrate.connect(crear_grupos_y_permisos, sender=self)

