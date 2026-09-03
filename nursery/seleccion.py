"""Panel de selección según docs/plan.md §7.

Normalización de cada componente a 0-100:
- Crecimiento (tasa cm/semana): escala lineal 0-10 cm/semana (se recorta fuera
  del rango). 10+ cm/semana = 100.
- Esbeltez (altura/diámetro): banda ideal 3-5 => 100; por debajo de 3 decae
  linealmente hasta 0 en 0; por encima de 5 decae hasta 0 en 10 (muy esbelta =
  etiolada = peor).
- Vigor y sanidad (1-5): lineales en (valor-1)/4 -> 0-100.
- Métricas ausentes (None) aportan 0 a su componente.
Índice = 0,40*Crec + 0,20*Esbeltez + 0,20*Vigor + 0,20*Sanidad.
"""

from .models import Planta

PESOS = {
    "crecimiento": 0.4,
    "esbeltez": 0.2,
    "vigor": 0.2,
    "sanidad": 0.2,
}
TASA_MAXIMA = 10.0
ESBELTEZ_IDEAL_MIN = 3.0
ESBELTEZ_IDEAL_MAX = 5.0
ESBELTEZ_MAXIMA = 10.0

CLAVES_ORDEN = (
    "indice",
    "tasa",
    "esbeltez",
    "vigor",
    "sanidad",
)


def _num(params, clave):
    valor = params.get(clave)
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _int(params, clave):
    valor = params.get(clave)
    if valor is None or valor == "":
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def _plantas_filtradas(params):
    plantas = Planta.objects.select_related("variedad", "etapa", "lote")
    tasa_min = _num(params, "tasa_min")
    if tasa_min is not None:
        plantas = plantas.filter(tasa_crecimiento__gte=tasa_min)
    esbeltez_min = _num(params, "esbeltez_min")
    if esbeltez_min is not None:
        plantas = plantas.filter(indice_esbeltez__gte=esbeltez_min)
    esbeltez_max = _num(params, "esbeltez_max")
    if esbeltez_max is not None:
        plantas = plantas.filter(indice_esbeltez__lte=esbeltez_max)
    vigor_min = _int(params, "vigor_min")
    if vigor_min is not None:
        plantas = plantas.filter(score_vigor_actual__gte=vigor_min)
    sanidad_min = _int(params, "sanidad_min")
    if sanidad_min is not None:
        plantas = plantas.filter(score_sanidad_actual__gte=sanidad_min)
    fitos_max = _int(params, "fitos_max")
    if fitos_max is not None:
        plantas = plantas.filter(n_eventos_fitosanitarios__lte=fitos_max)
    variedad = params.get("variedad")
    if variedad:
        plantas = plantas.filter(variedad_id=variedad)
    origen = params.get("origen")
    if origen:
        plantas = plantas.filter(origen=origen)
    lote = params.get("lote")
    if lote:
        plantas = plantas.filter(lote_id=lote)
    etapa = params.get("etapa")
    if etapa:
        plantas = plantas.filter(etapa_id=etapa)
    return plantas


def _score_tasa(valor):
    if valor is None:
        return 0.0
    return 100.0 * max(0.0, min(1.0, valor / TASA_MAXIMA))


def _score_esbeltez(valor):
    if valor is None:
        return 0.0
    if ESBELTEZ_IDEAL_MIN <= valor <= ESBELTEZ_IDEAL_MAX:
        return 100.0
    if valor < ESBELTEZ_IDEAL_MIN:
        return 100.0 * max(0.0, valor / ESBELTEZ_IDEAL_MIN)
    return 100.0 * max(
        0.0, (ESBELTEZ_MAXIMA - valor) / (ESBELTEZ_MAXIMA - ESBELTEZ_IDEAL_MAX)
    )


def _score_1_5(valor):
    if valor is None:
        return 0.0
    return 100.0 * (valor - 1) / 4.0


def calcular_indice(planta):
    componentes = {
        "crecimiento": _score_tasa(planta.tasa_crecimiento),
        "esbeltez": _score_esbeltez(planta.indice_esbeltez),
        "vigor": _score_1_5(planta.score_vigor_actual),
        "sanidad": _score_1_5(planta.score_sanidad_actual),
    }
    return round(
        sum(PESOS[clave] * componentes[clave] for clave in PESOS), 2
    )


def _fila_de_planta(planta):
    return {
        "planta": planta,
        "indice": calcular_indice(planta),
        "tasa": planta.tasa_crecimiento,
        "esbeltez": planta.indice_esbeltez,
        "vigor": planta.score_vigor_actual,
        "sanidad": planta.score_sanidad_actual,
    }


def obtener_filas(params):
    filas = [_fila_de_planta(p) for p in _plantas_filtradas(params)]
    clave = params.get("orden_por", "indice")
    if clave not in CLAVES_ORDEN:
        clave = "indice"
    direccion = params.get("direccion", "desc")
    if direccion == "asc":

        def clave_orden(fila):
            valor = fila[clave]
            return (1 if valor is None else 0, valor)

    else:

        def clave_orden(fila):
            valor = fila[clave]
            return (1 if valor is None else 0, -(valor or 0))

    filas.sort(key=clave_orden)
    return filas
