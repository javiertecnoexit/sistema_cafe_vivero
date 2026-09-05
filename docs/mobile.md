# Plan de experiencia móvil de campo y roles

> Complemento de `docs/plan.md`. Define el rediseño móvil de la captura en campo
> (invernadero) y el detalle de roles, para priorizar el uso desde el celular.
> Se implementa **después** de validar este plan (no tocar código aún).

---

## 1. Contexto

La mayor parte del trabajo ocurre **en el invernadero**, con el celular en mano.
Objetivos:
- Capturar datos rápido y sin errores usando la **cámara** (leer códigos QR/Code128
  y tomar fotos) sin trasladar archivos.
- Registrar planta/bandeja, mediciones, eventos (riego, etc.) y fotos en flujos
  cortos y con pocos toques.
- Separar claramente lo que **ve y hace** cada rol.

---

## 2. Roles (detalle)

### 2.1 Operario (campo)
**Ve (lectura):**
- Ficha de planta: código, variedad, origen, etapa, contenedor, lote, estado,
  mediciones (altura/diámetro/tasa/esbeltez), scores de vigor/sanidad, fotos,
  historial (timeline).
- Inventario básico (búsqueda por código/QR).
- **No ve**: proveedor, costos, notas internas, panel de selección, reportes,
  etiquetas, enlace público.

**Busca:**
- Una planta por código/QR para trabajar sobre ella.
- Su lote/bandeja.

**Ingresa (escritura):**
- Registrar Planta (con código escaneado o tecleado, validando unicidad).
- Registrar Bandeja.
- Medición, Evento (individual/lote/masivo), Foto (cámara), Cambio de estado.

**No puede:**
- Catálogos, panel de selección, reportes, etiquetas, activar enlace público.

### 2.2 Administrador (viverista)
**Ve:** todo (incluido proveedor, costos, notas internas, scores, inventario completo).
**Busca:** plantas, ranking/panel de selección, reportes.
**Ingresa:** todo + catálogos, etiquetas, promoción de bandeja, enlace público.
**Decide:** selección de ejemplares.

### 2.3 Cliente (público, por token)
**Ve:** solo la ficha pública de su planta (código, variedad, origen, etapa,
historial y fotos). **No** scores, proveedor, costos ni notas.
**No puede:** login, buscar otras plantas, ver inventario.

---

## 3. Principios de UX móvil

- Botones grandes (target táctil), tipografía legible, pocos campos por pantalla.
- "Guardar y seguir": tras guardar, volver a un estado que permita continuar con
  la siguiente planta/acción sin navegar de más.
- Cámara siempre que sea posible (código y foto), teclado numérico en mediciones.
- Acciones por rol visibles desde el home (sin menús anidados).

---

## 4. Captura con cámara

### 4.1 Lectura de códigos (QR y Code128)
- Librería JS: **`html5-qrcode`** (soporta QR y Code128/1D vía ZXing).
- Flujo: botón "Escanear" → abre la cámara → decodifica el código → busca `Planta`
  por `codigo` → redirige a la ficha.
- Si el código no existe: ofrece "Registrar planta con este código" (pre-rellena
  el campo código en el alta).
- Requiere **HTTPS** (getUserMedia); en dev local `localhost` funciona.

### 4.2 Fotos directas desde la cámara
- `<input type="file" accept="image/*" capture="environment">` abre la cámara del
  celular y sube la imagen al formulario (sin transferencia manual de archivos).
- Se aplica al formulario de `Foto` existente (agregando el atributo `capture`).

---

## 5. Flujos móviles propuestos

### 5.1 Home (tras login, según rol)
- Operario: **Escanear código · Registrar planta · Registrar bandeja · Nuevo evento · Buscar**.
- Admin: los anteriores + **Etiquetas · Selección · Reportes · Inventario completo**.

### 5.2 Escanear
Cámara → código → ficha de planta (o alta con código pre-rellenado).

