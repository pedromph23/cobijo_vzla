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

### FASE 2 — Bloques C, D, E: cierre territorial

**Commits:** `a58e4b1`, `6d9dcd2`, `0b0a258`

**Bloque C — UbicacionParroquiaMixin mejorado (`a58e4b1`):**
- Nuevo flag `_auto_asignar_parroquia` (default True) para desactivar
  auto-asignación por subclase.
- En `save()`: solo auto-asigna si `parroquia_id` está vacío.
  Respeta asignaciones manuales previas.
- Sin migración (solo métodos Python).

Comportamiento validado con 3 tests:
1. Creación → auto-asigna por geometría.
2. Actualización con parroquia previa → la respeta.
3. Override manual → respeta la asignación.

**Bloque D — unique_together corregido (`6d9dcd2`):**
- `Parroquia.unique_together` cambia de `(nombre, estado)` a
  `(nombre, municipio)`. Refleja la jerarquía territorial real.
- Nuevo índice `(municipio, nombre)`.
- Test: crear parroquia duplicada en el mismo municipio → IntegrityError.
- Sin conflictos previos: 0 grupos afectados.

**Bloque E — ZonaAfectada.parroquia asignada (`0b0a258`):**
- Migración 0023 asigna parroquia a la zona "Hospital Dr. Ricardo".
- Resultado: Sucre → Libertador → Distrito Capital.
- Jerarquía completa operativa: `ZonaAfectada → Parroquia → Municipio → Estado`.

**Estado final FASE 2:**
- 25 estados + 336 municipios + 1122 parroquias.
- 1121/1122 parroquias con municipio asignado (99.9%).
- 1 parroquia sin geometría pendiente de resolver manualmente.
- `ZonaAfectada` con jerarquía territorial completa.
- `UbicacionParroquiaMixin` con override manual y auto-asignación selectiva.

### FASE 3 — Bloques 1-3 y 5: validación universal

**Commits:** `e648433`, `4b78162`, `298fd9c`, `a6aceeb`, `5d76485`

**Bloque 1 — MunicipioForm:**
- Nuevo formulario explícito para el modelo `Municipio` creado en FASE 2.
- Validaciones: `clean_nombre` (validar_nombre_operativo),
  `clean_codigo_ine` (alfanumérico).
- Registrado en `MODELOS_CRUD`, `FORMULARIOS_PERSONALIZADOS` y
  `PERMISOS_POR_GRUPO`. Gestores solo lectura, Administradores CRUD completo.
- Reemplaza el fallback `modelform_factory(fields='__all__')`.

**Bloque 2 — ParroquiaForm con municipio:**
- Campo `municipio` agregado al formulario.
- Filtro dinámico del queryset de municipios según el estado seleccionado.
- Validación `clean()`: municipio debe pertenecer al mismo estado.
- Campos con default en el modelo ahora `required=False`.

**Bloque 3 — Validación MIME real con Pillow:**
- Nuevo validador `validar_imagen_real` en `apps/core/validators.py`.
- Verifica: tamaño, contenido real con `Image.verify()`, dimensiones
  mínimas (100x100) y máximas (10000x10000).
- Aplicado en `ReporteCiudadanoForm` (público) y `ReporteForm` (admin).
- Resuelve: un `.exe` renombrado a `.jpg` ya no pasa.

**Bloque 5 — Rate limiting en endpoints públicos:**
- `apps/core/throttles.py`: 3 clases AnonRateThrottle.
- Rates configurados en `settings.py`:
  - `anon`: 60/min (global).
  - `reporte_ciudadano`: 5/hour (anti-spam).
  - `mapa_calor_publico`: 30/min (anti-DoS).
  - `buscar_lugar`: 30/min (anti-scraping).
- Test verificado: 6º POST a reporte-ciudadano → 429.

**Confirmado en traceback del test:**
El heatmap tiene el N+1 de C11 (`calcular_indice_necesidad` ejecuta 1 query
por parroquia, ~1122 queries por generación). Se mitiga en FASE 5.

### FASE 5 — Rendimiento (5 bloques completados)

