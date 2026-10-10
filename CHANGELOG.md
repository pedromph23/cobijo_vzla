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

### FASE 1 — Nomenclatura y migraciones

**Commits:** `e968b85`, más el commit del validador centralizado

- `ParametrosModelo.verbose_name` → `'Simulación'` / `'Simulaciones'`.
- Renombrado visible en panel admin y Django admin.
- `apps/core/migrations/0015_alter_parametrosmodelo_options.py` aplicada.
- `apps/core/migrations/0016_restaurar_constraints_zonaafectada.py` restaura 3 CheckConstraints y 2 índices en `ZonaAfectada` que la 0015 había removido.
- Validador centralizado `validar_nombre_operativo` en `apps/core/validators.py` con reglas estrictas (vocal, consonante, máx 40% dígitos).
- 8 `clean_nombre` en `apps/mapa/forms.py` reemplazados por llamada al validador.

**Casos reales resueltos:**
- `343qdxg`, `412312rewdq112`, `q3|1|1`, `asde1qw134`, `1223124`.

**Registrado para FASE 7:**
- Rename real del modelo `ParametrosModelo` → `Simulacion` (tabla + FK).
- Limpiar constraints duplicados en `core_zonaafectada`.

### FASE 1 — Bloque 3: protección de modelos territoriales maestros

**Commit:** `40c7e96`

- `obtener_permisos_usuario` ahora respeta `territorial_master=True` también para usuarios no-staff en el camino por grupos.
- Si un modelo tiene `territorial_master=True` (Estado, Parroquia), el permiso se fuerza a `['ver']` independientemente de lo que el grupo otorgue.
- Antes: usuarios no-staff del grupo "Administradores" podían crear/editar/borrar Estados y Parroquias desde el panel operativo.
- Después: solo lectura en el panel. Edición reservada al Django admin para staff.

**Caso real detectado:** usuario `iujo` (grupos Administradores + Gestores, no staff) veía botones de CRUD en Estados y Parroquias.

**Verificado:** `core_estado` y `core_parroquia` quedan en `['ver']` para `iujo`.

### FASE 1 — Bloque 2: seguridad de endpoints admin

**Commit:** `4fc72cf`

**Endpoints con validación `es_gestor` añadida:**
- `api_estadisticas`
- `api_ejecutar_optimizacion`
- `api_mapa_calor`
- `api_exportar_csv`
- `api_exportar_geojson`

**Fixes:**
- `api_mapa_calor` ahora captura `ValueError` en `float()` de query params. Antes `?densidad=abc` devolvía 500.
- `api_ejecutar_comando` reemplaza `sys.stdout` redirection por `call_command(stdout=salida)`. El redirection global no era thread-safe en gunicorn.
- `api_buscar_lugar` (público) mueve `query` fuera del try para evitar `NameError` si `request.GET` falla.

**Resuelve:** CRÍTICOS C8, C9, C10 y ALTOS A5, A6, A15 del Plan Maestro v2.

### FASE 1 — Bloque 4: robustez del deploy

**Commit:** `e91a914`
**Tag de rollback:** `pre-bloque4-deploy-20261010`

**Problema resuelto:**
El deploy de `e968b85` tardó 17m25s porque `start.sh` ejecutaba `migrate` en
cada arranque del contenedor. Con 2 workers de gunicorn, ambos intentaban
migrar a la vez, causando race conditions y serialización en Postgres.

**Cambios:**
- `start.sh`: quitado `migrate --noinput`. Las migraciones se aplican
  manualmente desde local antes de pushear.
- `start.sh`: agregado `--preload --max-requests 1000 --max-requests-jitter 100`
  a gunicorn.
- `Dockerfile`: usuario no-root `cobijo`.
- `render.yaml`: `healthCheckPath` de `/admin/` a `/health/`.
- `cobijo_vzla/urls.py` + `apps/mapa/urls_health.py`: ruta pública `/health/`.

**Resultado medido:**
- Antes: 17m25s por deploy.
- Después: 1m08s por deploy.
- Mejora: 15x.

