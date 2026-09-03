import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.edit import CreateView

from .forms import (
    EstadoForm,
    EventoForm,
    EventoSeleccionForm,
    FotoForm,
    MedicionForm,
)
from .models import (
    EtapaFenologica,
    Evento,
    Foto,
    Lote,
    Medicion,
    Planta,
    Variedad,
)
from .seleccion import PESOS, obtener_filas


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def buscar_planta(request):
    codigo = request.GET.get("codigo", "").strip()
    no_encontrada = False
    if codigo:
        planta = Planta.objects.filter(codigo=codigo).first()
        if planta:
            return redirect("ficha_planta", pk=planta.pk)
        no_encontrada = True
    return render(
        request,
        "nursery/buscar.html",
        {"codigo": codigo, "no_encontrada": no_encontrada},
    )


def _construir_timeline(planta):
    items = []
    for medicion in planta.medicion_set.all():
        items.append(
            {
                "fecha": medicion.fecha,
                "pk": medicion.pk,
                "tipo": "Medición",
                "descripcion": (
                    f"Altura {medicion.altura_cm or '—'} cm · "
                    f"Diámetro {medicion.diametro_tallo_mm or '—'} mm"
                ),
                "imagen": None,
            }
        )
    for evento in planta.evento_set.all():
        descripcion = evento.tipo.nombre
        if evento.producto:
            descripcion += f" · {evento.producto}"
        items.append(
            {
                "fecha": evento.fecha,
                "pk": evento.pk,
                "tipo": "Evento",
                "descripcion": descripcion,
                "imagen": None,
            }
        )
    for foto in planta.foto_set.all():
        items.append(
            {
                "fecha": foto.fecha,
                "pk": foto.pk,
                "tipo": "Foto",
                "descripcion": f"{foto.tipo.nombre}",
                "imagen": foto.imagen,
            }
        )
    return sorted(items, key=lambda item: (item["fecha"], item["pk"]))


def _construir_timeline_publica(planta):
    items = []
    for medicion in planta.medicion_set.all():
        items.append(
            {
                "fecha": medicion.fecha,
                "pk": medicion.pk,
                "tipo": "Medición",
                "descripcion": (
                    f"Altura {medicion.altura_cm or '—'} cm · "
                    f"Diámetro {medicion.diametro_tallo_mm or '—'} mm"
                ),
                "imagen": None,
            }
        )
    for evento in planta.evento_set.all():
        items.append(
            {
                "fecha": evento.fecha,
                "pk": evento.pk,
                "tipo": "Evento",
                "descripcion": evento.tipo.nombre,
                "imagen": None,
            }
        )
    for foto in planta.foto_set.all():
        items.append(
            {
                "fecha": foto.fecha,
                "pk": foto.pk,
                "tipo": "Foto",
                "descripcion": f"{foto.tipo.nombre}",
                "imagen": foto.imagen,
            }
        )
    return sorted(items, key=lambda item: (item["fecha"], item["pk"]))


def ficha_publica(request, token):
    planta = get_object_or_404(
        Planta, token_publico=token, publico_activo=True
    )
    fotos = list(planta.foto_set.select_related("tipo").order_by("fecha", "id"))
    return render(
        request,
        "nursery/publica.html",
        {
            "planta": planta,
            "fotos": fotos,
            "timeline": _construir_timeline_publica(planta),
        },
    )


