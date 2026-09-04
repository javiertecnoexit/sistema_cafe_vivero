import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .etiquetas import (
    generar_codigos,
    generar_pdf_etiquetas,
    obtener_prefijo,
    validar_codigo_disponible,
)
from .seleccion import calcular_indice
from .models import (
    Bandeja,
    CambioEstado,
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


class CatalogoModelTests(TestCase):
    def test_crear_variedad(self):
        variedad = Variedad.objects.create(nombre="Catuaí", especie="Coffea arabica")
        self.assertEqual(variedad.nombre, "Catuaí")
        self.assertEqual(variedad.especie, "Coffea arabica")

    def test_variedad_nombre_unique(self):
        Variedad.objects.create(nombre="Catuaí", especie="Coffea arabica")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Variedad.objects.create(
                    nombre="Catuaí", especie="Coffea arabica"
                )

    def test_crear_proveedor(self):
        proveedor = Proveedor.objects.create(nombre="Vivero San Martín")
        self.assertEqual(proveedor.nombre, "Vivero San Martín")
        self.assertEqual(proveedor.contacto, "")

    def test_crear_etapa_fenologica(self):
        etapa = EtapaFenologica.objects.create(nombre="Germinación", orden=1)
        self.assertEqual(etapa.nombre, "Germinación")
        self.assertEqual(etapa.orden, 1)

    def test_crear_tipo_evento(self):
        tipo = TipoEvento.objects.create(nombre="Riego")
        self.assertEqual(tipo.nombre, "Riego")

    def test_crear_tipo_foto(self):
        tipo = TipoFoto.objects.create(nombre="Hoja")
        self.assertEqual(tipo.nombre, "Hoja")

    def test_crear_lote(self):
        lote = Lote.objects.create(nombre="Invernadero A", tipo="invernadero")
        self.assertEqual(lote.nombre, "Invernadero A")
        self.assertEqual(lote.tipo, "invernadero")
        self.assertEqual(lote.ubicacion, "")

    def test_crear_bandeja_con_proveedor(self):
        variedad = Variedad.objects.create(nombre="Bourbon", especie="Coffea arabica")
        proveedor = Proveedor.objects.create(nombre="Vivero San Martín")
        bandeja = Bandeja.objects.create(
            variedad=variedad,
            origen="proveedor",
            proveedor=proveedor,
            fecha_siembra="2026-08-01",
            n_semillas=50,
        )
        self.assertEqual(bandeja.variedad, variedad)
        self.assertEqual(bandeja.origen, "proveedor")
        self.assertEqual(bandeja.proveedor, proveedor)
        self.assertEqual(bandeja.n_semillas, 50)

    def test_bandeja_proveedor_puede_ser_null(self):
        variedad = Variedad.objects.create(nombre="Geisha", especie="Coffea arabica")
        bandeja = Bandeja.objects.create(
            variedad=variedad,
            origen="propia",
            fecha_siembra=None,
            n_semillas=None,
        )
        self.assertIsNone(bandeja.proveedor)
        self.assertIsNone(bandeja.fecha_siembra)
        self.assertIsNone(bandeja.n_semillas)


class PlantaModelTests(TestCase):
    def _crear_variedad(self, nombre="Catuaí"):
        return Variedad.objects.create(nombre=nombre, especie="Coffea arabica")

    def test_crear_planta_valida(self):
        variedad = self._crear_variedad()
        bandeja = Bandeja.objects.create(variedad=variedad, origen="propia")
        lote = Lote.objects.create(nombre="Invernadero A", tipo="invernadero")
        planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            bandeja=bandeja,
            fecha_alta="2026-09-01",
            contenedor="maceta",
            lote=lote,
        )
        self.assertEqual(planta.codigo, "CAT-0001")
        self.assertEqual(planta.variedad, variedad)
        self.assertEqual(planta.bandeja, bandeja)
        self.assertEqual(planta.lote, lote)
        self.assertEqual(planta.contenedor, "maceta")
        self.assertEqual(planta.estado, "activa")

    def test_token_publico_autogenerado_y_distinto(self):
        variedad = self._crear_variedad()
        planta_1 = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta="2026-09-01",
            contenedor="maceta",
        )
        planta_2 = Planta.objects.create(
            codigo="CAT-0002",
            variedad=variedad,
            origen="propia",
            fecha_alta="2026-09-01",
            contenedor="maceta",
        )
        self.assertIsNotNone(planta_1.token_publico)
        self.assertIsNotNone(planta_2.token_publico)
        self.assertNotEqual(planta_1.token_publico, planta_2.token_publico)

    def test_codigo_unique(self):
        variedad = self._crear_variedad()
        Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta="2026-09-01",
            contenedor="maceta",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Planta.objects.create(
                    codigo="CAT-0001",
                    variedad=variedad,
                    origen="propia",
                    fecha_alta="2026-09-01",
                    contenedor="maceta",
                )

    def test_valores_por_defecto(self):
        variedad = self._crear_variedad()
        planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta="2026-09-01",
            contenedor="maceta",
        )
        self.assertEqual(planta.n_eventos_fitosanitarios, 0)
        self.assertFalse(planta.publico_activo)
        self.assertIsNone(planta.ultima_altura)
        self.assertIsNone(planta.ultimo_diametro)
        self.assertIsNone(planta.ultima_fecha_medicion)
        self.assertIsNone(planta.tasa_crecimiento)
        self.assertIsNone(planta.indice_esbeltez)
        self.assertIsNone(planta.score_vigor_actual)
        self.assertIsNone(planta.score_sanidad_actual)


class MedicionEvaluacionModelTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="operario")
        variedad = Variedad.objects.create(nombre="Catuaí", especie="Coffea arabica")
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta="2026-09-01",
            contenedor="maceta",
        )

    def test_crear_medicion_valida(self):
        medicion = Medicion.objects.create(
            planta=self.planta,
            fecha=date(2026, 9, 10),
            altura_cm=15.5,
            diametro_tallo_mm=3.2,
            autor=self.usuario,
        )
        self.assertEqual(medicion.planta, self.planta)
        self.assertEqual(medicion.fecha, date(2026, 9, 10))
        self.assertEqual(medicion.altura_cm, 15.5)
        self.assertEqual(medicion.diametro_tallo_mm, 3.2)
        self.assertEqual(medicion.autor, self.usuario)

    def test_crear_evaluacion_valida(self):
        evaluacion = Evaluacion.objects.create(
            planta=self.planta,
            fecha="2026-09-10",
            score_vigor=4,
            score_sanidad=5,
            autor=self.usuario,
        )
        self.assertEqual(evaluacion.planta, self.planta)
        self.assertEqual(evaluacion.score_vigor, 4)
        self.assertEqual(evaluacion.score_sanidad, 5)
        self.assertEqual(evaluacion.autor, self.usuario)

    def test_score_vigor_fuera_de_rango_rechazado(self):
        for score in (0, 6):
            with self.subTest(score=score):
                evaluacion = Evaluacion(
                    planta=self.planta,
                    fecha="2026-09-10",
                    score_vigor=score,
                    score_sanidad=3,
                    autor=self.usuario,
                )
                with self.assertRaises(ValidationError):
                    evaluacion.full_clean()

    def test_score_sanidad_fuera_de_rango_rechazado(self):
        for score in (0, 6):
            with self.subTest(score=score):
                evaluacion = Evaluacion(
                    planta=self.planta,
                    fecha="2026-09-10",
                    score_vigor=3,
                    score_sanidad=score,
                    autor=self.usuario,
                )
                with self.assertRaises(ValidationError):
                    evaluacion.full_clean()

    def test_autor_guardado_en_medicion_y_evaluacion(self):
        medicion = Medicion.objects.create(
            planta=self.planta,
            fecha="2026-09-10",
            altura_cm=15.5,
            autor=self.usuario,
        )
        evaluacion = Evaluacion.objects.create(
            planta=self.planta,
            fecha="2026-09-10",
            score_vigor=4,
            score_sanidad=4,
            autor=self.usuario,
        )
        self.assertEqual(medicion.autor, self.usuario)
        self.assertEqual(evaluacion.autor, self.usuario)


class MetricaDenormalizadaTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="operario")
        variedad = Variedad.objects.create(nombre="Catuaí", especie="Coffea arabica")
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )

    def _crear_medicion(self, fecha, altura_cm=None, diametro_tallo_mm=None):
        return Medicion.objects.create(
            planta=self.planta,
            fecha=fecha,
            altura_cm=altura_cm,
            diametro_tallo_mm=diametro_tallo_mm,
            autor=self.usuario,
        )

    def _crear_evaluacion(self, fecha, score_vigor, score_sanidad):
        return Evaluacion.objects.create(
            planta=self.planta,
            fecha=fecha,
            score_vigor=score_vigor,
            score_sanidad=score_sanidad,
            autor=self.usuario,
        )

    def test_esbeltez_correcta(self):
        self._crear_medicion(
            date(2026, 9, 1), altura_cm=10, diametro_tallo_mm=2
        )
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.indice_esbeltez, 5.0)
        self.assertEqual(self.planta.ultima_altura, 10.0)
        self.assertEqual(self.planta.ultimo_diametro, 2.0)
        self.assertEqual(self.planta.ultima_fecha_medicion, date(2026, 9, 1))

    def test_esbeltez_none_si_falta_altura_o_diametro(self):
        self._crear_medicion(
            date(2026, 9, 1), altura_cm=10, diametro_tallo_mm=None
        )
        self.planta.refresh_from_db()
        self.assertIsNone(self.planta.indice_esbeltez)
        self._crear_medicion(
            date(2026, 9, 2), altura_cm=None, diametro_tallo_mm=3
        )
        self.planta.refresh_from_db()
        self.assertIsNone(self.planta.indice_esbeltez)
        self.assertIsNone(self.planta.ultima_altura)

    def test_tasa_crecimiento_con_dos_mediciones(self):
        self._crear_medicion(date(2026, 9, 1), altura_cm=10)
        self._crear_medicion(date(2026, 9, 8), altura_cm=17)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.tasa_crecimiento, 7.0)
        self.assertEqual(self.planta.ultima_altura, 17.0)
        self.assertEqual(self.planta.ultima_fecha_medicion, date(2026, 9, 8))

    def test_tasa_crecimiento_none_con_una_medicion(self):
        self._crear_medicion(date(2026, 9, 1), altura_cm=10)
        self.planta.refresh_from_db()
        self.assertIsNone(self.planta.tasa_crecimiento)

    def test_scores_actualizados_tras_nueva_evaluacion(self):
        self._crear_evaluacion(date(2026, 9, 1), score_vigor=3, score_sanidad=4)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.score_vigor_actual, 3)
        self.assertEqual(self.planta.score_sanidad_actual, 4)
        self._crear_evaluacion(date(2026, 9, 10), score_vigor=5, score_sanidad=5)
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.score_vigor_actual, 5)
        self.assertEqual(self.planta.score_sanidad_actual, 5)

    def test_borrar_medicion_recalcula_denormalizados(self):
        self._crear_medicion(
            date(2026, 9, 1), altura_cm=10, diametro_tallo_mm=2
        )
        medicion_reciente = self._crear_medicion(
            date(2026, 9, 10), altura_cm=20, diametro_tallo_mm=4
        )
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.ultima_altura, 20.0)
        medicion_reciente.delete()
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.ultima_altura, 10.0)
        self.assertEqual(self.planta.ultimo_diametro, 2.0)
        self.assertEqual(self.planta.ultima_fecha_medicion, date(2026, 9, 1))
        self.assertEqual(self.planta.indice_esbeltez, 5.0)
        self.assertIsNone(self.planta.tasa_crecimiento)

    def test_borrar_ultima_medicion_deja_denormalizados_none(self):
        medicion = self._crear_medicion(
            date(2026, 9, 1), altura_cm=10, diametro_tallo_mm=2
        )
        medicion.delete()
        self.planta.refresh_from_db()
        self.assertIsNone(self.planta.ultima_altura)
        self.assertIsNone(self.planta.ultimo_diametro)
        self.assertIsNone(self.planta.ultima_fecha_medicion)
        self.assertIsNone(self.planta.indice_esbeltez)
        self.assertIsNone(self.planta.tasa_crecimiento)

    def test_borrar_evaluacion_recalcula_scores(self):
        self._crear_evaluacion(date(2026, 9, 1), score_vigor=3, score_sanidad=4)
        evaluacion_reciente = self._crear_evaluacion(
            date(2026, 9, 10), score_vigor=5, score_sanidad=5
        )
        evaluacion_reciente.delete()
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.score_vigor_actual, 3)
        self.assertEqual(self.planta.score_sanidad_actual, 4)

    def test_borrar_ultima_evaluacion_deja_scores_none(self):
        evaluacion = self._crear_evaluacion(
            date(2026, 9, 1), score_vigor=3, score_sanidad=4
        )
        evaluacion.delete()
        self.planta.refresh_from_db()
        self.assertIsNone(self.planta.score_vigor_actual)
        self.assertIsNone(self.planta.score_sanidad_actual)


class EventoModelTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="operario")
        self.tipo_riego = TipoEvento.objects.create(nombre="Riego")
        self.tipo_fitosanitario = TipoEvento.objects.create(nombre="Fitosanitario")
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.lote = Lote.objects.create(nombre="Lote A", tipo="lote")
        self.planta_1 = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
        )
        self.planta_2 = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
        )
        self.planta_3 = Planta.objects.create(
            codigo="CAT-0003",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )

    def test_crear_evento_individual(self):
        evento = Evento.create_individual(
            tipo=self.tipo_riego,
            fecha=date(2026, 9, 5),
            planta=self.planta_1,
            autor=self.usuario,
        )
        self.assertEqual(evento.plantas.count(), 1)
        self.assertEqual(evento.plantas.first(), self.planta_1)
        self.assertEqual(evento.autor, self.usuario)

    def test_crear_evento_por_lote(self):
        evento = Evento.create_for_lote(
            tipo=self.tipo_riego,
            fecha=date(2026, 9, 5),
            lote=self.lote,
            autor=self.usuario,
        )
        plantas_evento = set(evento.plantas.all())
        self.assertEqual(plantas_evento, {self.planta_1, self.planta_2})

    def test_crear_evento_masivo(self):
        evento = Evento.create_bulk(
            tipo=self.tipo_riego,
            fecha=date(2026, 9, 5),
            plantas=[self.planta_1, self.planta_3],
            autor=self.usuario,
        )
        plantas_evento = set(evento.plantas.all())
        self.assertEqual(plantas_evento, {self.planta_1, self.planta_3})

    def test_evento_no_fitosanitario_no_incrementa(self):
        Evento.create_individual(
            tipo=self.tipo_riego,
            fecha=date(2026, 9, 5),
            planta=self.planta_1,
            autor=self.usuario,
        )
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 0)

    def test_evento_fitosanitario_incrementa_contador(self):
        Evento.create_bulk(
            tipo=self.tipo_fitosanitario,
            fecha=date(2026, 9, 5),
            plantas=[self.planta_1, self.planta_2],
            autor=self.usuario,
        )
        self.planta_1.refresh_from_db()
        self.planta_2.refresh_from_db()
        self.planta_3.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)
        self.assertEqual(self.planta_2.n_eventos_fitosanitarios, 1)
        self.assertEqual(self.planta_3.n_eventos_fitosanitarios, 0)

    def test_borrar_evento_fitosanitario_decrementa(self):
        evento = Evento.create_bulk(
            tipo=self.tipo_fitosanitario,
            fecha=date(2026, 9, 5),
            plantas=[self.planta_1, self.planta_2],
            autor=self.usuario,
        )
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)
        evento.delete()
        self.planta_1.refresh_from_db()
        self.planta_2.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 0)
        self.assertEqual(self.planta_2.n_eventos_fitosanitarios, 0)

    def test_borrar_evento_fitosanitario_no_baja_de_cero(self):
        evento = Evento.create_individual(
            tipo=self.tipo_fitosanitario,
            fecha=date(2026, 9, 5),
            planta=self.planta_1,
            autor=self.usuario,
        )
        Planta.objects.filter(pk=self.planta_1.pk).update(
            n_eventos_fitosanitarios=0
        )
        evento.delete()
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 0)


class FotoModelTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.usuario = get_user_model().objects.create_user(username="operario")
        variedad = Variedad.objects.create(nombre="Catuaí", especie="Coffea arabica")
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.tipo_hoja = TipoFoto.objects.create(nombre="Hoja")
        self.tipo_general = TipoFoto.objects.create(nombre="General")

    @staticmethod
    def _imagen(nombre="foto.png"):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            nombre, buffer.getvalue(), content_type="image/png"
        )

    def _crear_foto(self, tipo, activa=True, evento=None):
        return Foto.objects.create(
            planta=self.planta,
            imagen=self._imagen(),
            tipo=tipo,
            fecha=date(2026, 9, 10),
            activa=activa,
            autor=self.usuario,
            evento=evento,
        )

    def test_crear_foto_valida(self):
        foto = self._crear_foto(self.tipo_hoja)
        self.assertEqual(foto.planta, self.planta)
        self.assertTrue(foto.activa)
        self.assertTrue(foto.imagen.name.startswith("fotos/"))
        self.assertTrue(foto.imagen.storage.exists(foto.imagen.name))

    def test_segunda_foto_activa_desactiva_anterior(self):
        foto_1 = self._crear_foto(self.tipo_hoja)
        foto_2 = self._crear_foto(self.tipo_hoja)
        foto_1.refresh_from_db()
        foto_2.refresh_from_db()
        self.assertFalse(foto_1.activa)
        self.assertTrue(foto_2.activa)
        self.assertEqual(
            Foto.objects.filter(planta=self.planta, activa=True).count(), 1
        )

    def test_fotos_de_distinto_tipo_no_se_desactivan(self):
        foto_hoja = self._crear_foto(self.tipo_hoja)
        foto_general = self._crear_foto(self.tipo_general)
        foto_hoja.refresh_from_db()
        foto_general.refresh_from_db()
        self.assertTrue(foto_hoja.activa)
        self.assertTrue(foto_general.activa)
        self.assertEqual(
            Foto.objects.filter(planta=self.planta, activa=True).count(), 2
        )

    def test_evento_opcional_puede_ser_null(self):
        foto = self._crear_foto(self.tipo_hoja, evento=None)
        self.assertIsNone(foto.evento)


