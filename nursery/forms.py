import re
from datetime import date

from django import forms

from .models import Evento, Foto, Lote, Medicion, Planta, TipoEvento


class MedicionForm(forms.ModelForm):
    class Meta:
        model = Medicion
        fields = (
            "fecha",
            "altura_cm",
            "diametro_tallo_mm",
            "longitud_hoja_cm",
            "diametro_copa_cm",
            "n_ramas",
            "notas",
        )
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ("tipo", "fecha", "producto", "dosis", "notas")
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class EventoSeleccionForm(forms.Form):
    ALCANCE_CHOICES = [
        ("lote", "Todas las plantas de un lote"),
        ("masivo", "Un conjunto de plantas por códigos"),
    ]

    tipo = forms.ModelChoiceField(queryset=TipoEvento.objects.all(), label="Tipo")
    fecha = forms.DateField(
        initial=date.today, widget=forms.DateInput(attrs={"type": "date"})
    )
    producto = forms.CharField(max_length=200, required=False)
    dosis = forms.CharField(max_length=100, required=False)
    notas = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    alcance = forms.ChoiceField(choices=ALCANCE_CHOICES, label="Aplicar a")
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.all(), required=False, label="Lote"
    )
    codigos = forms.CharField(
        required=False,
        label="Códigos (separados por coma o espacio)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        data = super().clean()
        alcance = data.get("alcance")
        if alcance == "lote" and not data.get("lote"):
            self.add_error("lote", "Elegí un lote para este alcance.")
        elif alcance == "masivo":
            codigos = re.split(r"[\s,]+", (data.get("codigos") or "").strip())
            codigos = [c for c in codigos if c]
            if not codigos:
                self.add_error("codigos", "Ingresá al menos un código.")
            data["lista_codigos"] = codigos
        return data


class FotoForm(forms.ModelForm):
    class Meta:
        model = Foto
        fields = ("imagen", "tipo", "fecha", "activa")
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }


class EstadoForm(forms.ModelForm):
    class Meta:
        model = Planta
        fields = ("estado",)