@login_required
@permission_required("nursery.change_planta", raise_exception=True)
def alternar_publico(request, pk):
    _requiere_admin(request)
    planta = get_object_or_404(Planta, pk=pk)
    if request.method == "POST":
        planta.publico_activo = not planta.publico_activo
        planta.save(update_fields=["publico_activo"])
        estado = "activado" if planta.publico_activo else "desactivado"
        messages.success(request, f"Enlace público {estado}.")
    return redirect("ficha_planta", pk=planta.pk)


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def ficha_planta(request, pk):
    planta = get_object_or_404(Planta, pk=pk)
    activas = Foto.objects.filter(planta=planta, activa=True).order_by(
        "-fecha", "-id"
    )
    foto_actual = (
        activas.filter(tipo__nombre__iexact="General").first() or activas.first()
    )
    fotos = list(planta.foto_set.select_related("tipo").order_by("fecha", "id"))
    return render(
        request,
        "nursery/ficha.html",
        {
            "planta": planta,
            "foto_actual": foto_actual,
            "fotos": fotos,
            "timeline": _construir_timeline(planta),
            "es_admin": _usuario_admin(request.user),
        },
    )


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def inventario(request):
    plantas = (
        Planta.objects.select_related("variedad", "etapa", "lote")
        .order_by("codigo")
    )
    variedad = request.GET.get("variedad")
    if variedad:
        plantas = plantas.filter(variedad_id=variedad)
    origen = request.GET.get("origen")
    if origen:
        plantas = plantas.filter(origen=origen)
    lote = request.GET.get("lote")
    if lote:
        plantas = plantas.filter(lote_id=lote)
    etapa = request.GET.get("etapa")
    if etapa:
        plantas = plantas.filter(etapa_id=etapa)
    estado = request.GET.get("estado")
    if estado:
        plantas = plantas.filter(estado=estado)
    lista_plantas = list(plantas)
    totales = {valor: 0 for valor, _ in Planta.ESTADO_CHOICES}
    for planta in lista_plantas:
        totales[planta.estado] += 1
    contadores_lista = [
        {"valor": valor, "etiqueta": etiqueta, "total": totales[valor]}
        for valor, etiqueta in Planta.ESTADO_CHOICES
    ]
    return render(
        request,
        "nursery/inventario.html",
        {
            "plantas": lista_plantas,
            "contadores_lista": contadores_lista,
            "planta_choices": Planta.ESTADO_CHOICES,
            "variedades": Variedad.objects.order_by("nombre"),
            "lotes": Lote.objects.order_by("nombre"),
            "etapas": EtapaFenologica.objects.order_by("orden"),
            "filtros": request.GET,
        },
    )


class MedicionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Medicion
    form_class = MedicionForm
    permission_required = "nursery.add_medicion"
    template_name = "nursery/medicion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.planta = get_object_or_404(Planta, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"fecha": date.today()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["planta"] = self.planta
        return context

    def form_valid(self, form):
        form.instance.planta = self.planta
        form.instance.autor = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Medición guardada correctamente.")
        return reverse("ficha_planta", kwargs={"pk": self.planta.pk})


@login_required
@permission_required("nursery.add_evento", raise_exception=True)
def evento_planta(request, pk):
    planta = get_object_or_404(Planta, pk=pk)
    form = EventoForm(request.POST or None, initial={"fecha": date.today()})
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        Evento.create_individual(
            tipo=datos["tipo"],
            fecha=datos["fecha"],
            planta=planta,
            autor=request.user,
            producto=datos["producto"],
            dosis=datos["dosis"],
            notas=datos["notas"],
        )
        messages.success(request, "Evento registrado correctamente.")
        return redirect("ficha_planta", pk=planta.pk)
    return render(
        request, "nursery/evento_planta.html", {"form": form, "planta": planta}
    )


@login_required
@permission_required("nursery.add_evento", raise_exception=True)
def evento_nuevo(request):
    if request.method == "POST":
        form = EventoSeleccionForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            if datos["alcance"] == "lote":
                evento = Evento.create_for_lote(
                    tipo=datos["tipo"],
                    fecha=datos["fecha"],
                    lote=datos["lote"],
                    autor=request.user,
                    producto=datos["producto"],
                    dosis=datos["dosis"],
                    notas=datos["notas"],
                )
                mensaje = (
                    f"Evento aplicado a {evento.plantas.count()} plantas del lote."
                )
                messages.success(request, mensaje)
                return redirect("buscar_planta")
            plantas = list(
                Planta.objects.filter(codigo__in=datos["lista_codigos"])
            )
            encontrados = {planta.codigo for planta in plantas}
            faltantes = [
                codigo
                for codigo in datos["lista_codigos"]
                if codigo not in encontrados
            ]
            if faltantes:
                form.add_error(
                    "codigos",
                    "No se encontraron las plantas: " + ", ".join(faltantes),
                )
            else:
                Evento.create_bulk(
                    tipo=datos["tipo"],
                    fecha=datos["fecha"],
                    plantas=plantas,
                    autor=request.user,
                    producto=datos["producto"],
                    dosis=datos["dosis"],
                    notas=datos["notas"],
                )
                messages.success(
                    request, f"Evento aplicado a {len(plantas)} plantas."
                )
                return redirect("buscar_planta")
    else:
        form = EventoSeleccionForm()
    return render(request, "nursery/evento_nuevo.html", {"form": form})


