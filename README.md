# 🏠 Cobijo VZLA

git add README.md
git commit -m "docs: README completo con guía de mantenimiento"
git push origin main

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
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Instalación local](#-instalación-local)
- [Variables de entorno](#-variables-de-entorno)
- [Comandos de Django](#-comandos-de-django)
- [Base de datos](#-base-de-datos)
- [Deployment](#-deployment)
- [Mantenimiento](#-mantenimiento)
- [Troubleshooting](#-troubleshooting)
- [Reglas de oro](#-reglas-de-oro)
- [Autor](#-autor)

---

## 📖 Descripción

**Cobijo VZLA** es una aplicación web desarrollada en Django que permite:

- Visualizar en un mapa interactivo los refugios existentes y las zonas afectadas por emergencias.
- Gestionar puntos de demanda (necesidades humanitarias) georreferenciados.
- Optimizar la ubicación de nuevos sitios candidatos según parámetros configurables.
- Generar reportes y análisis geoespaciales.
- Proveer un panel administrativo completo para la gestión de datos.

Está diseñado para apoyar a organizaciones humanitarias y equipos de respuesta ante emergencias en Venezuela.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Python 3.12 · Django 6.1 |
| **API** | Django REST Framework |
| **Base de datos** | PostgreSQL 17 + PostGIS 3.3 |
| **Frontend** | HTML · CSS · JavaScript · Leaflet |
| **Optimización** | PuLP (programación lineal) |
| **Reportes** | ReportLab · openpyxl |
| **Análisis** | pandas · numpy · matplotlib |
| **Geoespacial** | GeoDjango · geopy · geojson |
| **Deploy** | Docker · Render |
| **BD en producción** | Supabase |
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
                              │
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
| `core` | Modelos base: Estados, Parroquias, Zonas Afectadas, Refugios, Puntos de Demanda |
| `emergencias` | Gestión de eventos y reportes ciudadanos |
| `optimizacion` | Algoritmos de optimización de ubicación de refugios |
| `mapa` | Vistas y APIs para el mapa interactivo |
| `reportes` | Generación de PDFs y Excel |
| `publico` | Vistas públicas del sistema |

### Características destacadas

- 🗺️ **Mapa interactivo** con Leaflet (marker clustering, heatmap, minimap)
- 📊 **Análisis geoespacial** con PostGIS
- 🎯 **Optimización de ubicaciones** con PuLP
- 📄 **Reportes dinámicos** en PDF y Excel
- 🔐 **Panel administrativo** completo
- 🌐 **API REST** para integraciones
- 📱 **Diseño responsive** con modo oscuro

---

## 📁 Estructura del proyecto

```
cobijo_vzla/
├── .env                     # Variables REALES (NO subir a Git)
├── .env.example             # Plantilla pública (SÍ subir)
├── .gitignore               # Archivos que Git ignora
├── .gitattributes           # Normalización de line endings
├── .dockerignore            # Archivos que Docker ignora
├── Dockerfile               # Receta de construcción Docker
├── start.sh                 # Script de arranque en producción
├── render.yaml              # Config del deploy en Render
├── requirements.txt         # Dependencias Python
├── manage.py                # Entry point de Django
├── myvenv/                  # Entorno virtual (NO subir)
├── cobijo_vzla/             # Configuración del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                    # Apps de Django
│   ├── core/
│   ├── emergencias/
│   ├── optimizacion/
│   ├── mapa/
│   ├── reportes/
│   └── publico/
├── templates/               # HTMLs
├── static/                  # CSS, JS, imágenes
└── media/                   # Uploads de usuarios (NO subir)
```

---

## 🚀 Instalación local

### Requisitos previos

- Python 3.12+
- PostgreSQL 15+ con PostGIS
- GDAL/GEOS (para GeoDjango)
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

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar el archivo de ejemplo y editar variables
cp .env.example .env
# Editar .env con los valores reales

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Ejecutar servidor de desarrollo
python manage.py runserver
```

Abrir en el navegador: http://127.0.0.1:8000/

---

## 🔐 Variables de entorno

El proyecto usa `python-dotenv` para leer variables del archivo `.env`.

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
DATABASE_URL=postgresql://postgres.<project-id>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# === GeoDjango (Windows) ===
GDAL_LIBRARY_PATH=...
GEOS_LIBRARY_PATH=...
```

### `.env.example` (público, **SÍ se sube a Git**)

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

> ⚠️ **Nunca** subas el `.env` real al repositorio. Ya está en `.gitignore`.

---

## ⚙️ Comandos de Django

### Activar / desactivar entorno

```bash
myvenv\Scripts\activate      # Windows
source myvenv/bin/activate   # Linux/Mac
deactivate                   # Salir
```

### Comandos habituales

| Comando | Descripción |
|---------|-------------|
| `python manage.py check` | Verifica que no haya errores |
| `python manage.py runserver` | Inicia servidor de desarrollo |
| `python manage.py migrate` | Aplica migraciones a la BD |
| `python manage.py makemigrations` | Genera migraciones desde modelos |
| `python manage.py showmigrations` | Ver migraciones aplicadas |
| `python manage.py createsuperuser` | Crear admin |
| `python manage.py changepassword <user>` | Cambiar contraseña |
| `python manage.py shell` | Consola interactiva |
| `python manage.py collectstatic` | Recolectar archivos estáticos |
| `python manage.py dbshell` | Abrir consola SQL de la BD |

### Comandos personalizados del proyecto

| Comando | Descripción |
|---------|-------------|
| `python manage.py cargar_datos_masivos` | Cargar datos desde archivos |
| `python manage.py importar_limites` | Importar límites geográficos |
| `python manage.py importar_osm` | Importar desde OpenStreetMap |
| `python manage.py importar_zonas_local` | Importar zonas afectadas |

### Consola interactiva

```bash
python manage.py shell
```

Ejemplos:

```python
from django.contrib.auth import get_user_model
from apps.core.models import Estado, Parroquia, RefugioExistente

# Contar registros
Estado.objects.count()
Parroquia.objects.count()
RefugioExistente.objects.count()

# Listar usuarios
User = get_user_model()
list(User.objects.values_list('username', 'is_superuser'))

exit()
```

---

## 🗄️ Base de datos

### Exportar backup (desde Postgres local)

```bash
pg_dump -U postgres -h localhost -p 5432 -d cobijo_vzla_db \
  -F c -b -f "backup_$(date +%Y-%m-%d).dump"
```

### Restaurar datos en Supabase

```bash
# Solo datos (requiere que las tablas ya existan)
pg_restore -d "$DATABASE_URL" \
  --no-owner --no-acl --data-only -v \
  "backup.dump"
```

### Restaurar una sola tabla

```bash
pg_restore -d "$DATABASE_URL" \
  --no-owner --no-acl --data-only \
  -t core_zonaafectada -v \
  "backup.dump"
```

### Filtrar errores reales del log

```bash
grep "error:" restore_log.txt | grep -v "RI_ConstraintTrigger"
```

### Consultas útiles en Supabase (SQL Editor)

```sql
-- Ver todas las tablas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Verificar PostGIS
SELECT PostGIS_Version();

-- Ver migraciones aplicadas
SELECT app, name, applied 
FROM django_migrations 
ORDER BY applied DESC;

-- Conteo de filas
SELECT 'core_estado' AS tabla, COUNT(*) FROM core_estado
UNION ALL
SELECT 'core_parroquia', COUNT(*) FROM core_parroquia
UNION ALL
SELECT 'core_zonaafectada', COUNT(*) FROM core_zonaafectada
UNION ALL
SELECT 'core_refugioexistente', COUNT(*) FROM core_refugioexistente;
```

### Connection strings de Supabase

| Modo | Puerto | Host | Uso |
|------|--------|------|-----|
| Direct | 5432 | `db.<project>.supabase.co` | A veces bloqueado |
| Session Pooler | 5432 | `aws-0-<region>.pooler.supabase.com` | Migraciones |
| **Transaction Pooler** | **6543** | `aws-0-<region>.pooler.supabase.com` | **Apps** ✅ |

> 💡 **Usa siempre el Transaction Pooler (6543)** para Django en producción.

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
Ejecuta start.sh (migrate + collectstatic + gunicorn)
        ↓
Health check a /admin/
        ↓
Live ✅ (o Failed ❌)
```

### Archivos clave del deploy

**`Dockerfile`** — instala Python, GDAL, GEOS, PROJ, libpq y las dependencias Python.

**`start.sh`** — corre en runtime: migrate + collectstatic + gunicorn.

**`render.yaml`** — configuración del servicio en Render.

### Variables de entorno en Render

Configuradas en **Dashboard → Service → Environment**:

| Variable | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | Generada por Render (automático) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `<app-name>.onrender.com,localhost,127.0.0.1` |
| `DATABASE_URL` | URL de Supabase (Transaction Pooler, puerto 6543) |
| `PYTHON_VERSION` | `3.12.1` |

### Forzar redeploy

1. Dashboard → servicio → **Manual Deploy**
2. Elegir **Deploy latest commit**
3. Marcar **Clear build cache & deploy** (si hay problemas)

### Sleep del plan gratis

Render Free duerme la app tras **15 minutos sin tráfico**. La primera petición tarda **30-50 segundos** en despertarla.

**Opciones**:

- Usar un servicio de ping externo (UptimeRobot, cron-job.org) cada 10 min.
- Subir a plan pagado.

---

## 🔧 Mantenimiento

### Hacer un cambio y desplegarlo

```bash
# 1. Activar venv
myvenv\Scripts\activate

# 2. Hacer los cambios en el código

# 3. Probar en local
python manage.py check
python manage.py runserver

# 4. Ver qué cambió
git status
git diff

# 5. Commit
git add .
git commit -m "feat: descripción del cambio"

# 6. Push → Render redespliega automáticamente
git push origin main
```

### Agregar un nuevo modelo

```bash
# 1. Editar apps/mi_app/models.py

# 2. Crear migración
python manage.py makemigrations mi_app

# 3. Aplicar en local
python manage.py migrate

# 4. Commit + push
git add .
git commit -m "feat: agregar modelo X"
git push origin main
```

### Backup completo de la BD

```bash
pg_dump -U postgres -h localhost -p 5432 \
  -d cobijo_vzla_db -F c -b \
  -f "backup_$(date +%Y-%m-%d).dump"
```

Guardar el archivo en un lugar seguro (Drive, Dropbox, etc.).

### Cambiar la contraseña de Supabase

1. Supabase → **Project Settings** → **Database** → **Reset password**
2. Copiar la nueva contraseña
3. Actualizar `.env` local
4. Render → **Environment** → editar `DATABASE_URL`
5. Render redeploya automáticamente

### Reset del schema (⚠️ emergencia)

**Solo usar si la BD está corrupta**. Borra TODOS los datos:

```sql
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

Después: `python manage.py migrate` + `pg_restore --data-only`.

---

## 🆘 Troubleshooting

### `exec format error` en Render

**Causa**: `start.sh` tiene line endings CRLF (Windows).

**Solución**:

```bash
# Convertir a LF
sed -i 's/\r$//' start.sh
git add start.sh
git commit -m "fix: convertir start.sh a LF"
git push origin main
```

En Windows PowerShell:

```powershell
$content = Get-Content start.sh -Raw
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$PWD\start.sh", $content, [System.Text.UTF8Encoding]::new($false))
```

### `password authentication failed`

**Causa**: contraseña incorrecta en `.env` o en Render.

**Solución**: verificar que ambos tengan la misma URL actualizada.

### `relation "X" does not exist`

**Causa**: migraciones no aplicadas.

**Solución**:

```bash
python manage.py migrate
```

### `column "name" does not exist` en `django_content_type`

**Causa**: tabla en estado inconsistente (típico tras `pg_restore` incompleto).

**Solución**: reset del schema + migrar + recargar datos.

### `Could not find GDAL library`

**Causa**: falta `GDAL_LIBRARY_PATH` o librería no instalada.

**Solución local (Windows)**:

```env
GDAL_LIBRARY_PATH=C:\...\OSGeo4W\bin\gdal313.dll
GEOS_LIBRARY_PATH=C:\...\OSGeo4W\bin\geos_c.dll
```

**Solución producción**: revisar que el `Dockerfile` incluya `gdal-bin`.

### Render dice "Live" pero la página da 500

**Causa**: el health check `/admin/` puede pasar incluso si la BD falla.

**Solución**:

1. Ver logs de Render
2. Buscar `Traceback`
3. Corregir y redeployar

### La app tarda 30-50 segundos en cargar

**Causa**: Render Free duerme tras 15 min sin tráfico.

**Solución**: usar uptime robot o subir a plan pagado.

---

## 📌 Reglas de oro

1. **Nunca** subas `.env` a Git
2. **Nunca** pegues contraseñas en chats, issues, ni logs
3. **Siempre** verifica `git status` antes de commitear
4. **Siempre** haz backup antes de tocar la BD de producción
5. **Nunca** corras `migrate --fake` sin entender por qué
6. **Nunca** uses `DROP SCHEMA CASCADE` en producción sin backup
7. **Si dudas, prueba primero en local**
8. **Los emojis y acentos rompen scripts de shell** — usa ASCII en `.sh`, `Dockerfile`, `.yaml`
9. **Los archivos que se ejecutan en Linux deben tener LF** — usa `.gitattributes`
10. **Rota credenciales** si accidentalmente las expones

---

## 🎓 Comandos de emergencia (cheat sheet)

```bash
# === ENTORNO ===
myvenv\Scripts\activate                       # Activar venv
deactivate                                     # Desactivar

# === DIAGNÓSTICO ===
python manage.py check                         # Verificar Django
python manage.py showmigrations                # Ver migraciones
grep DATABASE_URL .env                         # Ver URL

# === GIT ===
git status                                     # Ver cambios
git add . && git commit -m "fix: X" && git push origin main

# === BD ===
python manage.py migrate                       # Aplicar migraciones
python manage.py shell                         # Consola interactiva

# === BACKUP ===
pg_dump -U postgres -h localhost -d cobijo_vzla_db -F c -f backup.dump

# === RESTORE ===
pg_restore -d "$DATABASE_URL" --no-owner --no-acl --data-only -v "backup.dump"

# === LINE ENDINGS ===
file start.sh                                  # Debe decir "ASCII text" (no "CRLF")
```

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m "feat: agregar nueva funcionalidad"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

### Convenciones de commits

| Prefijo | Uso |
|---------|-----|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de bug |
| `docs:` | Documentación |
| `chore:` | Tareas varias |
| `refactor:` | Reestructuración |
| `style:` | Formato |

---

## 📄 Licencia

Este proyecto está licenciado bajo la **MIT License**. Ver el archivo [LICENSE](LICENSE) para más detalles.

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
| Dashboard Supabase | https://supabase.com/dashboard |
| Dashboard Render | https://dashboard.render.com |

---

<p align="center">
  Hecho con ❤️ para Venezuela 🇻🇪
</p>