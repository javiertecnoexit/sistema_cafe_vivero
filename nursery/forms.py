import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from .etiquetas import validar_codigo_disponible
from .models import (
    Bandeja,
    Evento,
    Foto,
    Lote,
    Medicion,
    Planta,
    TipoEvento,
    Variedad,
)


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
        ("individual", "Una planta (por código)"),
        ("lote", "Todas las plantas de un lote"),
        ("masivo", "Un conjunto de plantas por códigos"),
    ]

    tipo = forms.ModelChoiceField(queryset=TipoEvento.objects.all(), label="Tipo")
    fecha = forms.DateField(
        initial=date.today, widget=forms.DateInput(attrs={"type": "date"})
    )
    alcance = forms.ChoiceField(choices=ALCANCE_CHOICES, label="Aplicar a")
    codigo_individual = forms.CharField(
        required=False,
        label="Código de la planta",
        widget=forms.TextInput(attrs={"placeholder": "CAT-0001"}),
    )
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.all(), required=False, label="Lote"
    )
    codigos = forms.CharField(
        required=False,
        label="Códigos (separados por coma o espacio)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    producto = forms.CharField(max_length=200, required=False)
    dosis = forms.CharField(max_length=100, required=False)
    notas = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def clean(self):
        data = super().clean()
        alcance = data.get("alcance")
        if alcance == "individual":
            codigo = (data.get("codigo_individual") or "").strip()
            if not codigo:
                self.add_error(
                    "codigo_individual", "Ingresá el código de la planta."
                )
            data["codigo_individual"] = codigo
        elif alcance == "lote":
            if not data.get("lote"):
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
            "imagen": forms.ClearableFileInput(
                attrs={"capture": "environment", "accept": "image/*"}
            ),
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }


class EstadoForm(forms.ModelForm):
    class Meta:
        model = Planta
        fields = ("estado", "fecha_baja", "motivo_baja")
        widgets = {
            "fecha_baja": forms.DateInput(attrs={"type": "date"}),
            "motivo_baja": forms.TextInput(),
        }

    def clean(self):
        data = super().clean()
        estado = data.get("estado")
        if estado in Planta.ESTADOS_DE_SALIDA:
            if not data.get("fecha_baja"):
                self.add_error(
                    "fecha_baja", "La fecha de baja es obligatoria en estados de salida."
                )
            if not data.get("motivo_baja"):
                self.add_error(
                    "motivo_baja", "El motivo de baja es obligatorio en estados de salida."
                )
        else:
            data["fecha_baja"] = None
            data["motivo_baja"] = ""
        return data


class PlantaForm(forms.ModelForm):
    class Meta:
        model = Planta
        fields = (
            "codigo",
            "variedad",
            "origen",
            "proveedor",
            "bandeja",
            "fecha_alta",
            "etapa",
            "contenedor",
            "lote",
            "notas",
        )
        widgets = {
            "fecha_alta": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip()
        try:
            validar_codigo_disponible(codigo)
        except DjangoValidationError as error:
            raise forms.ValidationError(error.messages[0])
        return codigo

    def clean(self):
        data = super().clean()
        origen = data.get("origen")
        if origen == "proveedor" and not data.get("proveedor"):
            self.add_error(
                "proveedor", "El proveedor es obligatorio cuando el origen es proveedor."
            )
        elif origen == "propia":
            data["proveedor"] = None
        return data


class BandejaForm(forms.ModelForm):
    class Meta:
        model = Bandeja
        fields = (
            "variedad",
            "origen",
            "proveedor",
            "fecha_siembra",
            "n_semillas",
            "notas",
        )
        widgets = {
            "fecha_siembra": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        data = super().clean()
        origen = data.get("origen")
        if origen == "proveedor" and not data.get("proveedor"):
            self.add_error(
                "proveedor", "El proveedor es obligatorio cuando el origen es proveedor."
            )
        elif origen == "propia":
            data["proveedor"] = None
        return data


class EtiquetasForm(forms.Form):
    FORMATOS_CHOICES = [
        ("numerico", "Numérico"),
        ("qr", "QR"),
        ("code128", "Code128"),
    ]

    variedad = forms.ModelChoiceField(
        queryset=Variedad.objects.order_by("nombre"), label="Variedad"
    )
    cantidad = forms.IntegerField(min_value=1, initial=1)
    formatos = forms.MultipleChoiceField(
        choices=FORMATOS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Formatos",
    )


class PromocionForm(forms.Form):
    bandeja = forms.ModelChoiceField(
        queryset=Bandeja.objects.order_by("-id"), label="Bandeja"
    )
    sobrevivientes = forms.IntegerField(min_value=1, label="Sobrevivientes")
    fecha_alta = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fecha de alta",
    )
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.order_by("nombre"),
        required=False,
        label="Lote (opcional)",
    )
    contenedor = forms.ChoiceField(
        choices=Planta.CONTENEDOR_CHOICES,
        initial="suelo",
        label="Contenedor",
    )
