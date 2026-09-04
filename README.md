# Sistema de gestión de vivero de café

Sistema CRUD para gestionar un vivero de plantas de café orientado a la **selección de
ejemplares** mejor adaptados al clima de Buenos Aires.

## Estado

- **Fase 1 (en curso)**: CRUD base (plantas, mediciones, eventos, fotos, etiquetas,
  selección, roles).
- Fases posteriores: sensores ambientales, estación meteorológica y control de
  riego/iluminación/calefacción.

## Documentación

- [`docs/plan.md`](docs/plan.md) — especificación funcional y técnica (fuente de verdad).
- [`docs/tasks.md`](docs/tasks.md) — etapas, tareas y tests (desglose de trabajo).
- [`docs/review.md`](docs/review.md) — trazabilidad de requisitos y gaps priorizados.
- [`docs/git.md`](docs/git.md) — flujo de Git y repositorio remoto.
- [`AGENTS.md`](AGENTS.md) — roles y modo de trabajo de los agentes de IA.

## Tecnología

Django + PostgreSQL (nube). Ver `docs/plan.md` para el detalle del stack.

## Estructura del proyecto

```
manage.py
config/     # proyecto Django (settings, urls)
nursery/    # app núcleo del dominio
api/        # app API (Django REST Framework)
docs/       # especificación (plan.md, tasks.md)
```

## Configuración del entorno

1. Crear el entorno virtual e instalar dependencias:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. Configurar variables de entorno: copiar `.env.example` a `.env` y completar
   los valores (SECRET_KEY, DEBUG, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST,
   DB_PORT). El archivo `.env` está fuera de control de versiones.

3. Aplicar migraciones y levantar el servidor:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

> El proyecto usa PostgreSQL. La configuración se lee desde variables de
> entorno / `.env` en `config/settings.py`.
