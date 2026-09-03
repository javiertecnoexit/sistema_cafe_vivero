# Plan de construcción — etapas, tareas y tests

> Complemento de `docs/plan.md`. Define el desglose de trabajo para el agente
> implementador (`Cline`), en etapas ordenadas con dependencias, criterios de
> aceptación y tests.
>
> - **Fuente de verdad del diseño**: `docs/plan.md`.
> - **Fuente de verdad del desglose de trabajo**: este archivo.
> - Un **task** de este documento = **un prompt** acotado y autocontenido para `Cline`.
> - Convención de tests: **Django TestCase nativo** (`python manage.py test`).

---

## Convenciones transversales

- Nombres de modelos y campos de dominio **en español** (según `docs/plan.md`).
- Resto del código (apps, módulos, funciones) en inglés estándar de Django.
- Cada modelo catálogo registrado en Django Admin.
- Cada task se entrega con: código + migraciones (`makemigrations` + `migrate`) +
  tests + `python manage.py test` en verde.
- No agregar funcionalidad fuera del alcance del task.

---

## Mapa de dependencias (orden de implementación)

```
Etapa 0  Configuración del proyecto
   │
Etapa 1  Catálogos (modelos maestros)
   │
Etapa 2  Núcleo: Planta (depende de Variedad, Lote, Bandeja, Proveedor, EtapaFenologica)
   │
Etapa 3  Mediciones + Evaluaciones + métricas derivadas (depende de Planta)
   │
Etapa 4  Eventos (depende de TipoEvento y Planta)
   │
Etapa 5  Fotos (depende de TipoFoto, Planta, Evento)
   │
Etapa 6  Etiquetas y códigos (depende de Variedad y Planta)
   │
Etapa 7  API REST (DRF) (depende de 1–6)
   │
Etapa 8  Roles y permisos (depende de 1–7)
   │
Etapa 9  UI Captura (móvil) (depende de 1–8)
   │
Etapa 10 UI Consulta y análisis (depende de 1–8)
   │
Etapa 11 Panel de selección + export CSV (depende de 1–10)
   │
Etapa 12 Acceso público vía token (depende de 1–8)
   │
Etapa 13 Reportes de supervivencia/desempeño (depende de 1–11)
```

---

## Etapa 0 — Configuración del proyecto

### 0.1 Scaffold Django + PostgreSQL + entorno
- Crear entorno virtual, proyecto Django, app `nursery` (o `vivero`) y app `api`.
- Configurar PostgreSQL, variables de entorno (`.env` + `.env.example`), `requirements.txt`.
- Instalar dependencias base: Django, `psycopg2-binary`, DRF, Pillow, `django-storages`, `qrcode`, `python-barcode`.
- `settings.py` modular (dev/prod) o mínima con variables de entorno.

**Criterios de aceptación**
- `python manage.py runserver` levanta sin errores.
- `python manage.py migrate` aplica migraciones iniciales de Django.
- `.env` fuera de control de versiones (verificado en `.gitignore`).

**Tests**
- Sanity: `manage.py test` corre sin fallos (sin tests propios aún).
- (Opcional) test de settings: `DEBUG` según entorno.

---

## Etapa 1 — Catálogos (modelos maestros)

### 1.1 Modelos de catálogo
Modelos: `Variedad`, `Proveedor`, `EtapaFenologica`, `TipoEvento`, `TipoFoto`, `Lote`, `Bandeja`.

Campos según `docs/plan.md §5.1`:
- `Variedad`: nombre (único), especie, notas.
- `Proveedor`: nombre, contacto, notas.
- `EtapaFenologica`: nombre, orden.
- `TipoEvento`: nombre.
- `TipoFoto`: nombre.
- `Lote`: nombre, ubicación, tipo (invernadero/lote/hilera).
- `Bandeja`: variedad (FK), origen (proveedor/propia), proveedor (FK opcional), fecha_siembra, n_semillas, notas.

**Criterios de aceptación**
- Migración sin operaciones destructivas.
- Registro en Django Admin con `__str__` legible.
- `Variedad.nombre` único validado.

**Tests**
- Creación de cada modelo con datos mínimos válidos.
- Unicidad de `Variedad.nombre`.
- Relación opcional `Bandeja.proveedor` (puede ser nula).

---

## Etapa 2 — Núcleo: Planta

### 2.1 Modelo `Planta` + estados + código + token
- Modelo `Planta` con campos de `docs/plan.md §5.2`.
- Estados como choices: `activa`, `muerta`, `vendida`, `regalada`, `descartada`, `seleccionada`.
- Código único con prefijo por variedad (formato `PREFIJO-####`) validando unicidad.
- `token_público` (UUID) y `público_activo` (bool).
- Campos denormalizados: `ultima_altura`, `ultimo_diametro`, `ultima_fecha_medicion`,
  `tasa_crecimiento`, `indice_esbeltez`, `n_eventos_fitosanitarios`,
  `score_vigor_actual`, `score_sanidad_actual`.

