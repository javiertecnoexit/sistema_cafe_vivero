from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BandejaViewSet,
    EtapaFenologicaViewSet,
    EvaluacionViewSet,
    EventoViewSet,
    FotoViewSet,
    LoteViewSet,
    MedicionViewSet,
    PlantaViewSet,
    ProveedorViewSet,
    TipoEventoViewSet,
    TipoFotoViewSet,
    VariedadViewSet,
)

router = DefaultRouter()
router.register("variedades", VariedadViewSet, basename="variedad")
router.register("proveedores", ProveedorViewSet, basename="proveedor")
router.register("etapas", EtapaFenologicaViewSet, basename="etapafenologica")
router.register("tipos-evento", TipoEventoViewSet, basename="tipoevento")
router.register("tipos-foto", TipoFotoViewSet, basename="tipofoto")
router.register("lotes", LoteViewSet, basename="lote")
router.register("bandejas", BandejaViewSet, basename="bandeja")
router.register("plantas", PlantaViewSet, basename="planta")
router.register("mediciones", MedicionViewSet, basename="medicion")
router.register("evaluaciones", EvaluacionViewSet, basename="evaluacion")
router.register("eventos", EventoViewSet, basename="evento")
router.register("fotos", FotoViewSet, basename="foto")

urlpatterns = [
    path("", include(router.urls)),
]
