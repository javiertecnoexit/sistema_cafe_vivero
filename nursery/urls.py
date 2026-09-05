from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="inicio"),
    path("escanear/", views.escanear, name="escanear"),
    path("escanear/resolver/", views.resolver_codigo, name="resolver_codigo"),
    path("plantas/nueva/", views.nueva_planta, name="nueva_planta"),
    path("bandejas/nueva/", views.nueva_bandeja, name="nueva_bandeja"),
    path("buscar/", views.buscar_planta, name="buscar_planta"),
    path("inventario/", views.inventario, name="inventario"),
    path("plantas/<int:pk>/grafico/", views.grafico_planta, name="grafico_planta"),
    path("grafico-plantas/", views.grafico_plantas, name="grafico_plantas"),
    path("seleccion/", views.panel_seleccion, name="panel_seleccion"),
    path("seleccion/csv/", views.seleccion_csv, name="seleccion_csv"),
    path("reportes/", views.reportes, name="reportes"),
    path("etiquetas/", views.generar_etiquetas, name="generar_etiquetas"),
    path("bandejas/promover/", views.promover_bandeja, name="promover_bandeja"),
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
    path("plantas/<int:pk>/foto/", views.subir_foto, name="foto_planta"),
    path(
        "plantas/<int:pk>/fotos/",
        views.comparar_fotos,
        name="comparar_fotos",
    ),
    path(
        "plantas/<int:pk>/estado/",
        views.cambiar_estado,
        name="cambiar_estado",
    ),
]
