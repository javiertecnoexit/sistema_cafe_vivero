# Plan de diseño — Sistema de gestión de vivero de café

> Documento de diseño funcional y técnico. Fase 1: CRUD base.
> Proyecto orientado a la **selección de ejemplares** de café mejor adaptados al clima de Buenos Aires.
>
> Desglose de etapas, tareas y tests: [`docs/tasks.md`](tasks.md).

---

## 1. Visión

Sistema CRUD para gestionar un vivero de plantas de café con:

- **Trazabilidad individual completa** (código de barras, historial, procedencia).
- **Medición de desempeño** en el tiempo (crecimiento, esbeltez, vigor, sanidad).
- **Registro de eventos** culturales y fitosanitarios, individuales y masivos.
- **Fotografías** fechadas asociadas al individuo.
- **Selección y filtrado** de los mejores/peores ejemplares.
- Preparación para integrar **sensores ambientales y control** en fases posteriores.

---

## 2. Personas

| Persona | Necesidad principal |
|---|---|
| Operario de campo | Capturar mediciones, eventos y fotos rápidamente (móvil) |
| Viverista (admin) | Gestionar, revisar desempeño, decidir selección |
| Cliente / comprador | Ver historial de la planta adquirida (solo lectura) |
| Técnico / asesor | Revisar desempeño y sanidad de forma agregada |

---

## 3. Casos de uso clave

| # | Caso de uso | Implicación de UI / captura |
|---|---|---|
| 1 | Escanear QR y cargar una medición | Búsqueda por QR, formulario minimalista móvil |
| 2 | Registrar evento individual / lote / masivo | Selección de 1, un lote o N plantas + formulario |
| 3 | Ver historial de una planta (viverista) | Ficha de planta con línea de tiempo unificada |
| 4 | Cliente accede al historial de su planta | Ficha pública de solo lectura vía token |
| 5 | Comparar fotografías en el tiempo | Línea de tiempo con miniaturas ampliables |
| 6 | Comparar crecimiento entre candidatas | Gráfico multi-planta |
| 7 | Filtrar/rankear por desempeño | Panel de selección dedicado |
| 8 | Reporte de supervivencia por procedencia | Tabla/gráfico agregado |
| 9 | Inventario con filtros y contadores | Listado filtrable |
| 10 | Auditoría (quién hizo qué) | Autor y fecha en mediciones/eventos/evaluaciones |
| 11 | Generar etiquetas | Por lote (variedad + cantidad + formatos) → PDF; códigos pre-emitidos |
| 12 | Baja de planta (muerte/venta/regalo/descarte) | Acción de cambio de estado con motivo/fecha |
| 13 | Foto de hoja adulta vs foto general | Captura con tipo de foto + fecha |

---

## 4. Stack tecnológico

- **Backend**: Django + PostgreSQL (nube).
- **API**: Django REST Framework (base para la fase de sensores/IoT).
- **Imágenes**: Pillow + `django-storages` (S3).
- **Etiquetas**: `qrcode` + `python-barcode`.
- **Autenticación**: auth de Django con grupos (`admin`, `operario`).
- **Despliegue**: nube (detalles de proveedor/dominio/backups a confirmar al desplegar).

---

## 5. Modelo de datos

### 5.1 Catálogos (tablas maestras)

| Entidad | Campos |
|---|---|
| `Variedad` | nombre (único), especie, notas |
| `Proveedor` | nombre, contacto, notas |
| `EtapaFenologica` | nombre, orden |
| `TipoEvento` | nombre (trasplante, fitosanitario, fertilización, riego, poda, observación, cosecha) |
| `TipoFoto` | nombre (general/actual, hoja, evento, otra) |
| `Lote` | nombre, ubicación, tipo (invernadero/lote/hilera) |
| `Bandeja` | variedad, origen (proveedor/propia), proveedor (FK, opcional), fecha_siembra, n_semillas, notas |

### 5.2 Núcleo

| Entidad | Campos clave |
|---|---|
| `Planta` | código único (prefijo por variedad), variedad, origen (proveedor/propia), proveedor (FK, opcional), bandeja (FK), fecha_alta, etapa, contenedor (suelo/maceta), lote (FK), estado, notas, token_público, público_activo |
| `Medicion` | planta (FK), fecha, altura_cm, diametro_tallo_mm, longitud_hoja_cm, diametro_copa_cm, n_ramas, notas, autor |
| `Evaluacion` | planta (FK), fecha, score_vigor (1-5), score_sanidad (1-5), notas, autor |
| `Evento` | tipo (FK), fecha, producto, dosis, notas, plantas (M2M), autor |
| `Foto` | planta (FK), imagen, tipo (FK), fecha, activa, autor, evento (opcional) |

**Campos denormalizados en `Planta`** (para filtrado/ordenamiento fluido con cientos de plantas, se actualizan al guardar mediciones/evaluaciones/eventos):

- `ultima_altura`, `ultimo_diametro`, `ultima_fecha_medicion`
- `tasa_crecimiento` (cm/semana)
- `indice_esbeltez`
- `n_eventos_fitosanitarios`
- `score_vigor_actual`, `score_sanidad_actual`

### 5.3 Estados de planta

`activa`, `muerta`, `vendida`, `regalada`, `descartada`, `seleccionada`.

### 5.4 Etiquetas y códigos

- **Formato del código**: prefijo por variedad + secuencia (ej. `CAT-0001`).
- **Flujo**: las etiquetas se generan e imprimen **antes** de registrar la planta (etiquetas pre-emitidas); luego se asigna el código al cargar la planta.
- **Generación por lote**: se elige variedad, cantidad y formatos a incluir (numérico, QR, Code128 — 1, 2 o los 3).
- **Asignación**: el código se ingresa por escaneo (QR/Code128) o tecleo del numérico. El sistema **valida unicidad** (no usado en otra planta), sin exigir que haya sido pre-emitido.

