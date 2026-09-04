import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from nursery.models import (
    Bandeja,
    EtapaFenologica,
    Evaluacion,
    Evento,
    Foto,
    Lote,
    Medicion,
    Planta,
    Proveedor,
    TipoEvento,
    TipoFoto,
    Variedad,
)


class ApiTests(APITestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = self.settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.usuario = get_user_model().objects.create_user(username="operario")
        self.usuario.groups.add(Group.objects.get(name="admin"))
        self.variedad_a = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.variedad_b = Variedad.objects.create(
            nombre="Bourbon", especie="Coffea arabica"
        )
        self.proveedor = Proveedor.objects.create(nombre="Vivero San Martín")
        self.etapa = EtapaFenologica.objects.create(nombre="Plántula", orden=1)
        self.tipo_evento = TipoEvento.objects.create(nombre="Riego")
        self.tipo_foto = TipoFoto.objects.create(nombre="Hoja")
        self.lote = Lote.objects.create(nombre="Invernadero A", tipo="invernadero")
        self.bandeja = Bandeja.objects.create(
            variedad=self.variedad_a, origen="propia"
        )
        self.planta_a = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad_a,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
            etapa=self.etapa,
            estado="activa",
        )
        self.planta_b = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad_b,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            estado="vendida",
        )
        self.medicion = Medicion.objects.create(
            planta=self.planta_a,
            fecha=date(2026, 9, 10),
            altura_cm=15.5,
            autor=self.usuario,
        )
        self.evaluacion = Evaluacion.objects.create(
            planta=self.planta_a,
            fecha=date(2026, 9, 10),
            score_vigor=4,
            score_sanidad=5,
            autor=self.usuario,
        )
        self.evento = Evento.create_individual(
            tipo=self.tipo_evento,
            fecha=date(2026, 9, 5),
            planta=self.planta_a,
            autor=self.usuario,
        )
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        self.foto = Foto.objects.create(
            planta=self.planta_a,
            imagen=SimpleUploadedFile(
                "foto.png", buffer.getvalue(), content_type="image/png"
            ),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 10),
            autor=self.usuario,
        )
        self.recursos = [
            ("variedad", self.variedad_a),
            ("proveedor", self.proveedor),
            ("etapafenologica", self.etapa),
            ("tipoevento", self.tipo_evento),
            ("tipofoto", self.tipo_foto),
            ("lote", self.lote),
            ("bandeja", self.bandeja),
            ("planta", self.planta_a),
            ("medicion", self.medicion),
            ("evaluacion", self.evaluacion),
            ("evento", self.evento),
            ("foto", self.foto),
        ]

    def test_get_lista_y_detalle_de_cada_recurso(self):
        for basename, instancia in self.recursos:
            with self.subTest(recurso=basename):
                lista = reverse(f"{basename}-list")
                detalle = reverse(f"{basename}-detail", args=[instancia.pk])
                self.assertEqual(self.client.get(lista).status_code, 200)
                self.assertEqual(self.client.get(detalle).status_code, 200)

    def test_post_autenticado_crea_recurso(self):
        self.client.force_authenticate(user=self.usuario)
        respuesta_variedad = self.client.post(
            reverse("variedad-list"),
            {"nombre": "Geisha", "especie": "Coffea arabica"},
            format="json",
        )
        self.assertEqual(respuesta_variedad.status_code, 201)
        respuesta_medicion = self.client.post(
            reverse("medicion-list"),
            {
                "planta": self.planta_a.pk,
                "fecha": "2026-09-11",
                "altura_cm": 18.0,
                "autor": self.usuario.pk,
            },
            format="json",
        )
        self.assertEqual(respuesta_medicion.status_code, 201)

    def test_post_sin_autenticacion_rechazado(self):
        cliente_anonimo = APIClient()
        respuesta = cliente_anonimo.post(
            reverse("variedad-list"),
            {"nombre": "Geisha", "especie": "Coffea arabica"},
            format="json",
        )
        self.assertIn(respuesta.status_code, (401, 403))

    def test_filtrado_de_plantas(self):
        filtro = self.client.get(
            reverse("planta-list"),
            {"variedad": self.variedad_a.pk, "estado": "activa"},
        )
        self.assertEqual(filtro.status_code, 200)
        codigos = [item["codigo"] for item in filtro.data]
        self.assertEqual(codigos, ["CAT-0001"])
        filtro_vendida = self.client.get(
            reverse("planta-list"), {"estado": "vendida"}
        )
        codigos_vendida = [item["codigo"] for item in filtro_vendida.data]
        self.assertEqual(codigos_vendida, ["CAT-0002"])


class PermisosApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_user")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.operario = get_user_model().objects.create_user(username="operario_user")
        self.operario.groups.add(Group.objects.get(name="operario"))
        self.sin_grupo = get_user_model().objects.create_user(username="sin_grupo")
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.tipo_evento = TipoEvento.objects.create(nombre="Riego")

    def _crear_medicion(self, cliente):
        return cliente.post(
            reverse("medicion-list"),
            {
                "planta": self.planta.pk,
                "fecha": "2026-09-11",
                "altura_cm": 18.0,
                "autor": self.operario.pk,
            },
            format="json",
        )

    def test_operario_puede_crear_medicion(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.operario)
        self.assertEqual(self._crear_medicion(cliente).status_code, 201)

    def test_operario_puede_crear_evento(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.operario)
        respuesta = cliente.post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_evento.pk,
                "fecha": "2026-09-11",
                "autor": self.operario.pk,
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_operario_no_puede_crear_variedad(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.operario)
        respuesta = cliente.post(
            reverse("variedad-list"),
            {"nombre": "Geisha", "especie": "Coffea arabica"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_admin_puede_crear_variedad(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.admin)
        respuesta = cliente.post(
            reverse("variedad-list"),
            {"nombre": "Geisha", "especie": "Coffea arabica"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_autenticado_sin_grupo_no_puede_crear_variedad(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.sin_grupo)
        respuesta = cliente.post(
            reverse("variedad-list"),
            {"nombre": "Geisha", "especie": "Coffea arabica"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 403)


class RefuerzoApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_refuerzo")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.tipo_riego = TipoEvento.objects.create(nombre="Riego")
        self.tipo_fito = TipoEvento.objects.create(nombre="Fitosanitario")

    def _cliente(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.admin)
        return cliente

    def test_medicion_sin_autor_usa_request_user(self):
        respuesta = self._cliente().post(
            reverse("medicion-list"),
            {
                "planta": self.planta.pk,
                "fecha": "2026-09-11",
                "altura_cm": 12.0,
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        medicion = Medicion.objects.get(pk=respuesta.data["id"])
        self.assertEqual(medicion.autor, self.admin)

    def test_evento_fitosanitario_api_incrementa(self):
        respuesta = self._cliente().post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_fito.pk,
                "fecha": "2026-09-11",
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        evento = Evento.objects.get(pk=respuesta.data["id"])
        self.assertEqual(evento.autor, self.admin)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.n_eventos_fitosanitarios, 1)

    def test_delete_evento_fitosanitario_decrementa_sin_bajar_de_cero(self):
        cliente = self._cliente()
        respuesta = cliente.post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_fito.pk,
                "fecha": "2026-09-11",
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        evento_pk = respuesta.data["id"]
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.n_eventos_fitosanitarios, 1)
        respuesta_delete = cliente.delete(
            reverse("evento-detail", args=[evento_pk])
        )
        self.assertEqual(respuesta_delete.status_code, 204)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.n_eventos_fitosanitarios, 0)
        respuesta = cliente.post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_fito.pk,
                "fecha": "2026-09-12",
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        evento_pk = respuesta.data["id"]
        Planta.objects.filter(pk=self.planta.pk).update(
            n_eventos_fitosanitarios=0
        )
        cliente.delete(reverse("evento-detail", args=[evento_pk]))
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.n_eventos_fitosanitarios, 0)

    def test_evento_no_fitosanitario_no_incrementa(self):
        respuesta = self._cliente().post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_riego.pk,
                "fecha": "2026-09-11",
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.n_eventos_fitosanitarios, 0)


class CongelamientoSalidaApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_congela")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            estado="vendida",
            fecha_baja=date(2026, 9, 20),
            motivo_baja="Venta",
        )
        self.tipo_evento = TipoEvento.objects.create(nombre="Riego")
        self.tipo_foto = TipoFoto.objects.create(nombre="Hoja")

    def _cliente(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.admin)
        return cliente

    def _imagen(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            "foto.png", buffer.getvalue(), content_type="image/png"
        )

    def test_post_medicion_sobre_salida_400(self):
        respuesta = self._cliente().post(
            reverse("medicion-list"),
            {
                "planta": self.planta.pk,
                "fecha": "2026-09-21",
                "altura_cm": 12.0,
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Medicion.objects.count(), 0)

    def test_post_evento_sobre_salida_400(self):
        respuesta = self._cliente().post(
            reverse("evento-list"),
            {
                "tipo": self.tipo_evento.pk,
                "fecha": "2026-09-21",
                "plantas": [self.planta.pk],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Evento.objects.count(), 0)

    def test_post_foto_sobre_salida_400(self):
        respuesta = self._cliente().post(
            reverse("foto-list"),
            {
                "imagen": self._imagen(),
                "tipo": self.tipo_foto.pk,
                "fecha": "2026-09-21",
                "activa": True,
            },
            format="multipart",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Foto.objects.count(), 0)


class ResincronizacionEventoApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_resync")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.planta_1 = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.planta_2 = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.tipo_riego = TipoEvento.objects.create(nombre="Riego")
        self.tipo_fito = TipoEvento.objects.create(nombre="Fitosanitario")

    def _cliente(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.admin)
        return cliente

    def _crear_evento(self, tipo, plantas):
        cliente = self._cliente()
        respuesta = cliente.post(
            reverse("evento-list"),
            {
                "tipo": tipo.pk,
                "fecha": "2026-09-11",
                "plantas": [planta.pk for planta in plantas],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.data["id"]

    def test_patch_tipo_a_fitosanitario_incrementa(self):
        evento_pk = self._crear_evento(self.tipo_riego, [self.planta_1])
        respuesta = self._cliente().patch(
            reverse("evento-detail", args=[evento_pk]),
            {"tipo": self.tipo_fito.pk},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)

    def test_patch_tipo_desde_fitosanitario_decrementa(self):
        evento_pk = self._crear_evento(self.tipo_fito, [self.planta_1])
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)
        respuesta = self._cliente().patch(
            reverse("evento-detail", args=[evento_pk]),
            {"tipo": self.tipo_riego.pk},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 0)

    def test_patch_m2m_resincroniza(self):
        evento_pk = self._crear_evento(
            self.tipo_fito, [self.planta_1, self.planta_2]
        )
        self.planta_1.refresh_from_db()
        self.planta_2.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)
        self.assertEqual(self.planta_2.n_eventos_fitosanitarios, 1)
        respuesta = self._cliente().patch(
            reverse("evento-detail", args=[evento_pk]),
            {"plantas": [self.planta_2.pk]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.planta_1.refresh_from_db()
        self.planta_2.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 0)
        self.assertEqual(self.planta_2.n_eventos_fitosanitarios, 1)