**Criterios de aceptación**
- Migración correcta, admin registrado.
- El código no puede duplicarse.
- `token_público` se genera automáticamente al crear la planta.

**Tests**
- Creación válida con variedad + lote + bandeja.
- Violación de unicidad de código lanza error.
- `token_público` autogenerado y único.
- Valores por defecto de campos denormalizados (None/0).

---

## Etapa 3 — Mediciones, Evaluaciones y métricas derivadas

### 3.1 Modelos `Medicion` y `Evaluacion`
- `Medicion`: planta (FK), fecha, altura_cm, diametro_tallo_mm, longitud_hoja_cm,
  diametro_copa_cm, n_ramas, notas, autor.
- `Evaluacion`: planta (FK), fecha, score_vigor (1–5), score_sanidad (1–5), notas, autor.
- `autor` vinculado a usuario autenticado (auditoría).

**Criterios de aceptación**
- Admin registrado.
- Scores validados en rango 1–5.

**Tests**
- Creación válida.
- Validación de rango de scores (rechaza 0 y 6).
- Registro de `autor` (con usuario de test).

### 3.2 Métricas derivadas y denormalización
- Al guardar `Medicion`, recalcular en `Planta`: `ultima_altura`, `ultimo_diametro`,
  `ultima_fecha_medicion`, `indice_esbeltez` (`altura/diametro`), `tasa_crecimiento`
  (`(altura₂−altura₁)/(fecha₂−fecha₁)` → cm/semana).
- Al guardar `Evaluacion`, actualizar `score_vigor_actual` y `score_sanidad_actual`.

**Criterios de aceptación**
- Valores derivados se calculan automáticamente (no se digitan).
- Planta con 1 sola medición no tiene tasa de crecimiento.

**Tests**
- Esbeltez correcta con altura y diámetro conocidos.
- Tasa de crecimiento correcta con 2 mediciones separadas.
- Planta con 1 medición: `tasa_crecimiento = None`.
- Scores actualizados tras nueva evaluación.

---

## Etapa 4 — Eventos

### 4.1 Modelo `Evento` (individual / lote / masivo)
- `Evento`: tipo (FK TipoEvento), fecha, producto, dosis, notas, plantas (M2M), autor.
- Helpers para crear evento sobre 1 planta, un lote o N plantas.

**Criterios de aceptación**
- Admin registrado.
- Relación M2M correcta.
- Eventos fitosanitarios incrementan `Planta.n_eventos_fitosanitarios`.

**Tests**
- Evento individual, por lote y masivo (N plantas) crea las relaciones esperadas.
- Evento de tipo fitosanitario incrementa el contador denormalizado.

---

## Etapa 5 — Fotos

### 5.1 Modelo `Foto` + almacenamiento
- `Foto`: planta (FK), imagen, tipo (FK TipoFoto), fecha, activa (bool), autor, evento (FK opcional).
- Configurar `django-storages` + S3 (o almacenamiento local para dev) y Pillow.
- Al marcar una foto como activa, desactivar las demás del mismo tipo en la planta.

**Criterios de aceptación**
- Admin registrado.
- Imagen se guarda y sirve correctamente.
- Una sola foto activa por tipo y planta.

**Tests**
- Subida de imagen válida (con imagen de test).
- Unicidad de foto activa por tipo/planta.

---

## Etapa 6 — Etiquetas y códigos

### 6.1 Generación de etiquetas (pre-emisión) y validación de código
- Generación por lote: elegir variedad + cantidad + formatos (numérico, QR, Code128).
- Generar códigos secuenciales con prefijo por variedad (ej. `CAT-0001`).
- Exportar PDF con `qrcode` + `python-barcode`.
- Validación de unicidad al asignar código a una planta (no exige pre-emisión).

**Criterios de aceptación**
- PDF generable con 1, 2 o 3 formatos.
- Secuencia de códigos correcta y sin duplicados.
- Asignar un código ya usado a otra planta falla.

**Tests**
- Generación de N códigos secuenciales únicos.
- PDF se genera sin excepciones (validar bytes/archivo).
- Asignación de código duplicado rechazada.

---

## Etapa 7 — API REST (DRF)

### 7.1 Serializers + ViewSets
- Endpoints de lectura/escritura para catálogos y núcleo (Variedad, Lote, Bandeja,
  Planta, Medicion, Evaluacion, Evento, Foto).
- Autenticación por sesión/token para escritura.
- Listado filtrable de `Planta` (variedad, origen, lote, etapa, estado).

**Criterios de aceptación**
- Endpoints responden en JSON.
- Escritura protegida por autenticación.

**Tests**
- GET lista/detalle de cada recurso.
- POST/PUT autenticado.
- POST sin autenticación devuelve 401/403.
- Filtros de `Planta`.

