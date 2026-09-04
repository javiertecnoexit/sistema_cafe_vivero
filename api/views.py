from django.db.models import Count, F
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

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

from .permissions import PermisoEscrituraPorModelo
from .serializers import (
    BandejaSerializer,
    EtapaFenologicaSerializer,
    EvaluacionSerializer,
    EventoSerializer,
    FotoSerializer,
    LoteSerializer,
    MedicionSerializer,
    PlantaSerializer,
    ProveedorSerializer,
    TipoEventoSerializer,
    TipoFotoSerializer,
    VariedadSerializer,
)


class VariedadViewSet(viewsets.ModelViewSet):
    queryset = Variedad.objects.all()
    serializer_class = VariedadSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class EtapaFenologicaViewSet(viewsets.ModelViewSet):
    queryset = EtapaFenologica.objects.all()
    serializer_class = EtapaFenologicaSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class TipoEventoViewSet(viewsets.ModelViewSet):
    queryset = TipoEvento.objects.all()
    serializer_class = TipoEventoSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class TipoFotoViewSet(viewsets.ModelViewSet):
    queryset = TipoFoto.objects.all()
    serializer_class = TipoFotoSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.all()
    serializer_class = LoteSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class BandejaViewSet(viewsets.ModelViewSet):
    queryset = Bandeja.objects.all()
    serializer_class = BandejaSerializer
    permission_classes = [PermisoEscrituraPorModelo]


class PlantaViewSet(viewsets.ModelViewSet):
    queryset = Planta.objects.all()
    serializer_class = PlantaSerializer
    permission_classes = [PermisoEscrituraPorModelo]

    def get_queryset(self):
        queryset = super().get_queryset()
        filtros = {
            "variedad": "variedad_id",
            "origen": "origen",
            "lote": "lote_id",
            "etapa": "etapa_id",
            "estado": "estado",
        }
        for parametro, campo in filtros.items():
            valor = self.request.query_params.get(parametro)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset


def _esta_salida(planta):
    return planta.estado in Planta.ESTADOS_DE_SALIDA


def _rechazar_si_salida(planta):
    if _esta_salida(planta):
        raise ValidationError(
            "No se puede capturar sobre una planta en estado de salida."
        )


class MedicionViewSet(viewsets.ModelViewSet):
    queryset = Medicion.objects.all()
    serializer_class = MedicionSerializer
    permission_classes = [PermisoEscrituraPorModelo]

    def perform_create(self, serializer):
        _rechazar_si_salida(serializer.validated_data["planta"])
        serializer.save(autor=self.request.user)


class EvaluacionViewSet(viewsets.ModelViewSet):
    queryset = Evaluacion.objects.all()
    serializer_class = EvaluacionSerializer
    permission_classes = [PermisoEscrituraPorModelo]

    def perform_create(self, serializer):
        _rechazar_si_salida(serializer.validated_data["planta"])
        serializer.save(autor=self.request.user)


class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [PermisoEscrituraPorModelo]

    def perform_create(self, serializer):
        plantas = serializer.validated_data.get("plantas") or []
        if any(_esta_salida(planta) for planta in plantas):
            raise ValidationError(
                "No se puede capturar sobre una planta en estado de salida."
            )
        evento = serializer.save(autor=self.request.user)
        if Evento._es_tipo_fitosanitario(evento.tipo):
            ids = list(evento.plantas.values_list("id", flat=True))
            if ids:
                Planta.objects.filter(id__in=ids).update(
                    n_eventos_fitosanitarios=F("n_eventos_fitosanitarios") + 1
                )

    def perform_update(self, serializer):
        antes = set(serializer.instance.plantas.values_list("id", flat=True))
        evento = serializer.save()
        despues = set(evento.plantas.values_list("id", flat=True))
        afectadas = antes | despues
        if not afectadas:
            return
        tipos_fito = {
            tipo.pk
            for tipo in TipoEvento.objects.all()
            if Evento._es_tipo_fitosanitario(tipo)
        }
        filas = (
            Evento.objects.filter(
                plantas__id__in=afectadas, tipo_id__in=tipos_fito
            )
            .values("plantas__id")
            .annotate(total=Count("id"))
        )
        cuentas = {fila["plantas__id"]: fila["total"] for fila in filas}
        for planta_id in afectadas:
            Planta.objects.filter(pk=planta_id).update(
                n_eventos_fitosanitarios=cuentas.get(planta_id, 0)
            )

    def perform_destroy(self, instance):
        instance.delete()


class FotoViewSet(viewsets.ModelViewSet):
    queryset = Foto.objects.all()
    serializer_class = FotoSerializer
    permission_classes = [PermisoEscrituraPorModelo]

    def perform_create(self, serializer):
        _rechazar_si_salida(serializer.validated_data["planta"])
        serializer.save(autor=self.request.user)