class EtiquetaTests(TestCase):
    def setUp(self):
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )

    def _crear_planta(self, codigo):
        return Planta.objects.create(
            codigo=codigo,
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )

    def test_prefijo_derivado_de_variedad(self):
        self.assertEqual(obtener_prefijo(self.variedad), "CAT")

    def test_generar_codigos_secuenciales(self):
        codigos = generar_codigos(self.variedad, 3)
        self.assertEqual(codigos, ["CAT-0001", "CAT-0002", "CAT-0003"])
        self.assertEqual(len(set(codigos)), 3)

    def test_secuencia_no_reutiliza_numeros_existentes(self):
        self._crear_planta("CAT-0002")
        self._crear_planta("CAT-0005")
        codigos = generar_codigos(self.variedad, 2)
        self.assertEqual(codigos, ["CAT-0006", "CAT-0007"])

    def test_pdf_se_genera_con_cada_formato(self):
        for formato in ("numerico", "qr", "code128"):
            with self.subTest(formato=formato):
                pdf = generar_pdf_etiquetas(self.variedad, 2, [formato])
                self.assertTrue(pdf.startswith(b"%PDF"))
                self.assertGreater(len(pdf), 100)

    def test_pdf_con_formatos_combinados(self):
        pdf = generar_pdf_etiquetas(
            self.variedad, 3, ["numerico", "qr", "code128"]
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_validacion_de_codigo(self):
        self._crear_planta("CAT-0001")
        with self.assertRaises(ValidationError):
            validar_codigo_disponible("CAT-0001")
        validar_codigo_disponible("CAT-0099")


class CapturaUiTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="admin_ui")
        self.usuario.groups.add(Group.objects.get(name="admin"))
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

    def test_busqueda_y_ficha_sin_login_redirigen_al_login(self):
        respuesta_buscar = self.client.get(reverse("buscar_planta"))
        self.assertEqual(respuesta_buscar.status_code, 302)
        self.assertIn("/accounts/login/", respuesta_buscar.url)
        respuesta_ficha = self.client.get(
            reverse("ficha_planta", args=[self.planta.pk])
        )
        self.assertEqual(respuesta_ficha.status_code, 302)
        self.assertIn("/accounts/login/", respuesta_ficha.url)

    def test_buscar_codigo_existente_muestra_planta(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("buscar_planta"), {"codigo": "CAT-0001"}, follow=True
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "CAT-0001")

    def test_buscar_codigo_inexistente_muestra_no_encontrada(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("buscar_planta"), {"codigo": "CAT-9999"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se encontró")

    def test_get_formulario_medicion_autenticado(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("medir_planta", args=[self.planta.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Medir")

    def test_post_medicion_guarda_autor_y_actualiza_denormalizados(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post(
            reverse("medir_planta", args=[self.planta.pk]),
            {
                "fecha": "2026-09-20",
                "altura_cm": "12.5",
                "diametro_tallo_mm": "2.5",
            },
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta.pk])
        )
        medicion = Medicion.objects.get(planta=self.planta)
        self.assertEqual(medicion.autor, self.usuario)
        self.assertEqual(medicion.fecha, date(2026, 9, 20))
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.ultima_altura, 12.5)
        self.assertEqual(self.planta.ultimo_diametro, 2.5)


class CapturaAccionesUiTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.operario = get_user_model().objects.create_user(
            username="operario_acciones"
        )
        self.operario.groups.add(Group.objects.get(name="operario"))
        self.sin_grupo = get_user_model().objects.create_user(
            username="sin_grupo_acciones"
        )
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.tipo_riego = TipoEvento.objects.create(nombre="Riego")
        self.tipo_fito = TipoEvento.objects.create(nombre="Fitosanitario")
        self.tipo_hoja = TipoFoto.objects.create(nombre="Hoja")
        self.tipo_general = TipoFoto.objects.create(nombre="General")
        self.lote = Lote.objects.create(nombre="Lote A", tipo="lote")
        self.planta_1 = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
        )
        self.planta_2 = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
        )
        self.planta_3 = Planta.objects.create(
            codigo="CAT-0003",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )

    @staticmethod
    def _imagen(nombre="foto.png"):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            nombre, buffer.getvalue(), content_type="image/png"
        )

    def test_evento_individual_via_ui(self):
        self.client.force_login(self.operario)
        respuesta = self.client.post(
            reverse("evento_planta", args=[self.planta_1.pk]),
            {
                "tipo": self.tipo_riego.pk,
                "fecha": "2026-09-10",
                "producto": "",
                "dosis": "",
                "notas": "",
            },
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta_1.pk])
        )
        evento = Evento.objects.get()
        self.assertEqual(evento.autor, self.operario)
        self.assertEqual(list(evento.plantas.all()), [self.planta_1])

    def test_evento_fitosanitario_via_ui_incrementa(self):
        self.client.force_login(self.operario)
        self.client.post(
            reverse("evento_planta", args=[self.planta_1.pk]),
            {"tipo": self.tipo_fito.pk, "fecha": "2026-09-10"},
        )
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.n_eventos_fitosanitarios, 1)

    def test_evento_por_lote_via_ui(self):
        self.client.force_login(self.operario)
        respuesta = self.client.post(
            reverse("evento_nuevo"),
            {
                "tipo": self.tipo_riego.pk,
                "fecha": "2026-09-10",
                "producto": "",
                "dosis": "",
                "notas": "",
                "alcance": "lote",
                "lote": self.lote.pk,
                "codigos": "",
            },
        )
        self.assertRedirects(respuesta, reverse("buscar_planta"))
        evento = Evento.objects.get()
        self.assertEqual(
            set(evento.plantas.all()), {self.planta_1, self.planta_2}
        )

    def test_foto_via_ui_guarda_archivo_y_autor(self):
        self.client.force_login(self.operario)
        respuesta = self.client.post(
            reverse("foto_planta", args=[self.planta_1.pk]),
            {
                "imagen": self._imagen(),
                "tipo": self.tipo_hoja.pk,
                "fecha": "2026-09-10",
                "activa": "on",
            },
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta_1.pk])
        )
        foto = Foto.objects.get()
        self.assertEqual(foto.planta, self.planta_1)
        self.assertEqual(foto.autor, self.operario)
        self.assertTrue(foto.imagen.storage.exists(foto.imagen.name))

    def test_cambio_estado_via_ui(self):
        self.client.force_login(self.operario)
        respuesta = self.client.post(
            reverse("cambiar_estado", args=[self.planta_1.pk]),
            {
                "estado": "vendida",
                "fecha_baja": "2026-09-20",
                "motivo_baja": "Venta",
            },
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta_1.pk])
        )
        self.planta_1.refresh_from_db()
        self.assertEqual(self.planta_1.estado, "vendida")
        self.assertEqual(self.planta_1.fecha_baja, date(2026, 9, 20))
        self.assertEqual(self.planta_1.motivo_baja, "Venta")

    def test_acceso_sin_permiso_o_sin_autenticacion(self):
        respuesta_anon = self.client.get(
            reverse("evento_planta", args=[self.planta_1.pk])
        )
        self.assertEqual(respuesta_anon.status_code, 302)
        self.assertIn("/accounts/login/", respuesta_anon.url)
        self.client.force_login(self.sin_grupo)
        respuesta_sin_grupo = self.client.get(
            reverse("foto_planta", args=[self.planta_1.pk])
        )
        self.assertEqual(respuesta_sin_grupo.status_code, 403)


class ConsultaTimelineTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.usuario = get_user_model().objects.create_user(username="admin_consulta")
        self.usuario.groups.add(Group.objects.get(name="admin"))
        self.variedad_a = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.variedad_b = Variedad.objects.create(
            nombre="Bourbon", especie="Coffea arabica"
        )
        self.lote = Lote.objects.create(nombre="Lote A", tipo="lote")
        self.planta_1 = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad_a,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
            estado="activa",
        )
        self.planta_2 = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad_a,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            estado="vendida",
        )
        self.planta_3 = Planta.objects.create(
            codigo="CAT-0003",
            variedad=self.variedad_b,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            estado="activa",
        )
        self.tipo_evento = TipoEvento.objects.create(nombre="Riego")
        self.tipo_foto = TipoFoto.objects.create(nombre="Hoja")
        self.medicion = Medicion.objects.create(
            planta=self.planta_1,
            fecha=date(2026, 9, 2),
            altura_cm=12.0,
            autor=self.usuario,
        )
        self.evento = Evento.create_individual(
            tipo=self.tipo_evento,
            fecha=date(2026, 9, 1),
            planta=self.planta_1,
            autor=self.usuario,
        )
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        self.foto = Foto.objects.create(
            planta=self.planta_1,
            imagen=SimpleUploadedFile(
                "foto.png", buffer.getvalue(), content_type="image/png"
            ),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 3),
            autor=self.usuario,
        )

    def test_inventario_lista_y_filtra(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse("inventario"))
        self.assertEqual(respuesta.status_code, 200)
        for codigo in ("CAT-0001", "CAT-0002", "CAT-0003"):
            self.assertContains(respuesta, codigo)
        respuesta_vendida = self.client.get(
            reverse("inventario"), {"estado": "vendida"}
        )
        self.assertContains(respuesta_vendida, "CAT-0002")
        self.assertNotContains(respuesta_vendida, "CAT-0001")
        self.assertNotContains(respuesta_vendida, "CAT-0003")
        respuesta_variedad = self.client.get(
            reverse("inventario"), {"variedad": self.variedad_a.pk}
        )
        self.assertContains(respuesta_variedad, "CAT-0001")
        self.assertContains(respuesta_variedad, "CAT-0002")
        self.assertNotContains(respuesta_variedad, "CAT-0003")

    def test_inventario_contadores_por_estado(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("inventario"), {"variedad": self.variedad_a.pk}
        )
        self.assertEqual(respuesta.status_code, 200)
        contadores = {
            c["valor"]: c["total"] for c in respuesta.context["contadores_lista"]
        }
        self.assertEqual(contadores["activa"], 1)
        self.assertEqual(contadores["vendida"], 1)
        self.assertEqual(contadores["muerta"], 0)

    def test_ficha_muestra_linea_de_tiempo_cronologica(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("ficha_planta", args=[self.planta_1.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        timeline = respuesta.context["timeline"]
        self.assertEqual(len(timeline), 3)
        self.assertEqual(
            [item["tipo"] for item in timeline],
            ["Evento", "Medición", "Foto"],
        )
        fechas = [item["fecha"] for item in timeline]
        self.assertEqual(
            fechas,
            [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)],
        )
        self.assertEqual(fechas, sorted(fechas))


class GraficoFotosTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.usuario = get_user_model().objects.create_user(username="admin_graficos")
        self.usuario.groups.add(Group.objects.get(name="admin"))
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
        self.tipo_foto = TipoFoto.objects.create(nombre="General")
        Medicion.objects.create(
            planta=self.planta_1,
            fecha=date(2026, 9, 1),
            altura_cm=10.0,
            diametro_tallo_mm=2.0,
            autor=self.usuario,
        )
        Medicion.objects.create(
            planta=self.planta_1,
            fecha=date(2026, 9, 10),
            altura_cm=17.0,
            diametro_tallo_mm=3.0,
            autor=self.usuario,
        )
        Medicion.objects.create(
            planta=self.planta_2,
            fecha=date(2026, 9, 5),
            altura_cm=20.0,
            autor=self.usuario,
        )
        self.foto_1 = Foto.objects.create(
            planta=self.planta_1,
            imagen=SimpleUploadedFile(
                "foto1.png",
                Image.new("RGB", (10, 10), color="red").tobytes(),
                content_type="image/png",
            ),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 2),
            autor=self.usuario,
        )
        self.foto_2 = Foto.objects.create(
            planta=self.planta_1,
            imagen=SimpleUploadedFile(
                "foto2.png",
                Image.new("RGB", (10, 10), color="red").tobytes(),
                content_type="image/png",
            ),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 8),
            autor=self.usuario,
        )

    def test_grafico_una_planta_series_correctas(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("grafico_planta", args=[self.planta_1.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        alturas = [
            (item["fecha"], item["valor"])
            for item in respuesta.context["serie_altura"]
        ]
        diametros = [
            (item["fecha"], item["valor"])
            for item in respuesta.context["serie_diametro"]
        ]
        self.assertEqual(
            alturas,
            [(date(2026, 9, 1), 10.0), (date(2026, 9, 10), 17.0)],
        )
        self.assertEqual(
            diametros,
            [(date(2026, 9, 1), 2.0), (date(2026, 9, 10), 3.0)],
        )
        fechas = [fecha for fecha, _ in alturas]
        self.assertEqual(fechas, sorted(fechas))

    def test_grafico_multi_planta_incluye_seleccionadas(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("grafico_plantas"),
            {"plantas": [self.planta_1.pk, self.planta_2.pk]},
        )
        self.assertEqual(respuesta.status_code, 200)
        seleccionadas = respuesta.context["seleccionadas"]
        self.assertEqual(len(seleccionadas), 2)
        codigos = {planta.codigo for planta in seleccionadas}
        self.assertEqual(codigos, {"CAT-0001", "CAT-0002"})

    def test_ficha_galeria_fotos_en_orden_cronologico(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("ficha_planta", args=[self.planta_1.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        fotos = respuesta.context["fotos"]
        self.assertEqual(len(fotos), 2)
        fechas = [foto.fecha for foto in fotos]
        self.assertEqual(
            fechas,
            [date(2026, 9, 2), date(2026, 9, 8)],
        )


class PanelSeleccionTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_panel")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        datos = [
            ("CAT-0001", 6.0, 4.0, 5, 4, 1),
            ("CAT-0002", 2.0, 7.0, 4, 3, 3),
            ("CAT-0003", 6.5, 2.0, 2, 2, 0),
        ]
        for codigo, tasa, esbeltez, vigor, sanidad, fitos in datos:
            Planta.objects.create(
                codigo=codigo,
                variedad=self.variedad,
                origen="propia",
                fecha_alta=date(2026, 9, 1),
                contenedor="maceta",
                tasa_crecimiento=tasa,
                indice_esbeltez=esbeltez,
                score_vigor_actual=vigor,
                score_sanidad_actual=sanidad,
                n_eventos_fitosanitarios=fitos,
            )

    def _codigos(self, params):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("panel_seleccion"), params)
        self.assertEqual(respuesta.status_code, 200)
        return [fila["planta"].codigo for fila in respuesta.context["filas"]]

    def test_filtro_tasa_minima(self):
        self.assertEqual(
            set(self._codigos({"tasa_min": "5"})), {"CAT-0001", "CAT-0003"}
        )

    def test_filtro_esbeltez_entre(self):
        self.assertEqual(
            self._codigos({"esbeltez_min": "3", "esbeltez_max": "5"}),
            ["CAT-0001"],
        )

    def test_indice_compuesto_caso_conocido(self):
        planta = Planta.objects.get(codigo="CAT-0001")
        self.assertEqual(calcular_indice(planta), 79.0)

    def test_ranking_por_metricas(self):
        self.assertEqual(
            self._codigos({"orden_por": "sanidad", "direccion": "desc"}),
            ["CAT-0001", "CAT-0002", "CAT-0003"],
        )
        self.assertEqual(
            self._codigos({"orden_por": "tasa", "direccion": "desc"}),
            ["CAT-0003", "CAT-0001", "CAT-0002"],
        )

    def test_export_csv(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(
            reverse("seleccion_csv"), {"tasa_min": "5"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "text/csv")
        self.assertTrue(respuesta.content.startswith(b"\xef\xbb\xbf"))
        contenido = respuesta.content.decode("utf-8")
        self.assertTrue(contenido.startswith("\ufeff"))
        self.assertIn("codigo", contenido)
        self.assertIn("CAT-0001", contenido)
        self.assertIn("CAT-0003", contenido)
        self.assertNotIn("CAT-0002", contenido)


class FichaPublicaTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.admin = get_user_model().objects.create_user(username="admin_publico")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.proveedor = Proveedor.objects.create(nombre="Proveedor Secreto")
        self.tipo_evento = TipoEvento.objects.create(nombre="Fitosanitario")
        self.tipo_foto = TipoFoto.objects.create(nombre="General")
        self.planta_publica = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="proveedor",
            proveedor=self.proveedor,
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            notas="nota interna secreta",
            publico_activo=True,
        )
        Medicion.objects.create(
            planta=self.planta_publica,
            fecha=date(2026, 9, 2),
            altura_cm=12.0,
            notas="notas medicion privadas",
            autor=self.admin,
        )
        Evento.create_individual(
            tipo=self.tipo_evento,
            fecha=date(2026, 9, 1),
            planta=self.planta_publica,
            autor=self.admin,
            producto="fungicida secreto",
            dosis="10ml",
            notas="evento privado",
        )
        self.planta_inactiva = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            publico_activo=False,
        )

    def _url_publica(self, token):
        return reverse("ficha_publica", args=[token])

    def test_token_valido_publico_devuelve_200(self):
        respuesta = self.client.get(self._url_publica(self.planta_publica.token_publico))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "CAT-0001")

    def test_token_valido_inactivo_devuelve_404(self):
        respuesta = self.client.get(self._url_publica(self.planta_inactiva.token_publico))
        self.assertEqual(respuesta.status_code, 404)

    def test_token_inexistente_devuelve_404(self):
        from uuid import uuid4

        respuesta = self.client.get(self._url_publica(uuid4()))
        self.assertEqual(respuesta.status_code, 404)

    def test_no_expone_datos_sensibles(self):
        respuesta = self.client.get(self._url_publica(self.planta_publica.token_publico))
        contenido = respuesta.content.decode("utf-8")
        self.assertNotIn("Proveedor Secreto", contenido)
        self.assertNotIn("nota interna secreta", contenido)
        self.assertNotIn("notas medicion privadas", contenido)
        self.assertNotIn("fungicida secreto", contenido)
        self.assertNotIn("Vigor", contenido)
        self.assertNotIn("Sanidad", contenido)
        self.assertNotIn(str(self.planta_publica.token_publico), contenido)

    def test_activacion_por_admin(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("alternar_publico", args=[self.planta_inactiva.pk])
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta_inactiva.pk])
        )
        self.planta_inactiva.refresh_from_db()
        self.assertTrue(self.planta_inactiva.publico_activo)
        respuesta_publica = self.client.get(
            self._url_publica(self.planta_inactiva.token_publico)
        )
        self.assertEqual(respuesta_publica.status_code, 200)
        self.assertContains(respuesta_publica, "CAT-0002")


class ReportesTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_reportes")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad_a = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.variedad_b = Variedad.objects.create(
            nombre="Bourbon", especie="Coffea arabica"
        )
        self.proveedor_a = Proveedor.objects.create(nombre="ProvA")
        self.proveedor_b = Proveedor.objects.create(nombre="ProvB")
        datos = [
            ("CAT-0001", self.variedad_a, "proveedor", self.proveedor_a, "activa", 20.0, 4.0, 2.0),
            ("CAT-0002", self.variedad_a, "proveedor", self.proveedor_a, "muerta", None, None, None),
            ("CAT-0003", self.variedad_a, "proveedor", self.proveedor_a, "vendida", 10.0, 1.0, 3.0),
            ("CAT-0004", self.variedad_a, "propia", None, "activa", 30.0, 6.0, 4.0),
            ("CAT-0005", self.variedad_b, "proveedor", self.proveedor_b, "activa", 40.0, 8.0, 5.0),
        ]
        for codigo, variedad, origen, proveedor, estado, altura, tasa, diametro in datos:
            Planta.objects.create(
                codigo=codigo,
                variedad=variedad,
                origen=origen,
                proveedor=proveedor,
                fecha_alta=date(2026, 9, 1),
                contenedor="maceta",
                estado=estado,
                ultima_altura=altura,
                tasa_crecimiento=tasa,
                ultimo_diametro=diametro,
            )

    def test_supervivencia_por_procedencia(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes"))
        self.assertEqual(respuesta.status_code, 200)
        por_procedencia = {
            fila["procedencia"]: fila for fila in respuesta.context["supervivencia"]
        }
        prov_a = por_procedencia["Proveedor: ProvA"]
        self.assertEqual(prov_a["total"], 3)
        desglose = {col["etiqueta"]: col["cantidad"] for col in prov_a["columnas"]}
        self.assertEqual(desglose["Activa"], 1)
        self.assertEqual(desglose["Muerta"], 1)
        self.assertEqual(desglose["Vendida"], 1)
        self.assertEqual(prov_a["sobrevivientes"], 2)
        self.assertEqual(prov_a["porcentaje"], 66.7)
        propia = por_procedencia["Propia"]
        self.assertEqual(propia["total"], 1)
        self.assertEqual(propia["porcentaje"], 100.0)

    def test_desempeno_agregado(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes"))
        self.assertEqual(respuesta.status_code, 200)
        por_clave = {
            (fila["variedad"], fila["procedencia"]): fila
            for fila in respuesta.context["desempeno"]
        }
        catua_prov = por_clave[("Catuaí", "Proveedor: ProvA")]
        self.assertEqual(catua_prov["promedio_altura"], 15.0)
        self.assertEqual(catua_prov["promedio_diametro"], 2.5)
        self.assertEqual(catua_prov["promedio_tasa"], 2.5)
        catua_propia = por_clave[("Catuaí", "Propia")]
        self.assertEqual(catua_propia["promedio_altura"], 30.0)
        self.assertEqual(catua_propia["promedio_tasa"], 6.0)
        bourbon_prov = por_clave[("Bourbon", "Proveedor: ProvB")]
        self.assertEqual(bourbon_prov["promedio_altura"], 40.0)


class EtiquetasUiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_etiq")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.no_admin = get_user_model().objects.create_user(username="no_admin_etiq")
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )

    def test_get_como_admin_200(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("generar_etiquetas"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Generar etiquetas")

    def test_get_no_admin_403_y_sin_login_redirect(self):
        respuesta_anon = self.client.get(reverse("generar_etiquetas"))
        self.assertEqual(respuesta_anon.status_code, 302)
        self.client.force_login(self.no_admin)
        respuesta = self.client.get(reverse("generar_etiquetas"))
        self.assertEqual(respuesta.status_code, 403)

    def test_post_genera_pdf(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("generar_etiquetas"),
            {
                "variedad": self.variedad.pk,
                "cantidad": 2,
                "formatos": ["numerico", "qr"],
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn('filename="etiquetas.pdf"', respuesta["Content-Disposition"])
        self.assertTrue(respuesta.content.startswith(b"%PDF"))

    def test_post_sin_formatos_no_genera_pdf(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("generar_etiquetas"),
            {"variedad": self.variedad.pk, "cantidad": 2},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotEqual(respuesta["Content-Type"], "application/pdf")
        self.assertFalse(respuesta.content.startswith(b"%PDF"))
        self.assertContains(respuesta, "Generar etiquetas")


class BajasCongelamientoUiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_bajas")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.lote = Lote.objects.create(nombre="Lote A", tipo="lote")
        self.planta = Planta.objects.create(
            codigo="CAT-0001",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
            lote=self.lote,
        )
        self.tipo_evento = TipoEvento.objects.create(nombre="Riego")

    def _poner_en_salida(self):
        self.planta.estado = "vendida"
        self.planta.fecha_baja = date(2026, 9, 20)
        self.planta.motivo_baja = "Venta"
        self.planta.save(
            update_fields=["estado", "fecha_baja", "motivo_baja"]
        )

    def test_cambio_a_estado_salida_guarda_datos(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("cambiar_estado", args=[self.planta.pk]),
            {
                "estado": "vendida",
                "fecha_baja": "2026-09-20",
                "motivo_baja": "Venta",
            },
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta.pk])
        )
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.estado, "vendida")
        self.assertEqual(self.planta.fecha_baja, date(2026, 9, 20))
        self.assertEqual(self.planta.motivo_baja, "Venta")

    def test_cambio_a_no_salida_limpia_datos(self):
        self._poner_en_salida()
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("cambiar_estado", args=[self.planta.pk]),
            {"estado": "activa"},
        )
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta.pk])
        )
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.estado, "activa")
        self.assertIsNone(self.planta.fecha_baja)
        self.assertEqual(self.planta.motivo_baja, "")

    def test_salida_sin_motivo_fecha_formulario_invalido(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("cambiar_estado", args=[self.planta.pk]),
            {"estado": "vendida"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, "La fecha de baja es obligatoria en estados de salida."
        )
        self.planta.refresh_from_db()
        self.assertEqual(self.planta.estado, "activa")

    def test_capturas_bloqueadas_en_estado_salida(self):
        self._poner_en_salida()
        self.client.force_login(self.admin)
        respuesta_medir = self.client.get(
            reverse("medir_planta", args=[self.planta.pk])
        )
        self.assertRedirects(
            respuesta_medir, reverse("ficha_planta", args=[self.planta.pk])
        )
        respuesta_evento = self.client.get(
            reverse("evento_planta", args=[self.planta.pk])
        )
        self.assertRedirects(
            respuesta_evento, reverse("ficha_planta", args=[self.planta.pk])
        )
        respuesta_foto = self.client.get(
            reverse("foto_planta", args=[self.planta.pk])
        )
        self.assertRedirects(
            respuesta_foto, reverse("ficha_planta", args=[self.planta.pk])
        )
        respuesta_lote = self.client.post(
            reverse("evento_nuevo"),
            {
                "tipo": self.tipo_evento.pk,
                "fecha": "2026-09-21",
                "producto": "",
                "dosis": "",
                "notas": "",
                "alcance": "lote",
                "lote": self.lote.pk,
                "codigos": "",
            },
        )
        self.assertEqual(respuesta_lote.status_code, 200)
        self.assertEqual(Medicion.objects.count(), 0)
        self.assertEqual(Evento.objects.count(), 0)


class PromocionBandejaTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin_promo")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.no_admin = get_user_model().objects.create_user(username="no_admin_promo")
        self.variedad = Variedad.objects.create(
            nombre="Catuaí", especie="Coffea arabica"
        )
        self.proveedor = Proveedor.objects.create(nombre="Vivero San Martín")
        self.lote = Lote.objects.create(nombre="Invernadero A", tipo="invernadero")
        self.bandeja_propia = Bandeja.objects.create(
            variedad=self.variedad, origen="propia"
        )
        self.bandeja_proveedor = Bandeja.objects.create(
            variedad=self.variedad,
            origen="proveedor",
            proveedor=self.proveedor,
        )
        Planta.objects.create(
            codigo="CAT-0005",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )

    def _datos(self, bandeja, cantidad):
        return {
            "bandeja": bandeja.pk,
            "sobrevivientes": cantidad,
            "fecha_alta": "2026-09-25",
            "lote": self.lote.pk,
            "contenedor": "maceta",
        }

    def test_promocion_crea_n_plantas_con_codigos_secuenciales(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("promover_bandeja"), self._datos(self.bandeja_propia, 2)
        )
        self.assertRedirects(respuesta, reverse("buscar_planta"))
        plantas = Planta.objects.filter(bandeja=self.bandeja_propia).order_by(
            "codigo"
        )
        self.assertEqual(plantas.count(), 2)
        self.assertEqual(
            list(plantas.values_list("codigo", flat=True)),
            ["CAT-0006", "CAT-0007"],
        )
        for planta in plantas:
            self.assertEqual(planta.variedad, self.variedad)
            self.assertEqual(planta.origen, "propia")
            self.assertEqual(planta.bandeja, self.bandeja_propia)
            self.assertEqual(planta.fecha_alta, date(2026, 9, 25))
            self.assertEqual(planta.lote, self.lote)
            self.assertEqual(planta.contenedor, "maceta")
            self.assertEqual(planta.estado, "activa")

    def test_bandeja_no_se_modifica(self):
        self.client.force_login(self.admin)
        antes = {
            "origen": self.bandeja_propia.origen,
            "n_semillas": self.bandeja_propia.n_semillas,
            "variedad_id": self.bandeja_propia.variedad_id,
        }
        self.client.post(
            reverse("promover_bandeja"), self._datos(self.bandeja_propia, 1)
        )
        self.bandeja_propia.refresh_from_db()
        self.assertEqual(
            antes,
            {
                "origen": self.bandeja_propia.origen,
                "n_semillas": self.bandeja_propia.n_semillas,
                "variedad_id": self.bandeja_propia.variedad_id,
            },
        )
        self.assertEqual(Bandeja.objects.count(), 2)

    def test_promocion_hereda_proveedor(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("promover_bandeja"), self._datos(self.bandeja_proveedor, 1)
        )
        self.assertRedirects(respuesta, reverse("buscar_planta"))
        planta = Planta.objects.get(bandeja=self.bandeja_proveedor)
        self.assertEqual(planta.origen, "proveedor")
        self.assertEqual(planta.proveedor, self.proveedor)

    def test_acceso_no_admin(self):
        respuesta_anon = self.client.get(reverse("promover_bandeja"))
        self.assertEqual(respuesta_anon.status_code, 302)
        self.client.force_login(self.no_admin)
        respuesta = self.client.get(reverse("promover_bandeja"))
        self.assertEqual(respuesta.status_code, 403)


class CompararFotosTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tmp_media.cleanup)
        self.usuario = get_user_model().objects.create_user(username="admin_fotos_comp")
        self.usuario.groups.add(Group.objects.get(name="admin"))
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
        self.otra_planta = Planta.objects.create(
            codigo="CAT-0002",
            variedad=self.variedad,
            origen="propia",
            fecha_alta=date(2026, 9, 1),
            contenedor="maceta",
        )
        self.tipo_foto = TipoFoto.objects.create(nombre="General")
        self.foto_1 = Foto.objects.create(
            planta=self.planta,
            imagen=self._imagen("foto1.png"),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 1),
            autor=self.usuario,
        )
        self.foto_2 = Foto.objects.create(
            planta=self.planta,
            imagen=self._imagen("foto2.png"),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 10),
            autor=self.usuario,
        )
        self.foto_3 = Foto.objects.create(
            planta=self.planta,
            imagen=self._imagen("foto3.png"),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 20),
            autor=self.usuario,
        )
        self.foto_otra = Foto.objects.create(
            planta=self.otra_planta,
            imagen=self._imagen("foto_otra.png"),
            tipo=self.tipo_foto,
            fecha=date(2026, 9, 5),
            autor=self.usuario,
        )

    @staticmethod
    def _imagen(nombre):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            nombre, buffer.getvalue(), content_type="image/png"
        )

    def test_sin_parametros_lista_fotos(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("comparar_fotos", args=[self.planta.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["fotos"]), 3)
        self.assertIsNone(respuesta.context["foto_a"])
        self.assertIsNone(respuesta.context["foto_b"])
        self.assertContains(respuesta, "foto1.png")

    def test_con_dos_fotos_validas_muestra_ambas(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("comparar_fotos", args=[self.planta.pk]),
            {"foto_a": self.foto_1.pk, "foto_b": self.foto_2.pk},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["foto_a"], self.foto_1)
        self.assertEqual(respuesta.context["foto_b"], self.foto_2)
        self.assertContains(respuesta, self.foto_1.imagen.url)
        self.assertContains(respuesta, self.foto_2.imagen.url)

    def test_foto_inexistente_o_de_otra_planta_se_ignora(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(
            reverse("comparar_fotos", args=[self.planta.pk]),
            {"foto_a": self.foto_otra.pk, "foto_b": self.foto_2.pk},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context["foto_a"])
        self.assertEqual(respuesta.context["foto_b"], self.foto_2)
        respuesta_fantasma = self.client.get(
            reverse("comparar_fotos", args=[self.planta.pk]),
            {"foto_a": "9999", "foto_b": self.foto_1.pk},
        )
        self.assertEqual(respuesta_fantasma.status_code, 200)
        self.assertIsNone(respuesta_fantasma.context["foto_a"])


class HistorialEstadoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="admin_historial")
        self.usuario.groups.add(Group.objects.get(name="admin"))
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

    def _cambiar(self, estado, motivo="", fecha_baja=""):
        datos = {"estado": estado}
        if estado in ("muerta", "vendida", "regalada", "descartada"):
            datos["fecha_baja"] = fecha_baja or "2026-09-30"
            datos["motivo_baja"] = motivo or "Salida"
        return self.client.post(
            reverse("cambiar_estado", args=[self.planta.pk]), datos
        )

    def test_cambio_crea_registro_con_datos(self):
        self.client.force_login(self.usuario)
        self._cambiar("vendida", motivo="Venta")
        registro = CambioEstado.objects.get()
        self.assertEqual(registro.planta, self.planta)
        self.assertEqual(registro.estado_anterior, "activa")
        self.assertEqual(registro.estado_nuevo, "vendida")
        self.assertEqual(registro.fecha, date.today())
        self.assertEqual(registro.motivo, "Venta")
        self.assertEqual(registro.autor, self.usuario)

    def test_mismo_estado_no_crea_registro(self):
        self.client.force_login(self.usuario)
        respuesta = self._cambiar("activa")
        self.assertRedirects(
            respuesta, reverse("ficha_planta", args=[self.planta.pk])
        )
        self.assertEqual(CambioEstado.objects.count(), 0)

    def test_timeline_incluye_item_estado(self):
        self.client.force_login(self.usuario)
        self._cambiar("vendida", motivo="Venta")
        respuesta = self.client.get(
            reverse("ficha_planta", args=[self.planta.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        tipos = [item["tipo"] for item in respuesta.context["timeline"]]
        self.assertIn("Estado", tipos)
        estado = next(
            item for item in respuesta.context["timeline"] if item["tipo"] == "Estado"
        )
        self.assertEqual(estado["descripcion"], "activa → vendida")

    def test_ficha_publica_no_expone_autor(self):
        self.client.force_login(self.usuario)
        self._cambiar("vendida", motivo="Venta")
        self.planta.publico_activo = True
        self.planta.save(update_fields=["publico_activo"])
        respuesta = self.client.get(
            reverse("ficha_publica", args=[self.planta.token_publico])
        )
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode("utf-8")
        self.assertIn("Estado", contenido)
        self.assertNotIn("admin_historial", contenido)