---

## Etapa 8 — Roles y permisos

### 8.1 Grupos `admin` y `operario`
- Crear grupos y asignar permisos: `operario` (captura: medir, eventos, fotos, cambiar estado);
  `admin` (todo + catálogos + selección + activar enlaces públicos).
- Aplicar permisos en vistas y API.

**Criterios de aceptación**
- `operario` no puede gestionar catálogos ni panel de selección.
- `admin` tiene acceso total.

**Tests**
- Permisos por grupo en views/API (con usuarios de test).

---

## Etapa 9 — UI Captura (móvil/tablet)

### 9.1 Ficha rápida + formularios de captura
- Búsqueda por QR/código/texto.
- Ficha rápida: *Medir*, *Evento*, *Foto*, *Cambiar estado*.
- Formulario de medición minimalista (básicos + avanzadas opcionales).

**Criterios de aceptación**
- Flujo: escanear/buscar → ficha → acción.
- Solo `operario`/`admin` pueden capturar.

**Tests**
- Vista de búsqueda devuelve la planta correcta.
- Formulario de medición guarda y actualiza denormalizados.

---

## Etapa 10 — UI Consulta y análisis (escritorio)

### 10.1 Inventario + ficha de planta
- Inventario con filtros y contadores.
- Ficha de planta: línea de tiempo unificada (mediciones, eventos, fotos, estados).

### 10.2 Gráfico de crecimiento + comparador de fotos
- Gráfico altura/diámetro/esbeltez (una o múltiples plantas).
- Comparador de fotos (línea de tiempo con miniaturas ampliables).

**Criterios de aceptación**
- Inventario filtrable con contadores correctos.
- Ficha muestra cronología unificada.
- Gráfico renderiza serie temporal correcta.

**Tests**
- Contadores de inventario según filtros.
- Línea de tiempo ordenada cronológicamente.
- Datos del gráfico (endpoint o contexto) correctos.

---

## Etapa 11 — Panel de selección + export CSV

### 11.1 Selección, ranking y export
- Filtros por métrica con umbrales (tasa ≥ X, esbeltez entre Y-Z, vigor ≥ 4, sanidad ≥ 4, máx. eventos fitosanitarios).
- Ventana temporal configurable para crecimiento.
- Ranking mejor/peor por cualquier métrica.
- Índice compuesto ponderado (pesos configurables; default Crec 40 / Esbeltez 20 / Vigor 20 / Sanidad 20).
- Exportación CSV.

**Criterios de aceptación**
- Filtros y ranking correctos.
- Índice compuesto calculado según pesos.
- CSV descargable con las columnas esperadas.

**Tests**
- Filtro por umbral de tasa y esbeltez.
- Ranking correcto.
- Índice ponderado correcto (caso conocido).
- CSV generado con datos correctos.

---

## Etapa 12 — Acceso público vía token

### 12.1 Ficha pública de solo lectura
- Ficha pública accesible por token (no ID interno).
- Muestra: código, variedad, origen, etapa, línea de tiempo, fotos y mediciones.
- Oculta: proveedor, costos, notas internas, scores de vigor/sanidad.
- `público_activo` habilita/deshabilita el acceso.

**Criterios de aceptación**
- URL por token funciona sin login.
- Datos sensibles ocultos.
- Token desactivado → 404/no acceso.

**Tests**
- Acceso con token válido devuelve datos públicos.
- No expone proveedor, costos, notas internas ni scores.
- Token inválido/desactivado deniega acceso.

---

## Etapa 13 — Reportes de supervivencia/desempeño

### 13.1 Reportes agregados por procedencia
- Supervivencia por procedencia (origen/proveedor).
- Desempeño agregado (altura/diámetro/tasa promedio por variedad/procedencia).

**Criterios de aceptación**
- Tabla/gráfico agregado correcto.

**Tests**
- Cálculo de supervivencia por procedencia.
- Promedios de desempeño correctos.

---

## Backlog (esbozo) — Fase 2 y Fase 3

> Sin desglose atómico. Se planificará al cerrar Fase 1.

### Fase 2 — Sensores ambientales
- Modelos de sensor y estación meteorológica.
- API de ingesta de datos ambientales.
- Asociación de lecturas a lote/planta.

### Fase 3 — Control y analítica
- Control de riego/iluminación/calefacción.
- Correlación clima ↔ desempeño.
- Productividad de granos (evento `cosecha`).

---

## Criterios de "definition of done" (cada task)

1. Código implementado y limitado al alcance del task.
2. Migraciones generadas y aplicadas sin operaciones destructivas.
3. Tests del task en verde (`python manage.py test`).
4. Sin regresiones en tests previos.
5. Convenciones respetadas (PEP8, nombres en español para dominio).
6. Lista de lo realizado y lo que falta validar entregada por `Cline`.