---

## 6. Métricas y cálculos

| Métrica | Fórmula / definición |
|---|---|
| Índice de esbeltez | `altura_cm / diametro_tallo_mm` (requiere ambos) |
| Tasa de crecimiento | `(altura₂ − altura₁) / (fecha₂ − fecha₁)`, normalizada a cm/semana, ventana temporal configurable |
| Resistencia sanitaria | nº de eventos fitosanitarios + `score_sanidad` |
| Índice de desempeño | ponderación configurable (default: Crec 40 / Esbeltez 20 / Vigor 20 / Sanidad 20) sobre: tasa de crecimiento, esbeltez (rango ideal), vigor, sanidad |

- **Esbeltez**: es un índice (razón), no una tasa. Muy esbelta = etiolada = débil.
- **Tasa de crecimiento**: al ser la frecuencia de medición irregular, se normaliza al tiempo real transcurrido. Una planta con 1 sola medición no tiene tasa.
- Los valores derivados se calculan automáticamente (no se digitan) y se denormalizan en `Planta` para ordenar rápido.

---

## 7. Selección y filtrado

**Panel de selección dedicado** con:

- Criterios por métrica con umbrales (ej. tasa ≥ X cm/semana, esbeltez entre Y-Z, vigor ≥ 4, sanidad ≥ 4, máx. nº eventos fitosanitarios).
- Ventana temporal configurable para el crecimiento.
- **Ranking** mejor/peor (orden por cualquier métrica).
- **Índice compuesto ponderado** opcional (pesos configurables).
- Filtros por variedad, origen (proveedor/propia), lote, etapa.
- **Exportación** de resultados (CSV).

---

## 8. Interfaz

### A. Captura (móvil/tablet — operario)
1. Escanear (QR / código / búsqueda).
2. Ficha rápida: *Medir*, *Evento*, *Foto*, *Cambiar estado*.
3. Medición: formulario minimalista (básicos + 3 avanzadas opcionales).
4. Evento: individual / lote / masivo.
5. Foto: capturar con tipo + fecha.

### B. Consulta y análisis (escritorio — viverista/técnico)
6. Inventario: filtros + contadores.
7. Ficha de planta = línea de tiempo unificada (trasplantes, mediciones, eventos, fotos, estados).
8. Gráfico de crecimiento (altura/diámetro/esbeltez) + opción multi-planta.
9. Comparador de fotos (línea de tiempo con miniaturas ampliables).
10. Panel de selección (filtros + índice + ranking + export).
11. Reportes de supervivencia/desempeño por procedencia.
12. Generación de etiquetas por lote (variedad + cantidad + formatos) → PDF.

### C. Acceso público (cliente)
13. Ficha pública de solo lectura vía enlace/QR con **token** (no el ID interno).

---

## 9. Acceso y roles

| Rol | Permisos |
|---|---|
| Operario | Captura: medir, eventos, fotos, cambiar estado, registrar planta/bandeja |
| Admin (viverista) | Todo + catálogos + panel de selección + activar enlaces públicos |
| Público (cliente) | Solo lectura de la ficha de su planta vía token |

**Ficha pública**: muestra código, variedad, origen, etapa, línea de tiempo, fotos y mediciones de crecimiento. **Oculta**: proveedor, costos, notas internas y scores de vigor/sanidad.

> Detalle de lo que **ve/busca/ingresa** cada rol y el rediseño móvil de campo
> (cámara para códigos y fotos): ver [`docs/mobile.md`](mobile.md).

---

## 10. Reglas de negocio

1. Medición individual vía QR; formulario único con campos opcionales (se llena lo que se mida).
2. Eventos individuales / por lote / masivos (M2M con 1, un lote o N plantas).
3. Promoción desde `Bandeja`: al primer trasplante, las sobrevivientes pasan a `Planta` individual.
4. Estados de salida (muerta/vendida/regalada/descartada) congelan el seguimiento y quedan en historial.
5. Productividad de granos: evento `cosecha` (cantidad/peso) + métrica opcional; se captura en Fase 3 cuando fructifiquen.
6. Cada medición/evento/evaluación guarda autor y fecha (auditoría).
7. Etiquetas: se generan/emiten por lote antes de cargar la planta; el código se asigna luego validando unicidad.

---

## 11. Fases

- **Fase 1 (ahora)**: CRUD completo + etiquetas + fotos + eventos + mediciones + evaluaciones + panel de selección + roles + acceso público.
- **Fase 2**: API de sensores ambientales y estación meteorológica.
- **Fase 3**: control de riego/iluminación/calefacción + analítica (correlación clima ↔ desempeño) + productividad.

---

## 12. Decisiones de despliegue

- **Entorno de producción**: VPS propio gestionado con **EasyPanel**, despliegue
  con **Docker** (Django + gunicorn + whitenoise + PostgreSQL).
- **Almacenamiento de fotos**: disco persistente del VPS (volumen), sin S3 en
  esta fase. `django-storages` queda instalado para un futuro escalado.
- **Base de datos**: instancia PostgreSQL propia en el VPS.
- Detalles operativos (dominio, HTTPS, backups, seed): ver [`docs/deploy.md`](deploy.md).

**Pendientes menores (no bloqueantes):**

- Dominio y credenciales de producción se definen al contratar el VPS.
- Texto impreso en la etiqueta además del código (por defecto: solo el código en los formatos elegidos; puede añadirse variedad/fecha si se desea).
