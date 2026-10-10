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

### FASE 1 — Bloque 1.5: validaciones en formularios operativos

**Commits:** `fe7bed9`, `94006df`

- Bbox Venezuela en `_parsear_punto` (lat 0.60-12.25, lng -73.50 a -58.05).
- `PuntoDemandaForm`: `clean_nombre`, `clean_poblacion`, `clean_vulnerabilidad`, `clean_descripcion`.
- `SitioCandidatoForm`: `clean_nombre`, `clean_capacidad_maxima`, `clean_costo_apertura`, `clean_costo_operacion`.
- `RefugioExistenteForm`: `clean_nombre`, `clean_direccion`, `clean_capacidad_total`, `clean_capacidad_disponible`, `clean_horario`.
- `ZonaAfectadaForm`: `clean_nombre`, `clean_heridos`, `clean_fallecidos`, `clean_damnificados`, `clean_fecha_inicio`.
- `EventoForm`: `clean_fecha` (rechaza futuro > 5 min, año < 1900).
- `ParametrosModeloForm.clean_nombre_escenario`: rechaza símbolos raros (`|`, `@`).

**Casos reales detectados en producción y resueltos:**
- `PuntoDemanda` con nombre `1223124` → borrado, validación agregada.
- `ParametrosModelo` con nombre `q3|1|1` → borrado, validación agregada.
- `Evento` con fecha futura 2026-10-11 → borrado, validación agregada.

**Registrado para FASE 7:**
- Renombrar `ParametrosModelo` → `Simulacion` (o `Escenario`). Decisión pendiente del usuario.

**Pendiente para FASE 3:**
- Detección de duplicados (advertencia, no bloqueo).
- Regla heurística "60% dígitos" para nombres sospechosos (opcional).
- Validación MIME real de imágenes.

Avanza CRÍTICOS C1-C3 del Plan Maestro v2.

### Pendiente (FASE 1+)
- Ver Plan Maestro v2.
