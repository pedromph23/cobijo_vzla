# Changelog — Cobijo VZLA

Todas las modificaciones notables del proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Auditoría v2 — 2026-10-09

**Contexto:** auditoría técnica integral sobre `origin/main` @ `afcd86e`.

**Sincronización:**
- Local, GitHub y Render alineados en `main` @ `afcd86e`.
- Feature `feature/navegacion-venezuela-es` archivada como referencia histórica.
- Tags de respaldo: `pre-auditoria-feature-20261009`, `pre-auditoria-main-local-20261009`.

**Hallazgos:** 19 críticos, 16 altos, 14 medios.

**Plan Maestro v2** emitido con 7 fases. Próxima fase: cimientos de seguridad y deploy.

### Añadido
- `.gitignore`: entradas para `howmigrations` y `myvenv_linux/`.
- `CHANGELOG.md` inicial.

### FASE 1 — Bloque 1: formularios explícitos

**Commit:** `d901f5b`

- 5 formularios nuevos en `apps/mapa/forms.py`: `EstadoForm`, `ParroquiaForm`, `ParametrosModeloForm`, `EventoForm`, `ReporteForm`.
- Registrados en `FORMULARIOS_PERSONALIZADOS` de `apps/mapa/crud_views.py`.
- Reemplaza el fallback `modelform_factory(fields='__all__')` que permitía datos inválidos desde el CRUD.
- **Resuelve CRÍTICO C7** del Plan Maestro v2.

### Fallos detectados en tests (preexistentes, no bloqueantes)

Detectados al correr `python manage.py test apps.mapa`:

1. `ERROR test_geocodifica_y_devuelve_coordenadas` — `geocoding.py:168` `TypeError: 'types.SimpleNamespace' object is not iterable`. **Pendiente FASE 3.**
2. `ERROR test_reutiliza_cache` — mismo origen.
3. `FAIL test_panel_staff_permitido` — test espera `200`, código devuelve `302` (`/panel/` → `/panel/admin/`). Test desactualizado. **Pendiente FASE 6.**

Los 3 fallos existían antes de FASE 1 y no están relacionados con los formularios agregados.

### Pendiente (FASE 1+)
- Ver Plan Maestro v2.