**Commits:** `7faf4b1`, `9ed4c55`, `8cea2d6`, más los intermedios.

**Bloque 1 — N+1 en heatmap (CRÍTICO C11):**
- `calcular_indice_necesidad` hacía ~2 queries por parroquia (~2242 total).
- Nueva función `_precalcular_datos_parroquias` con 2 queries SQL agregadas.
- **Antes: >120s. Después: 8.11s. Mejora: 15x.**

**Bloque 2 — N+1 en optimizer (_ponderacion_demanda):**
- 1 query espacial por cada punto de demanda.
- Nueva `_precalcular_zonas_por_demanda` con 1 query agregada (ST_Contains + GROUP BY).

**Bloque 3 — N+1 en reportes (_historicos):**
- 1 + N queries (una por objeto_id).
- Reemplazado por 1 query SQL con `DISTINCT ON (objeto_id)`.
- **Antes: ~8s (149 registros). Después: query pura 0.227ms + latencia de red.**

**Bloque 4 — N+1 en reportes (df_por_estado):**
- 1 query espacial por cada zona afectada.
- Reemplazado por JOIN a la jerarquía FK `ZonaAfectada → Parroquia → Estado`.
- Bug detectado: las geometrías de estados (`.gdb` simplificado) y parroquias
  (otra fuente) no coinciden espacialmente → `ST_Intersects` daba falsos negativos.
- Solución: usar la FK construida en FASE 2 en lugar de operaciones espaciales.

**Bloque 5 — Cache robusto + cache-busting (CRÍTICOS C12, C17):**
- `FileBasedCache` → `DatabaseCache` (tabla `cobijo_cache` en Supabase).
  - Cache compartida entre los 2 workers de gunicorn.
  - Throttles con rate real (no rate × workers).
  - Invalidaciones coherentes.
- Cuantización de pesos en `Pesos.from_request`:
  - Pesos redondeados a múltiplos de 0.5 (STEP), topados en 10.0 (MAX).
  - Reduce el espacio de claves de caché de "infinito" a 21^7.
  - Inalcanzable con el throttle de 30/min por IP.

**Bloque 6 — Índices adicionales:**
- **No fue necesario.**
- `EXPLAIN ANALYZE` mostró que la query de `_historicos` ya usa el índice
  óptimo (`core_regist_modelo_1a3b3d_idx` sobre `(modelo, objeto_id,
  fecha_version DESC)`).
- Execution Time: **0.227ms** en Postgres. La latencia percibida es
  round-trip de red, no cómputo.

**Resumen de mejoras medibles:**

| Componente | Antes | Después | Mejora |
|---|---|---|---|
| Heatmap | >120s | 8.1s | 15x |
| _historicos (149 reg) | ~8s | ~0.2s (query pura) | ~40x |
| df_por_estado | N queries | 1 query FK | ~lineal |
| Throttle efectivo | rate × 2 | rate real | Correcto |
| Cache-busting | Infinitas claves | 21^7 | Acotado |

**Pendiente para FASE 6 (limpieza):**
- Recargar `Estado.geom` y `Parroquia.geom` de la misma fuente con la misma
  simplificación. Actualmente hay gaps que producen falsos negativos con
  ST_Contains/ST_Intersects entre niveles territoriales.

### FASE 6 — Limpieza y consistencia (5 bloques)

**Commits:** `ae6e1f7`, `fe58cfa`, `1d2261e`, `a0620cb`, `71435e7`

**Bloque 1 — Geometrías de estados corregidas:**
- Descubrimiento crítico: las geometrías de Estado sumaban 17,020 km²
  cuando Venezuela tiene ~916,445 km². Ejemplo: Bolívar medía 59 km²
  en BD vs 250,723 km² reales.
- Consecuencia: `ST_Contains`/`ST_Intersects` daban falsos negativos entre
  estados y sus municipios/parroquias.
- Antes: 74/336 municipios y 146/1121 parroquias intersectaban con su estado.
- Fix: exportar los 25 estados del `.gdb` con `-simplify 0.001` (~100 m).
- Después: 336/336 y 1121/1121 intersectan. Área total: 913,832 km².