@login_required
@permission_required("nursery.add_foto", raise_exception=True)
def subir_foto(request, pk):
    planta = get_object_or_404(Planta, pk=pk)
    form = FotoForm(
        request.POST or None,
        request.FILES or None,
        initial={"fecha": date.today(), "activa": True},
    )
    if request.method == "POST" and form.is_valid():
        Foto.objects.create(planta=planta, autor=request.user, **form.cleaned_data)
        messages.success(request, "Foto guardada correctamente.")
        return redirect("ficha_planta", pk=planta.pk)
    return render(
        request, "nursery/foto_form.html", {"form": form, "planta": planta}
    )


@login_required
@permission_required("nursery.change_planta", raise_exception=True)
def cambiar_estado(request, pk):
    planta = get_object_or_404(Planta, pk=pk)
    form = EstadoForm(request.POST or None, instance=planta)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            f"Estado actualizado a {planta.get_estado_display()}.",
        )
        return redirect("ficha_planta", pk=planta.pk)
    return render(
        request,
        "nursery/estado_form.html",
        {"form": form, "planta": planta},
    )


def _construir_svg(series):
    ancho, alto = 640, 240
    margen_izq, margen_der, margen_sup, margen_inf = 52, 16, 18, 40
    ancho_util = ancho - margen_izq - margen_der
    alto_util = alto - margen_sup - margen_inf
    colores = ["#2e7d32", "#1565c0", "#c62828", "#6a1b9a", "#ef6c00", "#00695c"]
    pares_planos = [p for s in series for p in s["pares"] if p[1] is not None]
    if not pares_planos:
        return ""
    valores = [valor for _, valor in pares_planos]
    minimo, maximo = min(valores), max(valores)
    rango = maximo - minimo if maximo != minimo else (abs(maximo) or 1.0)
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" '
        f'height="{alto}" viewBox="0 0 {ancho} {alto}">'
    ]
    for k in range(5):
        valor = maximo - rango * k / 4
        y = margen_sup + alto_util * k / 4
        partes.append(
            f'<line x1="{margen_izq}" y1="{y:.1f}" x2="{ancho - margen_der}" '
            f'y2="{y:.1f}" stroke="#e0e0e0"/>'
        )
        partes.append(
            f'<text x="{margen_izq - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#555">{valor:.1f}</text>'
        )

    def coord(i, valor):
        n = len(serie["pares"])
        x = margen_izq + (
            ancho_util * i / (n - 1) if n > 1 else ancho_util / 2
        )
        y = margen_sup + alto_util - alto_util * ((valor - minimo) / rango)
        return x, y

    for idx, serie in enumerate(series):
        color = colores[idx % len(colores)]
        pares = [(fecha, valor) for fecha, valor in serie["pares"] if valor is not None]
        if len(pares) == 1:
            x, y = coord(0, pares[0][1])
            partes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        elif pares:
            puntos = " ".join(
                f"{coord(i, valor)[0]:.1f},{coord(i, valor)[1]:.1f}"
                for i, (_, valor) in enumerate(pares)
            )
            partes.append(
                f'<polyline points="{puntos}" fill="none" stroke="{color}" '
                f'stroke-width="2.5"/>'
            )
        primera = pares[0][0].isoformat() if pares else ""
        ultima = pares[-1][0].isoformat() if pares else ""
        partes.append(
            f'<text x="{margen_izq}" y="{alto - 14}" font-size="11" '
            f'fill="{color}">{serie["codigo"]}</text>'
        )
        if primera and primera != ultima:
            partes.append(
                f'<text x="{ancho - margen_der}" y="{alto - 14}" '
                f'text-anchor="end" font-size="11" fill="#555">{primera} → {ultima}</text>'
            )
    partes.append("</svg>")
    return "".join(partes)


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def grafico_planta(request, pk):
    planta = get_object_or_404(Planta, pk=pk)
    mediciones = list(planta.medicion_set.order_by("fecha", "id"))
    serie_altura = [
        {"fecha": m.fecha, "valor": m.altura_cm}
        for m in mediciones
        if m.altura_cm is not None
    ]
    serie_diametro = [
        {"fecha": m.fecha, "valor": m.diametro_tallo_mm}
        for m in mediciones
        if m.diametro_tallo_mm is not None
    ]
    serie_esbeltez = [
        {
            "fecha": m.fecha,
            "valor": round(m.altura_cm / m.diametro_tallo_mm, 2),
        }
        for m in mediciones
        if m.altura_cm is not None and m.diametro_tallo_mm is not None
    ]
    graficos = []
    for titulo, serie in (
        ("Altura (cm)", serie_altura),
        ("Diámetro del tallo (mm)", serie_diametro),
        ("Índice de esbeltez", serie_esbeltez),
    ):
        graficos.append(
            {
                "titulo": titulo,
                "svg": _construir_svg(
                    [{"codigo": planta.codigo, "pares": [(p["fecha"], p["valor"]) for p in serie]}]
                ),
            }
        )
    return render(
        request,
        "nursery/grafico_planta.html",
        {
            "planta": planta,
            "mediciones": mediciones,
            "serie_altura": serie_altura,
            "serie_diametro": serie_diametro,
            "serie_esbeltez": serie_esbeltez,
            "graficos": graficos,
        },
    )


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def grafico_plantas(request):
    ids = request.GET.getlist("plantas")
    ids = [int(valor) for valor in ids if valor.isdigit()]
    seleccionadas = list(Planta.objects.filter(pk__in=ids).order_by("codigo"))
    series = []
    for planta in seleccionadas:
        pares = [
            (m.fecha, m.altura_cm)
            for m in planta.medicion_set.order_by("fecha", "id")
            if m.altura_cm is not None
        ]
        if pares:
            series.append({"codigo": planta.codigo, "pares": pares})
    return render(
        request,
        "nursery/grafico_plantas.html",
        {
            "plantas_disponibles": Planta.objects.order_by("codigo"),
            "seleccionadas": seleccionadas,
            "svg_multi": _construir_svg(series),
        },
    )


