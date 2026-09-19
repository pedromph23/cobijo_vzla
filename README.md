# 🏠 Cobijo VZLA

> Sistema de gestión geoespacial de refugios y zonas afectadas para situaciones de emergencia en Venezuela.

[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.3-316192)](https://postgis.net/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📋 Tabla de contenidos

- [Descripción](#-descripción)
- [Stack tecnológico](#-stack-tecnológico)
- [Arquitectura](#-arquitectura)
- [Funcionalidades](#-funcionalidades)
- [Sistema de roles y permisos](#-sistema-de-roles-y-permisos)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Instalación local](#-instalación-local)
- [Variables de entorno](#-variables-de-entorno)
- [Guía de uso](#-guía-de-uso)
- [API REST](#-api-rest)
- [Deployment](#-deployment)
- [Mantenimiento](#-mantenimiento)
- [Troubleshooting](#-troubleshooting)
- [Reglas de oro](#-reglas-de-oro)

---

## 📖 Descripción

**Cobijo VZLA** es una aplicación web desarrollada en Django que permite:

- Visualizar en un mapa interactivo los refugios existentes y las zonas afectadas por emergencias.
- Gestionar puntos de demanda (necesidades humanitarias) georreferenciados.
- Optimizar la ubicación de nuevos sitios candidatos mediante programación lineal entera.
- Generar reportes PDF y Excel con estadísticas.
- Proveer un **panel de administración propio** con permisos granulares por grupo de usuario.
- Servir un mapa de calor con índice de necesidad calculado por parroquia.

Diseñado para apoyar a organizaciones humanitarias en la gestión de emergencias.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Python 3.12 · Django 6.1 |
| **API** | Django REST Framework |
| **Base de datos** | PostgreSQL 17 + PostGIS 3.3 |
| **Frontend** | HTML · CSS · JavaScript · Leaflet 1.9 |
| **Optimización** | PuLP (programación lineal entera) |
| **Reportes** | ReportLab (PDF) · openpyxl (Excel) |
| **Análisis** | pandas · numpy · matplotlib |
| **Geoespacial** | GeoDjango · geopy · geojson |
| **Deploy** | Docker · Render · Supabase |
| **CI/CD** | GitHub + Render Auto-Deploy |

---

## 🏗️ Arquitectura

```
┌──────────────┐      ┌─────────────────┐      ┌──────────────┐
│   Usuario    │─────▶│  Render (app)   │─────▶│  Supabase    │
│  (navegador) │      │  Docker +       │      │  Postgres +  │
│              │◀─────│  Django +       │◀─────│  PostGIS     │
└──────────────┘      │  gunicorn       │      └──────────────┘
                      └─────────────────┘
                              ▲
                              │ git push
                      ┌─────────────────┐
                      │  GitHub         │
                      │  (código)       │
                      └─────────────────┘
```

### Servicios utilizados

| Servicio | Rol | Tier |
|----------|-----|------|
| **GitHub** | Repositorio del código | Free |
| **Supabase** | Base de datos Postgres + PostGIS | Free (500 MB) |
| **Render** | Hosting de la app Django | Free (con sleep) |

---

## ✨ Funcionalidades

### Apps internas

| App | Descripción |
|-----|-------------|
| `core` | Modelos base: Estados, Parroquias, Zonas Afectadas, Refugios, Puntos de Demanda, Sitios Candidatos, Parámetros |
| `emergencias` | Gestión de eventos y reportes ciudadanos |
| `optimizacion` | Algoritmos de optimización (P-mediana, P-centro, Cobertura máxima, Capacidades) |
| `mapa` | Panel de gestión + APIs del mapa administrativo |
| `reportes` | Generación de PDFs y Excel |
| `publico` | Mapa público interactivo + búsqueda + reportes ciudadanos |

### Características destacadas

- 🗺️ **Mapa interactivo** con Leaflet (marker clustering, heatmap, minimap)
- 📊 **Análisis geoespacial** con PostGIS
- 🎯 **Optimización de ubicaciones** con PuLP (4 modelos de localización)
- 📄 **Reportes dinámicos** en PDF y Excel
- 🔐 **Sistema CRUD propio** con permisos por grupo (mini-admin personalizado)
- 🌐 **API REST** para integraciones
- 📱 **Diseño responsive** con tema oscuro neón
- 🎤 **Navegación por voz** con Web Speech API (español México)
- 🧭 **Rutas interactivas** con Leaflet Routing Machine + OSRM
- ⚡ **Caché en disco** + precalentamiento del heatmap
- 🛡️ **Protección contra XSS** y path traversal

---

## 👥 Sistema de roles y permisos

El sistema tiene **3 niveles de acceso**:

### 🔴 Superusuario / Staff

- Acceso total a todo el sistema.
- Puede acceder a `/admin/` (Django admin, solo para desarrolladores).
- Ve el **Panel de Administración** con todas las pestañas.
- Puede crear, editar y borrar cualquier modelo.

### 🟣 Administradores (grupo `Administradores`)

- Ve el **Panel de Administración** (`/panel/admin/`).
- Puede gestionar **todos los modelos** del CRUD.
- Puede ejecutar **optimizaciones**.
- Puede cargar datos masivos.
- **NO accede** al `/admin/` de Django (a menos que sea staff).

### 🔵 Gestores (grupo `Gestores`)

- Ve el **Panel Operativo** (`/panel/gestor/`).
- Puede gestionar un **subconjunto de modelos** con permisos limitados:
  - `PuntoDemanda`: ver, crear, editar
  - `RefugioExistente`: ver, editar
  - `ZonaAfectada`: ver, editar
  - `Evento`: ver, editar
  - `Reporte`: ver, editar
  - `SitioCandidato` / `ParametrosModelo`: solo ver
- **NO ve** la pestaña "Optimización".
- **NO puede** borrar registros.

### Matriz de permisos

| Recurso | Admin | Gestor |
|---------|:-----:|:------:|
| Mapa interactivo | ✅ | ✅ |
| Datos (CRUD) | ✅ Total | ⚠️ Limitado |
| Optimización | ✅ | ❌ |
| Reportes | ✅ | ✅ |
| Carga de datos | ✅ | ❌ |
| Django admin | Solo staff | ❌ |

### Configuración

Los permisos se definen en `apps/mapa/permissions.py`:

```python
PERMISOS_POR_GRUPO = {
    'Administradores': {
        'core_estado': ['ver', 'crear', 'editar', 'borrar'],
        # ...todos los modelos
    },
    'Gestores': {
        'core_puntodemanda': ['ver', 'crear', 'editar'],
        'core_refugioexistente': ['ver', 'editar'],
        # ...
    },
}
```

**Para agregar un grupo nuevo**:
1. Crearlo en el admin de Django (`/admin/auth/group/add/`)
2. Agregar la entrada en `PERMISOS_POR_GRUPO`

---

## 📁 Estructura del proyecto

```
cobijo_vzla/
├── .env                          # Variables REALES (NO subir a Git)
├── .env.example                  # Plantilla pública (SÍ subir)
├── .gitignore                    # Exclusiones de Git
├── .gitattributes                # Normalización LF
├── .dockerignore                 # Exclusiones de Docker
├── Dockerfile                    # Receta de construcción
├── start.sh                      # Script de arranque en producción
├── render.yaml                   # Config del deploy en Render
├── requirements.txt              # Dependencias Python
├── manage.py                     # Entry point de Django
│
├── cobijo_vzla/                  # Configuración del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                         # Aplicaciones Django
│   ├── core/                     # Modelos base
│   │   ├── models.py             # Estado, Parroquia, Refugio, Zona...
│   │   ├── admin.py              # Admin de Django
│   │   ├── views.py              # APIs KPIs
│   │   └── urls.py
│   │
│   ├── emergencias/              # Eventos y reportes
│   │   ├── models.py             # Evento, Reporte
│   │   ├── admin.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── mapa/                     # Panel de gestión
│   │   ├── decorators.py         # @gestor_requerido, @admin_requerido
│   │   ├── permissions.py        # ⭐ Config CRUD por grupo
│   │   ├── crud_views.py         # ⭐ Vistas genéricas CBV
│   │   ├── urls_crud.py          # ⭐ Rutas /panel/datos/<modelo>/
│   │   ├── services.py           # Lógica de negocio
│   │   ├── views.py              # Vistas de plantilla + APIs
│   │   ├── urls.py
│   │   └── urls_api.py
│   │
│   ├── optimizacion/             # Algoritmos
│   │   ├── optimizer.py          # PuLP + 4 modelos
│   │   ├── heatmap.py            # Índice de necesidad
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── precalcular_heatmap.py
│   │   └── tests.py
│   │
│   ├── publico/                  # Portal público
│   │   ├── services.py
│   │   ├── views.py              # Mapa, búsqueda, reporte ciudadano
│   │   ├── forms.py
│   │   └── urls_api.py
│   │
│   └── reportes/                 # Generación de reportes
│       ├── generador_reportes.py # Excel + PDF
│       ├── services.py
│       ├── views.py
│       └── urls_api.py
│
├── templates/
│   ├── base.html
│   ├── admin/
│   │   ├── panel_admin.html      # Panel completo (admins)
│   │   ├── panel_gestor.html     # Panel operativo (gestores)
│   │   ├── carga_datos.html
│   │   ├── reportes.html
│   │   └── resultados.html
│   ├── mapa/crud/                # Templates del CRUD
│   │   ├── crud_list.html
│   │   ├── crud_form.html
│   │   └── crud_confirm_delete.html
│   ├── publico/
│   │   ├── mapa_publico.html
│   │   └── reporte_ciudadano.html
│   └── registration/
│       └── login.html
│
├── static/
│   ├── css/                      # Hojas de estilo
│   ├── js/                       # JavaScript
│   ├── img/                      # Imágenes
│   └── vendor/                   # Librerías externas
│       └── leaflet-routing-machine/
│
└── media/                        # Uploads de usuarios (NO subir)
```

---

## 🚀 Instalación local

### Requisitos previos

- Python 3.12+
- PostgreSQL 15+ con PostGIS
- GDAL/GEOS (para GeoDjango)
- Node.js (para dependencias de Leaflet)
- Git

### Windows: instalar GDAL/GEOS

1. Descarga [OSGeo4W](https://trac.osgeo.org/osgeo4w/)
2. Ejecuta el instalador → **Express Install**
3. Añade las rutas al `.env`:

```env
GDAL_LIBRARY_PATH=C:\Users\<usuario>\AppData\Local\Programs\OSGeo4W\bin\gdal313.dll
GEOS_LIBRARY_PATH=C:\Users\<usuario>\AppData\Local\Programs\OSGeo4W\bin\geos_c.dll
```

### Linux / macOS

```bash
sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev  # Debian/Ubuntu
brew install gdal geos proj                                     # macOS
```

### Pasos de instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/pedromph23/cobijo_vzla.git
cd cobijo_vzla

# 2. Crear y activar entorno virtual
python -m venv myvenv
myvenv\Scripts\activate          # Windows
source myvenv/bin/activate       # Linux/Mac

# 3. Instalar dependencias Python
pip install -r requirements.txt

# 4. Instalar dependencias JS
npm install

# 5. Copiar y editar .env
cp .env.example .env
# Editar .env con valores reales

# 6. Aplicar migraciones
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Precalcular heatmap (opcional, ~30s)
python manage.py precalcular_heatmap

# 9. Ejecutar
python manage.py runserver
```

Abrir en el navegador: http://127.0.0.1:8000/

---

## 🔐 Variables de entorno

El proyecto usa `python-dotenv` para leer variables del `.env`.

### `.env` (local, **NO se sube a Git**)

```env
# === Django ===
DJANGO_SECRET_KEY="..."
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# === PostgreSQL local (desarrollo) ===
DB_NAME=cobijo_vzla_db
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432

# === Supabase (producción) ===
DATABASE_URL=postgresql://postgres.<project>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# === GeoDjango (Windows) ===
GDAL_LIBRARY_PATH=...
GEOS_LIBRARY_PATH=...
```

### `.env.example` (público)

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

DATABASE_URL=

GDAL_LIBRARY_PATH=
GEOS_LIBRARY_PATH=
```

### Generar una `SECRET_KEY` nueva

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📚 Guía de uso

### Para Superusuarios / Administradores

1. **Acceder**: `https://cobijo-vzla.onrender.com/panel/`
2. Serás redirigido a `/panel/admin/`
3. Pestañas disponibles:

| Pestaña | Función |
|---------|---------|
| 🗺️ **Mapa** | Visualización geoespacial con capas configurables |
| 📊 **Datos** | CRUD completo de todos los modelos |
| ⚙️ **Optimización** | Ejecutar modelos de localización |
| 📄 **Reportes** | Descargar PDF/Excel |

### Para Gestores

1. **Acceder**: `https://cobijo-vzla.onrender.com/panel/`
2. Serás redirigido a `/panel/gestor/`
3. Pestañas disponibles:

| Pestaña | Función |
|---------|---------|
| 🗺️ **Mapa** | Visualización (refugios + zonas) |
| 📊 **Datos** | CRUD limitado (según permisos) |
| 📄 **Reportes** | Descargar PDF/Excel |

**NO verás** la pestaña "Optimización".

### CRUD de datos (`/panel/datos/`)

1. **Listar**: clic en cualquier tarjeta del grid
2. **Buscar**: campo de búsqueda en la parte superior
3. **Crear**: botón "Nuevo" (si tienes permiso)
4. **Editar**: ícono ✏️ en cada fila
5. **Borrar**: ícono 🗑️ en cada fila (con confirmación)

### Crear un usuario gestor

1. Ir al admin: `/admin/auth/user/add/`
2. Completar username y password
3. **NO marcar** "Staff status" ni "Superuser status"
4. En la sección **Groups**, mover **"Gestores"** a la derecha
5. Guardar

El usuario podrá iniciar sesión y verá el panel de gestor.

### Crear un usuario administrador

1. Ir al admin: `/admin/auth/user/add/`
2. Completar username y password
3. En la sección **Groups**, mover **"Administradores"** a la derecha
4. (Opcional) Marcar "Staff status" si necesita acceso al admin Django
5. Guardar

---

## 🌐 API REST

### Endpoints públicos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/publico/refugios/` | Lista de refugios operativos |
| GET | `/api/publico/zonas-afectadas/` | Zonas activas |
| GET | `/api/publico/mapa-calor/` | Puntos del heatmap |
| GET | `/api/publico/buscar-lugar/?q=<query>` | Búsqueda de lugares |
| POST | `/api/publico/reporte-ciudadano/` | Crear reporte |
| GET | `/api/publico/info-emergencia/` | Teléfonos de emergencia |

### Endpoints autenticados

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/estadisticas/` | KPIs generales |
| GET | `/api/datos-mapa/` | Datos del mapa admin |
| POST | `/api/ejecutar-optimizacion/` | Ejecutar optimización |
| GET | `/api/listar-resultados/` | Historial de optimizaciones |
| GET | `/api/resultados/<id>/` | Detalle de un resultado |
| GET | `/api/mapa-calor-admin/` | Heatmap admin (pesos custom) |
| POST | `/api/ejecutar-comando/` | Ejecutar comando (whitelist) |
| GET | `/api/exportar-csv/` | Exportar resultados CSV |
| GET | `/api/exportar-geojson/` | Exportar centros GeoJSON |
| GET | `/api/reportes/generar/` | Generar reporte |
| GET | `/api/reportes/descargar/<archivo>/` | Descargar reporte |
| GET | `/api/core/api/kpis/` | KPIs extendidos |
| GET | `/api/emergencias/api/kpis/` | KPIs de emergencias |

---

## 🚢 Deployment

### Flujo automático

```
git push origin main
        ↓
GitHub notifica a Render (webhook)
        ↓
Render construye la imagen Docker
        ↓
Ejecuta start.sh (migrate + collectstatic + precalcular_heatmap + gunicorn)
        ↓
Health check a /admin/
        ↓
Live ✅ (o Failed ❌)
```

### Archivos clave

| Archivo | Función |
|---------|---------|
| `Dockerfile` | Instala Python, GDAL, GEOS, PROJ, libpq y deps Python |
| `start.sh` | Runtime: migrate + collectstatic + heatmap + gunicorn |
| `render.yaml` | Config del servicio en Render |

### Variables de entorno en Render

Configuradas en **Dashboard → Service → Environment**:

| Variable | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | Generada por Render |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `<app>.onrender.com,localhost,127.0.0.1` |
| `DATABASE_URL` | URL de Supabase (Transaction Pooler, puerto `6543`) |
| `PYTHON_VERSION` | `3.12.1` |

### Deploy manual

1. Dashboard → servicio → **Manual Deploy**
2. Elegir **Deploy latest commit**
3. Marcar **Clear build cache & deploy** (si hay problemas)

### Sleep del plan gratis

Render Free duerme la app tras **15 min sin tráfico**. La primera petición tarda **30-50 segundos**.

**Soluciones**:
- Servicio de ping externo (UptimeRobot) cada 10 min
- Upgrade a plan pagado

---

## 🔧 Mantenimiento

### Comandos habituales

```bash
# Servidor local
python manage.py runserver

# Migraciones
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Tests
python manage.py test
python manage.py test apps.core
python manage.py test apps.mapa

# Precalcular heatmap (necesario tras cambios de datos)
python manage.py precalcular_heatmap

# Consola interactiva
python manage.py shell
```

### Comandos personalizados

| Comando | Descripción |
|---------|-------------|
| `python manage.py cargar_datos_prueba` | Generar datos ficticios |
| `python manage.py cargar_datos_masivos` | Generar 1500 puntos de demanda |
| `python manage.py importar_limites` | Importar estados/parroquias desde GeoJSON |
| `python manage.py importar_osm` | Importar desde OpenStreetMap |
| `python manage.py importar_zonas_local` | Importar zonas afectadas |
| `python manage.py precalcular_heatmap` | Precalcular caché del heatmap |

### Flujo de un cambio

```bash
# 1. Activar venv
myvenv\Scripts\activate

# 2. Hacer cambios
# ...

# 3. Verificar
python manage.py check
python manage.py test

# 4. Commit + push (Render redespliega automáticamente)
git add .
git commit -m "feat: descripción del cambio"
git push origin main
```

### Backup de la BD

```bash
# Exportar Postgres local
pg_dump -U postgres -h localhost -d cobijo_vzla_db -F c -f backup.dump

# Restaurar en Supabase (con --data-only si las tablas ya existen)
pg_restore -d "$DATABASE_URL" --no-owner --no-acl --data-only backup.dump
```

### Agregar un modelo al CRUD

1. Editar `apps/mapa/permissions.py`
2. Agregar la entrada en `MODELOS_CRUD`:
   ```python
   'mi_app_mimodelo': {
       'app_label': 'mi_app',
       'model_name': 'MiModelo',
       'verbose_name': 'Mi Modelo',
       'verbose_name_plural': 'Mis Modelos',
       'icon': 'fa-icon',
       'list_display': ['campo1', 'campo2'],
       'search_fields': ['campo1'],
       'ordering': ['-pk'],
   },
   ```
3. Agregar permisos en `PERMISOS_POR_GRUPO` para cada grupo
4. **No hace falta tocar las vistas** → son genéricas

---

## 🆘 Troubleshooting

### `exec format error` en Render

**Causa**: `start.sh` tiene line endings CRLF.

**Solución**:
```bash
sed -i 's/\r$//' start.sh
```

### `password authentication failed`

**Causa**: contraseña incorrecta en `.env` o Render.

**Solución**: verificar que ambos tengan la misma URL.

### `column "name" does not exist` en `django_content_type`

**Causa**: tabla en estado inconsistente tras `pg_restore`.

**Solución**: reset del schema + migrar + recargar datos.

### `Could not find GDAL library`

**Causa**: falta `GDAL_LIBRARY_PATH` o librería no instalada.

**Solución local (Windows)**: configurar en `.env`. **Producción**: el Dockerfile ya incluye `gdal-bin`.

### 403 Forbidden en `/panel/`

**Causa**: el usuario no está en ningún grupo con acceso.

**Solución**: agregar el usuario al grupo `Gestores` o `Administradores` desde el admin.

### El heatmap tarda 30s cada vez

**Causa**: la caché expira o no se precargó.

**Solución**: `python manage.py precalcular_heatmap` después de cambios de datos.

### La app tarda 30-50s en cargar

**Causa**: Render Free duerme tras 15 min sin tráfico.

**Solución**: uptime robot o upgrade.

---

## 📌 Reglas de oro

1. **Nunca** subas `.env` a Git
2. **Nunca** pegues contraseñas en chats, issues, ni logs
3. **Siempre** verifica `git status` antes de commitear
4. **Siempre** haz backup antes de tocar la BD de producción
5. **Nunca** corras `migrate --fake` sin entender por qué
6. **Nunca** uses `DROP SCHEMA CASCADE` en producción sin backup
7. **Si dudas, prueba primero en local**
8. **Los scripts `.sh`, `Dockerfile`, `.yaml` van con LF** — usa `.gitattributes`
9. **Rota credenciales** si las expones accidentalmente
10. **Un commit = un cambio lógico** (no "varios fixes mezclados")

---

## 🎓 Comandos de emergencia

```bash
# === ENTORNO ===
myvenv\Scripts\activate                       # Activar venv
deactivate                                     # Desactivar

# === DIAGNÓSTICO ===
python manage.py check                         # Verificar Django
python manage.py showmigrations                # Ver migraciones
python manage.py test                          # Correr tests

# === GIT ===
git status                                     # Ver cambios
git add . && git commit -m "fix: X" && git push origin main

# === BACKUP ===
pg_dump -U postgres -h localhost -d cobijo_vzla_db -F c -f backup.dump

# === RESTORE ===
pg_restore -d "$DATABASE_URL" --no-owner --no-acl --data-only backup.dump

# === LINE ENDINGS ===
file start.sh                                  # Debe decir "ASCII text"
```

---

## 📄 Licencia

Este proyecto está licenciado bajo la **MIT License**. Ver [LICENSE](LICENSE).

---

## 👤 Autor

**Pedro M.**

- GitHub: [@pedromph23](https://github.com/pedromph23)
- Repo: [cobijo_vzla](https://github.com/pedromph23/cobijo_vzla)

---

## 🔗 URLs del proyecto

| Recurso | URL |
|---------|-----|
| Repositorio | https://github.com/pedromph23/cobijo_vzla |
| App en producción | https://cobijo-vzla.onrender.com |
| Admin de producción | https://cobijo-vzla.onrender.com/admin/ |
| Panel de admin | https://cobijo-vzla.onrender.com/panel/admin/ |
| Panel de gestor | https://cobijo-vzla.onrender.com/panel/gestor/ |
| Dashboard Supabase | https://supabase.com/dashboard |
| Dashboard Render | https://dashboard.render.com |

---

<p align="center">
  Hecho con ❤️ para Venezuela 🇻🇪
</p>