**Bloque 2 — Parroquia huérfana eliminada:**
- La BD tenía 1122 parroquias vs 1121 en el `.gdb`.
- La extra era "Inmaculada Concepción" (Distrito Capital), sin geometría,
  sin historial, sin referencias, y no en el `.gdb`.
- Fix: migración 0026 elimina el registro con snapshot en RegistroVersion.
- Resultado: Parroquia.objects.count() = 1121.

**Bloque 3 — Migraciones fantasma y tabla huérfana:**
- `django_migrations` tenía 2 entradas sin archivo:
  - core/0004_parametrosmodelo_parametros_p_gte_1_and_more
  - core/0005_auditlog
- Colisionaban con 0004_registroauditoria y 0005_registroversion.
- Tabla `core_auditlog` con 2 filas de pruebas manuales.
- Fix: migración 0027 (DELETE + DROP TABLE) con reversión.
- Resultado: `django_migrations` limpio, tabla eliminada.

**Bloque 4 — Constraints redundantes:**
- 3 CheckConstraint explícitos en ZonaAfectada duplicaban los CHECK
  auto-generados por `PositiveIntegerField`.
- Fix: migración 0028 quita los 3 redundantes.
- Resultado: 7 constraints → 4. Protección intacta.

**Bloque 5 — Documentación:**
- Nuevo `docs/README.md` como índice de documentación técnica.
- Nota al inicio de `README.md` principal apuntando a `docs/`.
- Los documentos técnicos detallados (arquitectura, desarrollo, deployment,
  operaciones, API, permisos) se redactarán en sesiones futuras.

**Hallazgos CRÍTICOS resueltos en FASE 6:**

| # | Descripción | Estado |
|---|---|---|
| C16 (raíz) | Geometrías de estados mal cargadas | ✅ |
| — | 13 parroquias "faltantes" del .gdb | ✅ Aclarado (14 features duplicadas, no faltantes) |
| — | Migraciones fantasma | ✅ |
| — | Tabla core_auditlog huérfana | ✅ |
| — | Constraints redundantes | ✅ |

**Estado territorial final tras FASE 6:**
- Estados: 25 (área 913,832 km², error <0.3%)
- Municipios: 336 (100% intersectan con su estado)
- Parroquias: 1121 (100% intersectan con su estado)
- Coincidencia exacta con el dataset oficial del `.gdb`.

### FASE 4 — Seguridad avanzada (4 bloques)

**Commits:** `13f2d98`, `9d02301`, `296a2be`, `af37e10`

**Bloque 1 — Cabeceras de seguridad y cookies:**
- `SECURE_PROXY_SSL_HEADER`: detecta HTTPS detrás del proxy de Render.
- `SECURE_SSL_REDIRECT`: activo en producción.
- `SECURE_HSTS_SECONDS`: 1 año (31536000 s).
- `SECURE_HSTS_INCLUDE_SUBDOMAINS` y PRELOAD.
- `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`: solo HTTPS en producción.

Todos se activan automáticamente cuando `DEBUG=False`. Verificado con
`python manage.py check --deploy` en ambos modos (0 issues).

**Bloque 2 — LOGGING estructurado:**
- Handler a stdout (Render Logs).
- root: WARNING, django: WARNING, apps propias: INFO.
- Errores y warnings visibles en el dashboard de Render.

**Bloque 3 — IP real del cliente:**
- `ip_cliente` ahora lee `X-Forwarded-For` y toma la primera IP
  (cliente original) con fallback a `REMOTE_ADDR`.
- Los registros de auditoría reflejan la IP real del cliente.

**Bloque 4 — Session hardening:**
- `SESSION_COOKIE_AGE`: 8 horas.
- `SESSION_COOKIE_HTTPONLY`: True.
- `SESSION_COOKIE_SAMESITE`: 'Lax'.
- `CSRF_COOKIE_SAMESITE`: 'Lax'.
- `CSRF_COOKIE_AGE`: 8 horas.