def _usuario_admin(usuario):
    return bool(
        usuario.is_staff or usuario.groups.filter(name="admin").exists()
    )


def _requiere_admin(request):
    if not _usuario_admin(request.user):
        raise PermissionDenied


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def panel_seleccion(request):
    _requiere_admin(request)
    filas = obtener_filas(request.GET)
    claves_orden = [
        ("indice", "Índice"),
        ("tasa", "Tasa de crecimiento"),
        ("esbeltez", "Índice de esbeltez"),
        ("vigor", "Vigor"),
        ("sanidad", "Sanidad"),
    ]
    pesos_display = {clave: int(valor * 100) for clave, valor in PESOS.items()}
    return render(
        request,
        "nursery/panel_seleccion.html",
        {
            "filas": filas,
            "pesos_display": pesos_display,
            "claves_orden": claves_orden,
            "variedades": Variedad.objects.order_by("nombre"),
            "lotes": Lote.objects.order_by("nombre"),
            "etapas": EtapaFenologica.objects.order_by("orden"),
            "filtros": request.GET,
            "csv_query": request.GET.urlencode(),
        },
    )


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def seleccion_csv(request):
    _requiere_admin(request)
    filas = obtener_filas(request.GET)
    respuesta = HttpResponse(content_type="text/csv")
    respuesta["Content-Disposition"] = 'attachment; filename="seleccion.csv"'
    escritor = csv.writer(respuesta)
    escritor.writerow(
        [
            "codigo",
            "variedad",
            "origen",
            "lote",
            "etapa",
            "estado",
            "ultima_altura",
            "ultima_fecha_medicion",
            "tasa_crecimiento",
            "indice_esbeltez",
            "score_vigor",
            "score_sanidad",
            "n_eventos_fitosanitarios",
            "indice",
        ]
    )
    for fila in filas:
        planta = fila["planta"]
        escritor.writerow(
            [
                planta.codigo,
                planta.variedad.nombre,
                planta.get_origen_display(),
                planta.lote.nombre if planta.lote else "",
                planta.etapa.nombre if planta.etapa else "",
                planta.get_estado_display(),
                planta.ultima_altura,
                planta.ultima_fecha_medicion,
                planta.tasa_crecimiento,
                planta.indice_esbeltez,
                planta.score_vigor_actual,
                planta.score_sanidad_actual,
                planta.n_eventos_fitosanitarios,
                fila["indice"],
            ]
        )
    return respuesta


