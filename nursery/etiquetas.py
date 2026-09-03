"""Generación de códigos y etiquetas para plantas de café.

Regla del prefijo: se deriva del nombre de la variedad tomando sus primeras
tres letras (ignorando espacios y tildes), en mayúsculas. Ej.: "Catuaí" -> "CAT".
Los códigos tienen el formato PREFIJO-#### (ej. "CAT-0001") y continúan la
secuencia numérica más alta ya usada por plantas existentes con ese prefijo.
"""

import re
import unicodedata
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw, ImageFont

from .models import Planta

FORMATOS_VALIDOS = ("numerico", "qr", "code128")


def obtener_prefijo(variedad):
    """Devuelve el prefijo de código para una variedad según la regla documentada."""
    nombre = unicodedata.normalize("NFD", variedad.nombre)
    letras = "".join(
        c for c in nombre if unicodedata.category(c) != "Mn" and c.isalpha()
    )
    return letras[:3].upper()


def generar_codigos(variedad, cantidad):
    """Genera `cantidad` códigos secuenciales únicos con el prefijo de la variedad."""
    if cantidad < 1:
        raise ValueError("La cantidad debe ser al menos 1.")
    prefijo = obtener_prefijo(variedad)
    patron = re.compile(rf"^{re.escape(prefijo)}-(\d+)$")
    numeros = []
    for codigo in Planta.objects.values_list("codigo", flat=True):
        if codigo:
            coincidencia = patron.match(codigo)
            if coincidencia:
                numeros.append(int(coincidencia.group(1)))
    siguiente = (max(numeros) if numeros else 0) + 1
    return [f"{prefijo}-{siguiente + i:04d}" for i in range(cantidad)]


def validar_codigo_disponible(codigo):
    """Valida que un código no esté asignado a ninguna planta existente."""
    if Planta.objects.filter(codigo=codigo).exists():
        raise ValidationError(f"El código '{codigo}' ya está asignado a otra planta.")


def _imagen_qr(datos, alto):
    import qrcode

    imagen = qrcode.make(datos).convert("RGB")
    ancho = max(1, round(imagen.width * alto / imagen.height))
    return imagen.resize((ancho, alto), Image.Resampling.LANCZOS)


def _imagen_code128(datos, alto):
    from barcode import get_barcode
    from barcode.writer import ImageWriter

    codigo = get_barcode("code128", datos, writer=ImageWriter())
    buffer = BytesIO()
    codigo.write(buffer, options={"write_text": False})
    buffer.seek(0)
    imagen = Image.open(buffer).convert("RGB")
    ancho = max(1, round(imagen.width * alto / imagen.height))
    return imagen.resize((ancho, alto), Image.Resampling.LANCZOS)


def _imagen_texto(datos, alto):
    fuente = ImageFont.load_default(size=88)
    medidas = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = medidas.textbbox((0, 0), datos, font=fuente)
    ancho = max(1, bbox[2] - bbox[0]) + 80
    imagen = Image.new("RGB", (ancho, alto), "white")
    draw = ImageDraw.Draw(imagen)
    bbox = draw.textbbox((0, 0), datos, font=fuente)
    x = (ancho - (bbox[2] - bbox[0])) / 2 - bbox[0]
    y = (alto - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((x, y), datos, font=fuente, fill="black")
    return imagen


def _renderizar_etiqueta(codigo, formatos):
    alto = 260
    separacion = 30
    margen = 24
    partes = []
    if "numerico" in formatos:
        partes.append(_imagen_texto(codigo, alto))
    if "qr" in formatos:
        partes.append(_imagen_qr(codigo, alto))
    if "code128" in formatos:
        partes.append(_imagen_code128(codigo, alto))
    ancho = margen * 2 + separacion * (len(partes) - 1) + sum(p.width for p in partes)
    etiqueta = Image.new("RGB", (ancho, alto + margen * 2), "white")
    x = margen
    for parte in partes:
        etiqueta.paste(parte, (x, margen))
        x += parte.width + separacion
    return etiqueta


def generar_pdf_etiquetas(variedad, cantidad, formatos):
    """Genera un PDF con una etiqueta por código y lo devuelve como bytes."""
    invalidos = [f for f in formatos if f not in FORMATOS_VALIDOS]
    if invalidos:
        raise ValueError(f"Formatos no válidos: {', '.join(invalidos)}")
    codigos = generar_codigos(variedad, cantidad)
    etiquetas = [_renderizar_etiqueta(c, formatos) for c in codigos]
    buffer = BytesIO()
    etiquetas[0].save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=etiquetas[1:],
        resolution=100.0,
    )
    return buffer.getvalue()
