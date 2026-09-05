# Plan de despliegue — Fase 1 en producción (VPS + EasyPanel)

> Objetivo: poner en producción la **Fase 1** (CRUD completo, sin sensores) en un
> VPS gestionado con EasyPanel, usando Docker. Las **Fases 2 y 3** (sensores,
> control y analítica) se incorporan más adelante, sin bloquear este despliegue.
>
> Estado actual del código: funciona en desarrollo (Django + PostgreSQL local,
> `runserver`, media servido en `DEBUG`). Falta prepararlo para producción.

---

## 1. Arquitectura objetivo

```
Internet
   │  HTTPS (Let's Encrypt vía EasyPanel/Traefik)
   ▼
Reverse proxy (Traefik, integrado en EasyPanel)
   │
   ▼  (puerto 8000 interno)
[ contenedor web: Django + gunicorn + whitenoise ]
   │
   ├─ static (admin/whitenoise)  → servido por gunicorn
   └─ media  (fotos)             → volumen persistente + servido por Django
        │
        ▼
[ contenedor db: PostgreSQL 16 ]
   │
   └─ volumen persistente (datos)
```

- **web**: imagen propia (Django + gunicorn + whitenoise).
- **db**: imagen `postgres:16-alpine` con volumen de datos.
- **media**: volumen persistente montado en el contenedor web.
- **Sin S3**: en un solo VPS el disco es persistente; S3 queda para un futuro
  escalado horizontal. `django-storages` sigue instalado (inactivo).

---

## 2. Cambios de código requeridos (previos al despliegue)

> Estos cambios los implementará el agente `Cline` en una tarea dedicada. Aquí se
> documentan para su revisión.

### 2.1 `config/settings.py`

- `ALLOWED_HOSTS` desde variable de entorno (lista separada por comas), con un
  default seguro solo para dev.
- `CSRF_TRUSTED_ORIGINS` desde variable de entorno (origen `https://dominio`).
- `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- Añadir `whitenoise` a `MIDDLEWARE` (después de `SecurityMiddleware`).
- Añadir `STORAGES` (o mantener default) y dejar `MEDIA_URL`/`MEDIA_ROOT` como
  están (disco persistente).
- Bloque de seguridad opcional cuando `DEBUG=False`:
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`.
- Mantener la carga de `.env` ya existente.

### 2.2 `config/urls.py`

- Servir `media` también en producción (las fotos son públicas en la ficha por
  token): reemplazar el guard `if settings.DEBUG:` por una condición que también
  sirva media en producción (o una ruta explícita con `django.views.static.serve`).

### 2.3 `requirements.txt`

- Añadir `gunicorn>=21` y `whitenoise>=6`.

### 2.4 `Dockerfile` (nuevo, raíz del repo)

- Base `python:3.11-slim`.
- Instalar dependencias, copiar código, `collectstatic` al build.
- `CMD` con `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3`.

### 2.5 `docker-compose.yml` (nuevo, raíz del repo) — opcional

- Servicio `web` (build local) + servicio `db` (`postgres:16-alpine`).
- Volúmenes: `media` (persistente), `staticfiles` (o servido por whitenoise),
  `db_data` (datos de PostgreSQL).

### 2.6 Comando de seed (nuevo, `nursery/management/commands/seed.py`)

- Crea el **superusuario** (admin) si no existe y los **catálogos iniciales**:
  `Variedad`, `TipoEvento` (trasplante, fitosanitario, fertilización, riego, poda,
  observación, cosecha), `TipoFoto` (general, hoja, evento, otra), `EtapaFenologica`,
  y opcionalmente un `Lote` de ejemplo.
- Idempotente (usa `get_or_create`).

---

## 3. Variables de entorno (producción)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta larga y aleatoria | (generar con `secrets.token_urlsafe(64)`) |
| `DEBUG` | `False` en producción | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma | `vivero.example.com,www.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Origen https | `https://vivero.example.com` |
| `DB_NAME` | Nombre de la base | `sistema_cafe_vivero` |
| `DB_USER` | Usuario de BD | `vivero_user` |
| `DB_PASSWORD` | Contraseña de BD | (generar) |
| `DB_HOST` | Host de BD (nombre del servicio) | `db` |
| `DB_PORT` | Puerto de BD | `5432` |

> Nota: `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` son **nuevas** respecto al `.env`
> de desarrollo; se añadirán a `.env.example` al implementar los cambios.

---

## 4. Pasos de despliegue (VPS + EasyPanel)

### 4.1 Pre-requisitos
- VPS con EasyPanel instalado y acceso SSH/panel.
- Dominio apuntando al VPS (registro A).
- Repositorio público/privado accesible (GitHub) o build desde el código local.

### 4.2 Provisionar PostgreSQL
- En EasyPanel, crear el servicio **PostgreSQL 16** (o usar la instancia propia).
- Crear base `sistema_cafe_vivero` y usuario `vivero_user` con contraseña fuerte.
- Guardar las credenciales para el `.env`.

### 4.3 Desplegar la app (web)
1. Subir el código (git) al VPS o conectar el repo en EasyPanel.
2. Construir la imagen Docker (EasyPanel: servicio "Dockerfile" apuntando al repo).
3. Montar el **volumen persistente** para `media` (p. ej. `/app/media`) y para
   `staticfiles` si aplica.
4. Configurar las **variables de entorno** (§3).

### 4.4 Migraciones y datos iniciales
```bash
# dentro del contenedor web (o vía "ejecutar comando" de EasyPanel)
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed
```

### 4.5 Dominio y HTTPS
- En EasyPanel, exponer el servicio web y asignar el dominio.
- Activar HTTPS con Let's Encrypt.

### 4.6 Verificación
- `/` redirige a login; `/admin/` carga con estáticos.
- Login con el superusuario del seed.
- Cargar una `Variedad` y una `Planta`; subir una foto y verificar que se muestra
  en la ficha y en la ficha pública por token.
- `/api/plantas/` responde JSON.

---

## 5. Backups

- **Base de datos**: `pg_dump` programado (cron diario):
  ```bash
  pg_dump -U vivero_user -h db sistema_cafe_vivero > backup_$(date +%F).sql
  ```
- **Media**: copia del volumen `media` (rsync/tar) con la misma frecuencia.
- Guardar ambos fuera del VPS (o al menos en un segundo volumen/objeto).

---

## 6. Actualizaciones futuras

- Subir cambios a `main` → re-desplegar la imagen (EasyPanel "redeploy").
- Siempre ejecutar `migrate` y, si hubo cambios estáticos, `collectstatic`.
- Fases 2/3 se integran como nuevas apps/tareas sin afectar este despliegue.

---

## 7. Checklist de producción

- [ ] `DEBUG=False`.
- [ ] `SECRET_KEY` fuerte y fuera del repo.
- [ ] `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` correctos.
- [ ] HTTPS activo y redirección de HTTP.
- [ ] Migraciones aplicadas y `seed` ejecutado.
- [ ] Estáticos del admin visibles (whitenoise/collectstatic).
- [ ] Fotos (media) persistentes y visibles.
- [ ] Backups programados (BD + media).
- [ ] `.env` de producción nunca en el repo.
