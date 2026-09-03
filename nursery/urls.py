from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="buscar_planta"), name="inicio"),
    path("buscar/", views.buscar_planta, name="buscar_planta"),
    path("inventario/", views.inventario, name="inventario"),
    path("plantas/<int:pk>/grafico/", views.grafico_planta, name="grafico_planta"),
    path("grafico-plantas/", views.grafico_plantas, name="grafico_plantas"),
    path("seleccion/", views.panel_seleccion, name="panel_seleccion"),
    path("seleccion/csv/", views.seleccion_csv, name="seleccion_csv"),
    path("reportes/", views.reportes, name="reportes"),
    path(
        "publica/<uuid:token>/", views.ficha_publica, name="ficha_publica"
    ),
    path(
        "plantas/<int:pk>/publico/",
        views.alternar_publico,
        name="alternar_publico",
    ),
    path("plantas/<int:pk>/", views.ficha_planta, name="ficha_planta"),
    path(
        "plantas/<int:pk>/medir/",
        views.MedicionCreateView.as_view(),
        name="medir_planta",
    ),
    path(
        "plantas/<int:pk>/evento/",
        views.evento_planta,
        name="evento_planta",
    ),
    path("eventos/nuevo/", views.evento_nuevo, name="evento_nuevo"),
    path(
        "plantas/<int:pk>/foto/",
        views.subir_foto,
        name="foto_planta",
    ),
    path(
        "plantas/<int:pk>/estado/",
        views.cambiar_estado,
        name="cambiar_estado",
    ),
]
