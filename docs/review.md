# Revisión integral — Fase 1

> Matriz de trazabilidad entre la especificación (`docs/plan.md`) y lo
> implementado, con la lista priorizada de gaps. Se actualiza al cerrar cada
> gap.

---

## 1. Alcance de la revisión

- **Especificación**: `docs/plan.md` (casos de uso §3, reglas de negocio §10,
  roles §9, stack §4).
- **Implementación revisada**: `nursery/` (modelos, lógica, UI) y `api/` (DRF).
- **Estado general**: Fase 1 funcional, 86 tests en verde, `check` sin issues,
  migraciones limpias y no destructivas.
- **Commit de referencia**: `f42be77` (`feat: implementa Fase 1 del sistema de
  vivero de cafe`).

---

## 2. Trazabilidad — casos de uso (§3)

| # | Caso de uso | Estado | Nota |
|---|---|---|---|
| 1 | Escanear QR y cargar medición | ✅ | Búsqueda por código + formulario de medición |
| 2 | Evento individual / lote / masivo | ✅ | UI + helpers del modelo |
| 3 | Historial de una planta (viverista) | ✅ | Línea de tiempo unificada |
| 4 | Cliente accede al historial vía token | ✅ | Ficha pública por UUID |
| 5 | Comparar fotografías en el tiempo | ✅ | Galería cronológica + comparador lado a lado (M3) |
| 6 | Comparar crecimiento entre candidatas | ✅ | Gráfico multi-planta (altura) |
| 7 | Filtrar / rankear por desempeño | ✅ | Panel de selección |
| 8 | Reporte de supervivencia por procedencia | ✅ | Reportes |
| 9 | Inventario con filtros y contadores | ✅ | Inventario |
| 10 | Auditoría (quién hizo qué) | ✅ | autor/fecha en medición, evento, evaluación, foto y cambio de estado (G5) |
| 11 | Generar etiquetas | ✅ | UI de emisión por lote (G1) |
| 12 | Baja de planta (muerte/venta/regalo/descarte) | ✅ | `fecha_baja`/`motivo_baja` + congelamiento (G3/G4) |
| 13 | Foto de hoja adulta vs general | ✅ | `TipoFoto` |

---

## 3. Trazabilidad — reglas de negocio (§10)

| # | Regla | Estado | Nota |
|---|---|---|---|
| 1 | Medición individual vía QR, formulario único | ✅ | |
| 2 | Eventos individuales / lote / masivos | ✅ | |
| 3 | Promoción desde `Bandeja` (trasplante → `Planta`) | ✅ | Vista `promover_bandeja` (G2) |
| 4 | Estados de salida congelan seguimiento | ✅ | Bloqueo en UI/API (G4) |
| 5 | Productividad de granos (evento `cosecha`) | ⏳ Fase 3 | Diferido correctamente |
| 6 | Auditoría: autor y fecha | ⚠️ parcial | Falta en cambio de estado |
| 7 | Etiquetas pre-emitidas + validación de unicidad | ⚠️ parcial | Validación OK; sin emisión desde el sistema ni persistencia |

---

## 4. Trazabilidad — roles (§9)

| Rol | Permisos | Estado |
|---|---|---|
| Operario | Captura (medir, eventos, fotos, estado) | ✅ |
| Admin | Todo + catálogos + selección + enlace público | ✅ |
| Público | Solo lectura vía token | ✅ |

---

## 5. Stack (§4) — verificación

| Componente | Estado |
|---|---|
| Django + PostgreSQL | ✅ |
| DRF (API) | ✅ |
| Pillow + `django-storages` (S3) | ✅ Pillow activo; S3 **diferido** al despliegue |
| `qrcode` + `python-barcode` | ✅ (lógica) |
| Auth con grupos `admin`/`operario` | ✅ |

---

## 6. Gaps priorizados

### Bloqueantes de completitud de Fase 1 (alcance explícito del plan)

| ID | Gap | Origen | Impacto |
|---|---|---|---|
| G1 | Etiquetas: falta UI/endpoint de generación (variedad + cantidad + formatos → PDF) | CU 11, §5.4, §8.B-12 | ✅ Cerrado |
| G2 | Promoción desde `Bandeja` a `Planta` (sobrevivientes al trasplante) | Regla 3 | ✅ Cerrado |
| G3 | Baja de planta con motivo/fecha (no solo estado) | CU 12, Regla 4 | ✅ Cerrado |
| G4 | Estados de salida congelan seguimiento | Regla 4 | ✅ Cerrado |
| G5 | Histórico de cambios de estado (auditoría) | CU 10, Regla 6 | ✅ Cerrado (modelo `CambioEstado`) |

### Mejoras menores (no bloqueantes)

| ID | Mejora | Estado |
|---|---|---|
| M1 | `LANGUAGE_CODE=es` y `TIME_ZONE=America/Argentina/Buenos_Aires` | ✅ |
| M2 | CSV con BOM UTF-8 para Excel | ✅ |
| M3 | Comparador de fotos lado a lado (CU 5 completo) | ✅ |
| M4 | PUT/PATCH de evento no resincroniza contador fitosanitario (caso borde) | ✅ |

---

## 7. Orden de trabajo propuesto

1. ~~G1 — Etiquetas (UI/endpoint de emisión por lote).~~ ✅
2. ~~G3 + G4 — Baja de planta con motivo/fecha + congelar seguimiento.~~ ✅
3. ~~G2 — Promoción desde `Bandeja`.~~ ✅
4. ~~G5 — Histórico de cambios de estado (modelo `CambioEstado`).~~ ✅
5. ~~Mejoras M1–M4.~~ ✅

> Todos los gaps de Fase 1 cerrados. Backlog restante para Fase 2/3: sensores
> ambientales, control y analítica, productividad de granos (ver `docs/tasks.md`).

> Nota: G3/G5 implican cambios de modelo → migración nueva (a revisar que sea
> no destructiva). Se definirá el enfoque exacto en el prompt de cada tarea.