def _etiqueta_procedencia(planta):
    if planta.origen == "proveedor":
        if planta.proveedor_id:
            return f"Proveedor: {planta.proveedor.nombre}"
        return "Proveedor (sin datos)"
    return "Propia"


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)


def _calcular_supervivencia(plantas):
    estados = [estado for estado, _ in Planta.ESTADO_CHOICES]
    grupos = {}
    for planta in plantas:
        procedencia = _etiqueta_procedencia(planta)
        grupo = grupos.setdefault(
            procedencia,
            {
                "procedencia": procedencia,
                "total": 0,
                "desglose": {estado: 0 for estado in estados},
            },
        )
        grupo["total"] += 1
        grupo["desglose"][planta.estado] += 1
    filas = []
    for grupo in grupos.values():
        sobrevivientes = (
            grupo["desglose"]["activa"]
            + grupo["desglose"]["vendida"]
            + grupo["desglose"]["regalada"]
            + grupo["desglose"]["seleccionada"]
        )
        grupo["sobrevivientes"] = sobrevivientes
        grupo["porcentaje"] = (
            round(sobrevivientes / grupo["total"] * 100, 1)
            if grupo["total"]
            else None
        )
        grupo["columnas"] = [
            {"etiqueta": etiqueta, "cantidad": grupo["desglose"][estado]}
            for estado, etiqueta in Planta.ESTADO_CHOICES
        ]
        filas.append(grupo)
    return sorted(filas, key=lambda fila: fila["total"], reverse=True)


def _calcular_desempeno(plantas):
    grupos = {}
    for planta in plantas:
        procedencia = _etiqueta_procedencia(planta)
        clave = (planta.variedad.nombre, procedencia)
        grupo = grupos.setdefault(
            clave,
            {
                "variedad": planta.variedad.nombre,
                "procedencia": procedencia,
                "alturas": [],
                "diametros": [],
                "tasas": [],
            },
        )
        grupo["alturas"].append(planta.ultima_altura)
        grupo["diametros"].append(planta.ultimo_diametro)
        grupo["tasas"].append(planta.tasa_crecimiento)
    filas = []
    for grupo in grupos.values():
        filas.append(
            {
                "variedad": grupo["variedad"],
                "procedencia": grupo["procedencia"],
                "promedio_altura": _promedio(grupo["alturas"]),
                "promedio_diametro": _promedio(grupo["diametros"]),
                "promedio_tasa": _promedio(grupo["tasas"]),
            }
        )
    return sorted(filas, key=lambda fila: (fila["variedad"], fila["procedencia"]))


@login_required
@permission_required("nursery.view_planta", raise_exception=True)
def reportes(request):
    _requiere_admin(request)
    plantas = list(
        Planta.objects.select_related("variedad", "proveedor", "etapa", "lote")
    )
    return render(
        request,
        "nursery/reportes.html",
        {
            "supervivencia": _calcular_supervivencia(plantas),
            "desempeno": _calcular_desempeno(plantas),
            "estados_columnas": [e for _, e in Planta.ESTADO_CHOICES],
        },
    )