### 5.3 Registrar planta
Formulario mínimo: código (escaneado/tecleado, valida unicidad) → variedad →
origen → contenedor → lote (opcional) → fecha_alta (default hoy) → etapa (opcional)
→ foto inicial (opcional, cámara). Guardar → ficha.

### 5.4 Registrar bandeja
variedad → origen → proveedor (si origen=proveedor) → fecha_siembra → n_semillas →
notas. Guardar → home.

### 5.5 Medición
(ya existe) minimizar a fecha (default hoy), altura, diámetro + avanzadas opcionales.

### 5.6 Evento
- Individual: desde la ficha.
- Global ("Nuevo evento"): riego/fertilización/etc. con alcance (lote / todas /
  lista de códigos), tipo, fecha (default hoy), producto/dosis/notas opcionales.

### 5.7 Foto
Desde la ficha: elegir tipo → capturar con cámara → guardar.

### 5.8 Estado
Desde la ficha: cambiar estado (baja con motivo/fecha si es de salida).

---

## 6. Acceso por rol (aplicación)

| Recurso | Operario | Admin | Público |
|---|---|---|---|
| Ficha planta | ✅ (sin proveedor/costos/notas) | ✅ completo | ✅ (por token, saneada) |
| Registrar planta/bandeja | ✅ | ✅ | — |
| Medición/evento/foto/estado | ✅ | ✅ | — |
| Inventario | ✅ básico | ✅ completo | — |
| Catálogos | — | ✅ | — |
| Etiquetas | — | ✅ | — |
| Panel selección | — | ✅ | — |
| Reportes | — | ✅ | — |
| Enlace público | — | ✅ | — |

> Nota: hoy los permisos de Django ya reflejan parte de esto (grupos `admin`/
> `operario`); falta ajustar la **visibilidad de campos** por rol (ocultar
> proveedor/costos/notas al operario) y habilitar el alta de planta/bandeja para
> el operario.

---

## 7. Consideraciones técnicas

- **HTTPS** obligatorio para la cámara (producción ya usa HTTPS vía EasyPanel).
- **Conectividad en el invernadero**: decisión pendiente. Si la señal es
  inestable, se evalúa una **PWA con captura offline y sincronización** (fase
  futura, más compleja). Si hay WiFi/datos estables, no hace falta.
- **Dependencia**: se añade `html5-qrcode` como recurso estático (sin CDN
  externo obligatorio; se puede servir localmente).

---

## 8. Alcance de cambios vs. lo existente

**Se reutiliza:** modelos, permisos/grupos, formularios de medición/evento/foto/
estado, lógica de códigos/etiquetas, panel de selección, reportes, ficha pública.

**Se agrega:** home móvil por rol, escaneo de códigos con cámara, alta de
planta/bandeja, `capture` en foto, ajuste de visibilidad de campos por rol.

---

## 9. Plan de tareas propuesto (para Cline, posterior a la validación)

| Etapa | Tarea |
|---|---|
| M1 | Home móvil + navegación por rol (menú/acciones) |
| M2 | Escaneo de códigos con cámara (html5-qrcode) → ficha |
| M3 | Alta de Planta y Bandeja desde UI (operario/admin) |
| M4 | Foto directa con cámara (`capture`) |
| M5 | Evento global rápido (riego, etc.) desde home |
| M6 | Ajuste de visibilidad de campos por rol |
| M7 | (opcional, diferido) PWA offline + sincronización |

---

## 10. Decisiones tomadas

1. **Conectividad**: WiFi/datos **estables** → **no** se implementa PWA offline
   (M7 queda como opción futura, no requerida ahora).
2. **Visibilidad del operario**: ve **scores** de vigor/sanidad (dato agronómico
   útil) y **oculta** proveedor, costos y notas internas.
3. **Registrar planta/bandeja**: el **operario sí** puede dar de alta plantas y
   bandejas desde el celular.
