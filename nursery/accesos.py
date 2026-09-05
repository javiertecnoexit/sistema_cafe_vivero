"""Grupos y permisos por defecto según docs/plan.md §9 y docs/mobile.md §2.1.

"admin": acceso total (add/change/delete/view sobre todos los modelos).
"operario": captura (add/change/view sobre Medicion, Evaluacion, Evento, Foto),
alta de Planta y Bandeja (add/change/view sobre Planta; add/view sobre Bandeja)
y cambio de estado de Planta.
"""

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

MODELOS_CAPTURA = ("medicion", "evaluacion", "evento", "foto")
ACCIONES_TOTALES = ("add", "change", "delete", "view")


def _permisos_de_modelo(modelo, acciones):
    content_type = ContentType.objects.get_for_model(modelo)
    codenames = [f"{accion}_{modelo._meta.model_name}" for accion in acciones]
    return Permission.objects.filter(content_type=content_type, codename__in=codenames)


def crear_grupos_y_permisos(sender, **kwargs):
    grupo_admin, _ = Group.objects.get_or_create(name="admin")
    grupo_operario, _ = Group.objects.get_or_create(name="operario")
    modelos = apps.get_app_config("nursery").get_models()
    for modelo in modelos:
        grupo_admin.permissions.add(*_permisos_de_modelo(modelo, ACCIONES_TOTALES))
        modelo_nombre = modelo._meta.model_name
        if modelo_nombre in MODELOS_CAPTURA:
            grupo_operario.permissions.add(
                *_permisos_de_modelo(modelo, ("add", "change", "view"))
            )
        elif modelo_nombre == "planta":
            grupo_operario.permissions.add(
                *_permisos_de_modelo(modelo, ("add", "change", "view"))
            )
        elif modelo_nombre == "bandeja":
            grupo_operario.permissions.add(
                *_permisos_de_modelo(modelo, ("add", "view"))
            )
