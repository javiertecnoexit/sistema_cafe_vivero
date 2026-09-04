from django.contrib import admin

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

admin.site.register(Variedad)
admin.site.register(Proveedor)
admin.site.register(EtapaFenologica)
admin.site.register(TipoEvento)
admin.site.register(TipoFoto)
admin.site.register(Lote)
admin.site.register(Bandeja)
admin.site.register(Planta)
admin.site.register(Medicion)
admin.site.register(Evaluacion)
admin.site.register(Evento)
admin.site.register(Foto)
admin.site.register(CambioEstado)

