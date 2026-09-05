import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from nursery.models import (
    EtapaFenologica,
    Lote,
    TipoEvento,
    TipoFoto,
    Variedad,
)

VARIEDADES = ["Catuaí", "Bourbon", "Geisha"]
TIPOS_EVENTO = [
    "Trasplante",
    "Fitosanitario",
    "Fertilización",
    "Riego",
    "Poda",
    "Observación",
    "Cosecha",
]
TIPOS_FOTO = ["General", "Hoja", "Evento", "Otra"]
ETAPAS = [("Germinación", 1), ("Plántula", 2), ("Juvenil", 3)]


class Command(BaseCommand):
    help = "Crea superusuario, usuario operario y catálogos iniciales (idempotente)."

    def handle(self, *args, **options):
        created = {"variedad": 0, "tipoevento": 0, "tipofoto": 0, "etapa": 0}
        for nombre in VARIEDADES:
            _, nuevo = Variedad.objects.get_or_create(
                nombre=nombre, especie="Coffea arabica"
            )
            created["variedad"] += int(nuevo)
        for nombre in TIPOS_EVENTO:
            _, nuevo = TipoEvento.objects.get_or_create(nombre=nombre)
            created["tipoevento"] += int(nuevo)
        for nombre in TIPOS_FOTO:
            _, nuevo = TipoFoto.objects.get_or_create(nombre=nombre)
            created["tipofoto"] += int(nuevo)
        for nombre, orden in ETAPAS:
            _, nuevo = EtapaFenologica.objects.get_or_create(
                nombre=nombre, orden=orden
            )
            created["etapa"] += int(nuevo)
        _, lote_nuevo = Lote.objects.get_or_create(
            nombre="Invernadero A", tipo="invernadero"
        )

        grupo_operario, _ = Group.objects.get_or_create(name="operario")
        User = get_user_model()

        username_admin = os.environ.get(
            "DJANGO_SUPERUSER_USERNAME", "admin"
        )
        password_admin = os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD", "admin12345"
        )
        admin, admin_nuevo = User.objects.get_or_create(
            username=username_admin
        )
        if admin_nuevo:
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(password_admin)
            admin.save()

        usuario_operario = "operario"
        password_operario = os.environ.get(
            "SEED_OPERARIO_PASSWORD", "clave12345"
        )
        operario, operario_nuevo = User.objects.get_or_create(
            username=usuario_operario
        )
        if operario_nuevo:
            operario.set_password(password_operario)
            operario.save()
        operario.groups.add(grupo_operario)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed completado: "
                f"variedades {created['variedad']} nuevas, "
                f"tipos de evento {created['tipoevento']} nuevos, "
                f"tipos de foto {created['tipofoto']} nuevos, "
                f"etapas {created['etapa']} nuevas, "
                f"lote {'creado' if lote_nuevo else 'ya existía'}, "
                f"admin {'creado' if admin_nuevo else 'ya existía'} "
                f"({username_admin}), "
                f"operario {'creado' if operario_nuevo else 'ya existía'}."
            )
        )