**Nota importante para el equipo:**
`preDeployCommand` de Render no está disponible en plan free. **Toda migración
futura debe aplicarse desde local con `python manage.py migrate` antes de
pushear.** De lo contrario, el código se despliega sin los cambios de BD
esperados y la app fallará.

**Resuelve:** CRÍTICO C18 (migrate en cada arranque), ALTOS A3, A4, A14 del
Plan Maestro v2.

### FASE 2 — Limpieza de parroquias duplicadas

**Commit pendiente**
**Migración:** `0017_limpiar_parroquias_duplicadas`

**Problema detectado:**
La BD tenía 149 grupos de parroquias duplicadas (298 registros afectados),
producto de dos importaciones sucesivas con diferente formato de
capitalización:
  - `id=82   'Boca De Chávez'` (primera importación)
  - `id=1132 'Boca de Chávez'` (segunda importación)

Ambos registros eran idénticos salvo la capitalización: misma geometría,
misma población, mismo estado.

**Verificaciones previas:**
- 149 grupos duplicados confirmados.
- Ambos registros con geometría en los 149 grupos.
- Poblaciones idénticas en los 149 grupos.
- Cero `PuntoDemanda` apuntaban a parroquias duplicadas → sin riesgo de
  romper FKs.

**Estrategia aplicada:**
- Normalización de nombre (sin acentos, minúsculas, espacios normalizados).
- Agrupación por `(estado_id, nombre_normalizado)`.
- Conservación del registro con ID MENOR.
- Snapshot del eliminado en `RegistroVersion` para trazabilidad.
- Eliminación del registro con ID MAYOR.

**Resultado:**
- Parroquias: 1271 → 1122.
- Grupos duplicados restantes: 0.
- Snapshots en auditoría: 149.
- Distribución por estado coherente con división territorial real.

**Reversibilidad:**
Los 149 registros eliminados quedan en `RegistroVersion` con
`ruta='migration:0017_limpiar_parroquias_duplicadas'` para restauración
manual si fuera necesario.

### FASE 2 — Bloque B: estructura territorial completa

**Modelo:** `Municipio` creado.

**Migraciones:**
- `0018_create_municipio`: nueva tabla con nombre, estado (FK), codigo_ine,
  geom (MultiPolygon), poblacion, densidad_poblacional, indice_vulnerabilidad.
- `0019_parroquia_municipio_fk`: FK `Parroquia.municipio` (SET_NULL, nullable).
- `0020_zonaafectada_parroquia_fk`: FK `ZonaAfectada.parroquia` (SET_NULL, nullable).
- `0021_poblar_municipios`: 336 municipios desde `.gdb` (capa ven_admin2).
- `0022_asignar_municipio_parroquias`: asignación por geometría.
- `reportes/0003_rename_indexes_django61`: renombrado de índices por cambio
  de hashing en Django 6.1 (inocuo).

**Datos cargados:**
- 336 municipios con código INE del `.gdb` (ej: VE1501).
- 336 con geometría simplificada (`-simplify 0.005` → 533 KB en JSON).

**Asignación de parroquias a municipios:**
- Algoritmo 1: `ST_Contains(municipio.geom, ST_PointOnSurface(parroquia.geom))`.
- Algoritmo 2 (fallback): municipio con mayor área de intersección.
- Filtro: solo municipios del mismo estado de la parroquia.

**Resultado:**
- 1121 / 1122 parroquias con municipio asignado (99.9%).
- 1 parroquia sin asignar: `Inmaculada Concepción` (Distrito Capital)
  porque no tiene geometría cargada. Pendiente resolución manual.
- 0 inconsistencias territoriales (municipio de estado ≠ parroquia).

**Verificación cruzada:**
- Baruta (Miranda): 3 parroquias correctas.
- Chacao (Miranda): 1 parroquia correcta.
- Distribución por estado coherente con la división territorial real.

**Preparado para futuras fases:**
- `UbicacionParroquiaMixin` con override y caché (FASE 2 Bloque C).
- Filtrado territorial en `ZonaAfectada` por parroquia.
- Agregaciones por municipio en reportes.

### Pendiente (FASE 1+)
- Ver Plan Maestro v2.
