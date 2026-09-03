# AGENTS.md — Guía de trabajo para agentes de IA

Este archivo define los roles y el modo de trabajo de los asistentes de IA del proyecto
(`opencode` y `Cline`). Cualquier agente debe leerlo antes de actuar.

## Propósito del proyecto

Sistema de gestión de un vivero de café orientado a la **selección de ejemplares**
mejor adaptados al clima de Buenos Aires. Tecnología: **Django + PostgreSQL** (Fase 1: CRUD base).

## Fuente única de verdad

- **`docs/plan.md`** — especificación funcional y técnica. Es el documento de referencia.
  Ante cualquier duda o conflicto, **prevalece `docs/plan.md`**.

## Roles

### `opencode` (Planificador / Fiscalizador)
- Escribe y actualiza la especificación (`docs/plan.md`) y este archivo.
- Genera **prompts acotados y autocontenidos** para `Cline` (1 tarea = 1 prompt).
- Revisa el trabajo de `Cline`: lee el diff, corre migraciones, tests y lint.
- No implementa a menos que el usuario lo pida explícitamente.

### `Cline` (Implementador)
- Ejecuta únicamente lo indicado en el prompt que recibe.
- Debe leer `docs/plan.md` antes de comenzar cada tarea.
- **No inventa** campos, modelos ni funcionalidad fuera de lo especificado.
- Hace cambios pequeños y atómicos; no sobre-ingenieriza.
- Ante ambigüedad, pregunta en lugar de asumir.

### Usuario
- Aprueba el plan, valida resultados y decide cuándo hacer commit/push.

## Flujo de trabajo (ciclo de una tarea)

1. `opencode` redacta el prompt (alcance + criterios de aceptación + prohibiciones).
2. `Cline` implementa siguiendo `docs/plan.md` y el prompt.
3. `opencode` fiscaliza: revisa diff, `makemigrations`, `migrate`, `test`, lint.
4. El usuario valida.
5. Commit (solo cuando el usuario lo solicite).

## Reglas para `Cline`

- Leer `docs/plan.md` antes de empezar.
- Implementar solo lo especificado; no agregar funcionalidad extra.
- Respetar las convenciones existentes del código (Django, PEP8).
- **No escribir comentarios innecesarios en el código.**
- No ejecutar migraciones destructivas ni borrar datos sin aviso.
- Entregar una lista clara de lo realizado y de lo que falta validar.

## Reglas para `opencode`

- Mantener `docs/plan.md` actualizado cuando haya cambios de diseño.
- Verificar cada entrega antes de autorizar la siguiente tarea.
- No pedir a `Cline` tareas fuera del alcance definido.

## Convenciones de código

- Python 3, Django, PEP8.
- Nombres de modelos y campos de dominio **en español**, tal como figuran en
  `docs/plan.md` (ej. `altura_cm`, `diametro_tallo_mm`).
- Resto del código en inglés estándar de Django.
- Migraciones: siempre revisar que no incluyan operaciones destructivas.

## Comandos

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

- Lint/formato: **por definir** al configurar el proyecto; se documentará aquí.

## Git

- Ver `docs/git.md` para el flujo de ramas, commits y repositorio remoto.
- **Nunca** commitear, pushear o crear PRs sin que el usuario lo pida explícitamente.