**Verificación end-to-end en producción:**
- Health check OK tras cada deploy.
- Redirección HTTP → HTTPS funcionando.
- Login y sesión funcionan correctamente.
- No hubo loop de redirects.

**Hallazgos resueltos:** A1, A2, S9, S10, S13 del Plan Maestro v2.

### FASE 3 — Bloque 4: detección de duplicados

**Commit:** `e639adf`

Cierra FASE 3 al 100%.

**Nuevo helper `apps/core/dedup.py`:**
- `similitud_nombres(a, b)`: usa `SequenceMatcher` con normalización
  (sin acentos, minúsculas, espacios colapsados) + detección de contención.
  - "Hospital Central" vs "Hospital Central de Caracas" → 0.94 (no 0.74).
  - "Hospital Central" vs "Hospital Universitario" → 0.63.
- `distancia_metros(lat1, lng1, lat2, lng2)`: geodésica vía geopy.
- `buscar_similar(...)`: combina nombre similar (umbral 0.85) + cercanía
  geográfica (umbral 100 m). Devuelve el candidato más similar o None.

**Formularios con detección:**
- `PuntoDemandaForm`: nombre + ubicación.
- `RefugioExistenteForm`: nombre + ubicación.
- `ZonaAfectadaForm`: nombre + evento.

**UI:**
- Nuevo campo `confirmar_duplicado` (checkbox) al final de cada formulario.
- Si hay duplicado y no está marcado, se rechaza con mensaje humano.
- Si está marcado, se permite crear (confirmación explícita).
- En modo edición se excluye la propia instancia de la comparación.

**Tests verificados:**
- Duplicado sin confirmar → valid=False con mensaje claro.
- Duplicado con confirmación → valid=True.
- Registro nuevo sin coincidencias → valid=True.

**Estado final FASE 3 (100%):**
- Bloque 1 — MunicipioForm ✅
- Bloque 2 — ParroquiaForm con municipio ✅
- Bloque 3 — Validación MIME real ✅
- Bloque 4 — Detección de duplicados ✅
- Bloque 5 — Rate limiting ✅

### FASE 7 — Nomenclatura (2 bloques + bonus)

**Commits:** `c0b3efa`, `ab5b605`, `37aab66`

**Bloque 1 — Rename ParametrosModelo → Simulacion:**
- Modelo: `ParametrosModelo` → `Simulacion`.
- Tabla: `core_parametrosmodelo` → `core_simulacion`.
- FK en `ResultadoOptimizacion`: `parametros` → `escenario`.
- Columna: `parametros_id` → `escenario_id`.
- Clases: `ParametrosModeloForm` → `SimulacionForm`,
  `ParametrosModeloAdmin` → `SimulacionAdmin`.
- Claves: `core_parametrosmodelo` → `core_simulacion` en permissions
  y crud_views.
- Migración 0029: RenameModel + RenameField.
- Migración 0030: data fix en `RegistroVersion.modelo`.

Motivación: el nombre anterior confundía con "configuración de sistema".
`Simulacion` refleja su función real: plantilla de simulación de
optimización.

**Bloque 2 — Typo `San Bernandino` → `San Bernardino`:**
- Parroquia id=15 (Municipio Libertador, Distrito Capital).
- Migración 0031: rename verificando nombre antiguo antes de cambiar.
- Resultado: 0 instancias con typo.

**Bonus — Fix de tests preexistentes:**
- `apps/core/tests.py` tenía `test_esta_activa` y `test_cerrar_zona`
  fallando por pasar fechas como string en lugar de datetime.
- Ahora `apps.core: 18/18 tests OK`.

**Estado: 100% del Plan Maestro v2 completado.**

Todas las fases del plan original están cerradas:
- FASE 0 ✅ Sincronización
- FASE 1 ✅ Cimientos y validaciones
- FASE 2 ✅ Integridad territorial
- FASE 3 ✅ Validación universal
- FASE 4 ✅ Seguridad avanzada
- FASE 5 ✅ Rendimiento
- FASE 6 ✅ Limpieza
- FASE 7 ✅ Nomenclatura

### Pendiente (FASE 1+)
- Ver Plan Maestro v2.
