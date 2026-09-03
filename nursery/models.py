import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Variedad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    especie = models.CharField(max_length=100)
    notas = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    contacto = models.CharField(max_length=200, blank=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class EtapaFenologica(models.Model):
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField()

    def __str__(self):
        return self.nombre


class TipoEvento(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class TipoFoto(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Lote(models.Model):
    TIPO_CHOICES = [
        ("invernadero", "Invernadero"),
        ("lote", "Lote"),
        ("hilera", "Hilera"),
    ]

    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    def __str__(self):
        return self.nombre


class Bandeja(models.Model):
    ORIGEN_CHOICES = [
        ("proveedor", "Proveedor"),
        ("propia", "Propia"),
    ]

    variedad = models.ForeignKey(Variedad, on_delete=models.PROTECT)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, null=True, blank=True
    )
    fecha_siembra = models.DateField(null=True, blank=True)
    n_semillas = models.PositiveIntegerField(null=True, blank=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Bandeja {self.pk} - {self.variedad} - {self.fecha_siembra or 'sin fecha'}"


class Planta(models.Model):
    ORIGEN_CHOICES = [
        ("proveedor", "Proveedor"),
        ("propia", "Propia"),
    ]
    CONTENEDOR_CHOICES = [
        ("suelo", "Suelo"),
        ("maceta", "Maceta"),
    ]
    ESTADO_CHOICES = [
        ("activa", "Activa"),
        ("muerta", "Muerta"),
        ("vendida", "Vendida"),
        ("regalada", "Regalada"),
        ("descartada", "Descartada"),
        ("seleccionada", "Seleccionada"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    variedad = models.ForeignKey(Variedad, on_delete=models.PROTECT)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, null=True, blank=True
    )
    bandeja = models.ForeignKey(
        Bandeja, on_delete=models.PROTECT, null=True, blank=True
    )
    fecha_alta = models.DateField()
    etapa = models.ForeignKey(
        EtapaFenologica, on_delete=models.PROTECT, null=True, blank=True
    )
    contenedor = models.CharField(max_length=20, choices=CONTENEDOR_CHOICES)
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="activa"
    )
    notas = models.TextField(blank=True)
    token_publico = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    publico_activo = models.BooleanField(default=False)

    ultima_altura = models.FloatField(null=True, blank=True)
    ultimo_diametro = models.FloatField(null=True, blank=True)
    ultima_fecha_medicion = models.DateField(null=True, blank=True)
    tasa_crecimiento = models.FloatField(null=True, blank=True)
    indice_esbeltez = models.FloatField(null=True, blank=True)
    n_eventos_fitosanitarios = models.PositiveIntegerField(default=0)
    score_vigor_actual = models.PositiveSmallIntegerField(null=True, blank=True)
    score_sanidad_actual = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.codigo

    def recalcular_denormalizados_medicion(self):
        self.ultima_altura = None
        self.ultimo_diametro = None
        self.ultima_fecha_medicion = None
        self.indice_esbeltez = None
        self.tasa_crecimiento = None
        ultima = self.medicion_set.order_by("-fecha", "-id").first()
        if ultima is not None:
            self.ultima_altura = ultima.altura_cm
            self.ultimo_diametro = ultima.diametro_tallo_mm
            self.ultima_fecha_medicion = ultima.fecha
            if ultima.altura_cm is not None and ultima.diametro_tallo_mm is not None:
                self.indice_esbeltez = round(
                    ultima.altura_cm / ultima.diametro_tallo_mm, 2
                )
            self.tasa_crecimiento = self._calcular_tasa_crecimiento()
        self.save(
            update_fields=[
                "ultima_altura",
                "ultimo_diametro",
                "ultima_fecha_medicion",
                "indice_esbeltez",
                "tasa_crecimiento",
            ]
        )

    def _calcular_tasa_crecimiento(self):
        mediciones = list(
            self.medicion_set.filter(altura_cm__isnull=False)
            .order_by("-fecha", "-id")[:2]
        )
        if len(mediciones) < 2:
            return None
        reciente, anterior = mediciones[0], mediciones[1]
        dias = (reciente.fecha - anterior.fecha).days
        if dias <= 0:
            return None
        return round((reciente.altura_cm - anterior.altura_cm) / dias * 7, 2)

    def recalcular_denormalizados_evaluacion(self):
        self.score_vigor_actual = None
        self.score_sanidad_actual = None
        ultima = self.evaluacion_set.order_by("-fecha", "-id").first()
        if ultima is not None:
            self.score_vigor_actual = ultima.score_vigor
            self.score_sanidad_actual = ultima.score_sanidad
        self.save(update_fields=["score_vigor_actual", "score_sanidad_actual"])


class Medicion(models.Model):
    planta = models.ForeignKey(Planta, on_delete=models.CASCADE)
    fecha = models.DateField()
    altura_cm = models.FloatField(null=True, blank=True)
    diametro_tallo_mm = models.FloatField(null=True, blank=True)
    longitud_hoja_cm = models.FloatField(null=True, blank=True)
    diametro_copa_cm = models.FloatField(null=True, blank=True)
    n_ramas = models.PositiveIntegerField(null=True, blank=True)
    notas = models.TextField(blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Medición {self.pk} - {self.planta} - {self.fecha}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.planta.recalcular_denormalizados_medicion()

    def delete(self, *args, **kwargs):
        planta = self.planta
        super().delete(*args, **kwargs)
        planta.recalcular_denormalizados_medicion()


class Evaluacion(models.Model):
    SCORE_CHOICES = [
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    ]

    planta = models.ForeignKey(Planta, on_delete=models.CASCADE)
    fecha = models.DateField()
    score_vigor = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    score_sanidad = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    notas = models.TextField(blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Evaluación {self.pk} - {self.planta} - {self.fecha}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.planta.recalcular_denormalizados_evaluacion()

    def delete(self, *args, **kwargs):
        planta = self.planta
        super().delete(*args, **kwargs)
        planta.recalcular_denormalizados_evaluacion()


class Evento(models.Model):
    tipo = models.ForeignKey(TipoEvento, on_delete=models.PROTECT)
    fecha = models.DateField()
    producto = models.CharField(max_length=200, blank=True)
    dosis = models.CharField(max_length=100, blank=True)
    notas = models.TextField(blank=True)
    plantas = models.ManyToManyField(Planta, blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Evento {self.pk} - {self.tipo} - {self.fecha}"

    @staticmethod
    def _es_tipo_fitosanitario(tipo):
        return tipo.nombre.strip().lower() == "fitosanitario"

    @classmethod
    def _crear_con_plantas(
        cls, tipo, fecha, plantas, autor, producto="", dosis="", notas=""
    ):
        plantas = list(plantas)
        evento = cls.objects.create(
            tipo=tipo,
            fecha=fecha,
            producto=producto,
            dosis=dosis,
            notas=notas,
            autor=autor,
        )
        evento.plantas.set(plantas)
        if plantas and cls._es_tipo_fitosanitario(tipo):
            ids = [planta.id for planta in plantas]
            Planta.objects.filter(id__in=ids).update(
                n_eventos_fitosanitarios=models.F("n_eventos_fitosanitarios") + 1
            )
        return evento

    @classmethod
    def create_individual(
        cls, tipo, fecha, planta, autor, producto="", dosis="", notas=""
    ):
        return cls._crear_con_plantas(
            tipo, fecha, [planta], autor, producto, dosis, notas
        )

    @classmethod
    def create_for_lote(
        cls, tipo, fecha, lote, autor, producto="", dosis="", notas=""
    ):
        return cls._crear_con_plantas(
            tipo, fecha, lote.planta_set.all(), autor, producto, dosis, notas
        )

    @classmethod
    def create_bulk(
        cls, tipo, fecha, plantas, autor, producto="", dosis="", notas=""
    ):
        return cls._crear_con_plantas(
            tipo, fecha, plantas, autor, producto, dosis, notas
        )

    def delete(self, *args, **kwargs):
        es_fitosanitario = self._es_tipo_fitosanitario(self.tipo)
        ids = list(self.plantas.values_list("id", flat=True))
        super().delete(*args, **kwargs)
        if es_fitosanitario and ids:
            Planta.objects.filter(
                id__in=ids, n_eventos_fitosanitarios__gt=0
            ).update(n_eventos_fitosanitarios=models.F("n_eventos_fitosanitarios") - 1)


class Foto(models.Model):
    planta = models.ForeignKey(Planta, on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to="fotos/%Y/%m/")
    tipo = models.ForeignKey(TipoFoto, on_delete=models.PROTECT)
    fecha = models.DateField()
    activa = models.BooleanField(default=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    evento = models.ForeignKey(
        Evento, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"Foto {self.pk} - {self.planta} - {self.tipo} - {self.fecha}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.activa:
            self.__class__.objects.filter(
                planta=self.planta, tipo=self.tipo, activa=True
            ).exclude(pk=self.pk).update(activa=False)

