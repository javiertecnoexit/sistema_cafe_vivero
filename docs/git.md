# Git — flujo de trabajo y repositorio remoto

## Repositorio remoto

El repositorio remoto se crea **desde el día uno**, antes de escribir código.

### Creación con GitHub CLI (`gh`)

```bash
gh repo create <org>/<nombre> --private --source . --remote origin --push
```

O, desde la carpeta del proyecto ya inicializada:

```bash
gh repo create <nombre> --private --source . --remote origin
git push -u origin main
```

### Configuración inicial (si no está hecha)

```bash
git init
git config user.name  "Tu Nombre"
git config user.email "tu@email.com"
```

## Rama principal

- `main` — rama protegida, siempre en estado funcional.

## Flujo de ramas

- Cada tarea se desarrolla en una rama corta y descriptiva: `feat/`, `fix/`, `docs/`.
- Ejemplo: `feat/modelo-planta`, `fix/validacion-codigo`.
- Al terminar, se integra a `main` (merge o PR) cuando el usuario lo apruebe.

## Convención de commits

- Mensajes cortos, en español, verbo en imperativo.
- Prefijo por tipo: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Ejemplo: `feat: agrega modelo Planta y catálogo de variedades`.

## Reglas

- **Nunca** commitear, pushear o crear PRs sin que el usuario lo solicite explícitamente.
- No subir secretos ni archivos `.env`.
- Revisar `git status` y `git diff` antes de cada commit; agregar solo lo intencional.
