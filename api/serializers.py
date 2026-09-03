from rest_framework import serializers

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


class VariedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variedad
        fields = "__all__"


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"


class EtapaFenologicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtapaFenologica
        fields = "__all__"


class TipoEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoEvento
        fields = "__all__"


class TipoFotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoFoto
        fields = "__all__"


class LoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = "__all__"


class BandejaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bandeja
        fields = "__all__"


class PlantaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planta
        fields = "__all__"
        read_only_fields = (
            "ultima_altura",
            "ultimo_diametro",
            "ultima_fecha_medicion",
            "tasa_crecimiento",
            "indice_esbeltez",
            "n_eventos_fitosanitarios",
            "score_vigor_actual",
            "score_sanidad_actual",
        )


class MedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicion
        fields = "__all__"
        read_only_fields = ("autor",)


class EvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluacion
        fields = "__all__"
        read_only_fields = ("autor",)


class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = "__all__"
        read_only_fields = ("autor",)


class FotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Foto
        fields = "__all__"
        read_only_fields = ("autor",)
