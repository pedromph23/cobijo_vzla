# CobijoVzla

Aplicación web para localizar refugios temporales y centros de acopio en Venezuela durante emergencias.

## Requisitos

- Python 3.10+ (recomendado 3.12)
- PostgreSQL con PostGIS
- Dependencias listadas en requirements.txt

## Instalación

1. Clonar el repositorio.
2. Crear entorno virtual: `python -m venv myvenv` y activarlo.
3. Instalar dependencias: `pip install -r requirements.txt`
4. Crear base de datos: `createdb cobijo_vzla_db` y habilitar PostGIS: `psql -d cobijo_vzla_db -c "CREATE EXTENSION postgis;"`
5. Configurar variables de entorno (copiar .env.example a .env y ajustar).
6. Ejecutar migraciones: `python manage.py makemigrations` y `python manage.py migrate`
7. Crear superusuario: `python manage.py createsuperuser`
8. Crear grupo "Gestores" en el admin y asignar usuarios.
9. (Opcional) Cargar datos de prueba: `python manage.py cargar_datos_prueba`
10. Iniciar servidor: `python manage.py runserver`

pip install requests

## Uso

- Mapa público: http://localhost:8000/
- Panel administrativo: http://localhost:8000/panel/
- Admin Django: http://localhost:8000/admin/

## Comandos de gestión

- `python manage.py cargar_datos_prueba` – Carga datos ficticios.
- `python manage.py importar_limites archivo.geojson` – Importa límites administrativos.

python manage.py importar_limites parroquias.geojson

## Configuracion para Windows

# Entorno de Desarrollo para Cobijo Vzla (GeoDjango en Windows vía WSL)

Este documento detalla la configuración exacta necesaria para ejecutar este proyecto en un entorno de desarrollo con Windows. 

Dado que el proyecto utiliza **GeoDjango**, requiere bibliotecas espaciales en C++ (como GDAL y GEOS). La instalación nativa de estas librerías en Windows suele generar errores de dependencias (`.dll` faltantes). Para solucionar esto de manera definitiva y profesional, el backend se ejecuta en **Linux (Debian)** utilizando **WSL (Windows Subsystem for Linux)**, mientras que el código fuente y la base de datos PostgreSQL se mantienen en Windows.

---

## 🐧 Fase 1: Instalación y Preparación de Linux (WSL)

### 1.1 Instalar Debian en WSL
Abrir PowerShell como Administrador en Windows y ejecutar:
```powershell
wsl --install -d Debian

(Al finalizar, pedirá reiniciar el equipo. Luego, se abrirá la terminal de Debian para crear un usuario y contraseña).

(Al finalizar, pedirá reiniciar el equipo. Luego, se abrirá la terminal de Debian para crear un usuario y contraseña).

1.2 Navegar a la carpeta del proyecto
WSL monta automáticamente el disco C:\ de Windows en la ruta /mnt/c/. Para acceder al proyecto desde la terminal de Linux:

cd /mnt/c/Users/Pedro/Desktop/cobijo_vzla

Fase 2: Instalación de Dependencias del Sistema
Dentro de la terminal de Debian, es necesario instalar el motor espacial (GDAL), las herramientas de desarrollo de Python y las cabeceras de PostgreSQL (libpq-dev) necesarias para compilar psycopg2.

sudo apt update
sudo apt install gdal-bin libgdal-dev python3-gdal python3-venv python3-dev libpq-dev

Fase 3: Configurar PostgreSQL en Windows para aceptar conexiones de WSL
Por defecto, PostgreSQL en Windows solo acepta conexiones locales (localhost). Como WSL funciona como una máquina virtual con su propia subred, Windows bloquea la conexión arrojando un error de Connection timed out.

3.1 Editar postgresql.conf
Buscar el archivo de configuración en Windows (generalmente en C:\Program Files\PostgreSQL\16\data\postgresql.conf).
Abrir con el Bloc de notas, buscar la línea listen_addresses, quitar el símbolo # y cambiarla a:

listen_addresses = '*'

3.2 Editar pg_hba.conf
En la misma carpeta, abrir pg_hba.conf y agregar la siguiente regla al final del documento para dar acceso a la subred de Linux:

host    all             all             0.0.0.0/0               scram-sha-256

3.3 Abrir el puerto en el Firewall de Windows
Abrir el Símbolo del sistema (CMD) como Administrador en Windows y ejecutar:

netsh advfirewall firewall add rule name="PostgreSQL WSL" dir=in action=allow protocol=TCP localport=5432

3.4 Reiniciar el servicio de PostgreSQL
En Windows, presionar Win + R, escribir services.msc, buscar el servicio postgresql-x64, hacer clic derecho y seleccionar Reiniciar.

🐍 Fase 4: Creación del Entorno Virtual (El "Truco" de WSL)
Importante: No se debe crear el entorno virtual (.venv o myvenv) dentro de la carpeta del proyecto montada en /mnt/c/.... El sistema de archivos de Windows (NTFS) bloquea la creación de enlaces simbólicos y permisos de Unix, provocando errores como Operation not permitted al intentar instalar pip.

Para solucionarlo, el entorno virtual se aloja en el sistema de archivos nativo de Linux (la carpeta home o ~), pero se ejecuta sobre el código fuente en Windows.

4.1 Crear y activar el entorno en Linux
En la terminal de Debian:

# 1. Crear el entorno en la carpeta personal de Linux
python3 -m venv ~/myvenv_cobijo

# 2. Activar el entorno
source ~/myvenv_cobijo/bin/activate

🚀 Fase 5: Ejecución del Proyecto
5.1 Instalar requerimientos
Con el entorno virtual activado ((myvenv_cobijo) visible en la terminal) y estando en la ruta del proyecto (/mnt/c/Users/Pedro/Desktop/cobijo_vzla), instalar las librerías:

pip install -r requirements.txt

5.2 Configurar la Base de Datos en settings.py
En caso de que la conexión a localhost no funcione por el enrutamiento de WSL, se debe averiguar la IP interna con la que WSL ve a Windows (ej. 172.31.128.1) y configurarla en settings.py:

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'tu_base_de_datos',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_password',
        'HOST': '172.31.128.1', # O 'localhost' si hay soporte nativo activo
        'PORT': '5432',
    }
}

ALLOWED_HOSTS = ['*'] # Necesario para evitar el error "DisallowedHost"

5.3 Aplicar Migraciones y Arrancar el Servidor
Bash

python manage.py makemigrations
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

(El comando 0.0.0.0:8000 le indica a Linux que exponga el servidor en todas sus interfaces de red).

🌐 Fase 6: Acceso a la Aplicación
Para ver la aplicación corriendo, abrir cualquier navegador web en Windows (Chrome, Firefox, Edge) e ingresar a:

👉 http://localhost:8000

Documentación generada para mantener el entorno de desarrollo estable, escalable y libre de conflictos de dependencias espaciales.

Pasos para crear el superusuario

Abre tu terminal y asegúrate de tener tu entorno virtual activo. 

[1] Escribe el comando principal:

python manage.py createsuperuser

Introduce la información solicitada por la consola:

Username: Escribe el nombre de usuario (sin espacios ni mayúsculas preferiblemente).

Email address: Ingresa tu dirección de correo electrónico.

Password: Escribe tu contraseña. 

Al escribirla no se verá nada en pantalla por seguridad; es un comportamiento normal.

Password (again): Vuelve a escribir la contraseña para confirmar. 

Si la contraseña es muy corta o común, Django te pedirá confirmar si deseas aceptarla de todos modos escribiendo y (yes).

Apagar terminal Linux WSL

Abre PowerShell o Símbolo del sistema (CMD) en Windows (no importa si no es como administrador).

Ejecuta este comando para apagar por completo todas las instancias de WSL:

wsl --shutdown

Vuelve a abrir tu terminal de Debian.

2. Verificar que la red ya funcione
Una vez dentro de tu terminal de Linux nuevamente, prueba si ya hay internet ejecutando:

ping -c 3 8.8.8.8

Si ves respuestas con los tiempos de "ms", significa que la red ya está conectada.

3. Volver a ejecutar el comando
Con la red restablecida, activa tu entorno virtual y corre tu importación de OpenStreetMap otra vez:

source ~/myvenv_cobijo/bin/activate
cd /mnt/c/Users/Pedro/Desktop/cobijo_vzla

Descargar los datos locales (Método manual o web) desde la pagina web https://overpass-turbo.eu/
Entra a la página oficial Overpass Turbo desde el navegador web de tu PC con Windows (allí sí tienes internet directo).

En el cuadro de código de la izquierda, pega esta consulta para Caracas o cualquier Estado/Parroquia:

 ## Se remplaza Caracas por el Estado o Parroquia que se quiera buscar

[out:json][timeout:25];
// Corrección aplicada: se usan corchetes para buscar el área por nombre
area["name"="Caracas"]->.searchArea;
(
  node["amenity"="hospital"](area.searchArea);
  way["amenity"="hospital"](area.searchArea);
  node["amenity"="school"](area.searchArea);
  way["amenity"="school"](area.searchArea);
  node["leisure"="park"](area.searchArea);
  way["leisure"="park"](area.searchArea);
);
out body;
>;
out skel qt;


Pasos rápidos para obtener tu archivo:

Pega este código corregido en el panel izquierdo de Overpass Turbo.

Dale al botón Ejecutar (Run) arriba a la izquierda.

Cuando carguen los puntos, haz clic en Exportar -> GeoJSON para descargarlo.

Guárdalo en tu proyecto (por ejemplo, en data/caracas_osm.geojson) y procésalo con tu comando local.

Para Importar los datos descargados lo hacemos por medio del comando y archivo que se descargo con el nombre que se le asigno:

python manage.py importar_osm caracas_osm.geojson

Consulta de Overpass QL para Zonas de Emergencia / Daños:
Pega el siguiente código en Overpass Turbo:

[out:json][timeout:25];
area["name"="Caracas"]->.searchArea;
(
  // Buscar elementos relacionados con emergencias
  node["emergency"](area.searchArea);
  way["emergency"](area.searchArea);
  
  // Buscar edificaciones colapsadas o con daños reportados
  node["building"="collapsed"](area.searchArea);
  way["building"="collapsed"](area.searchArea);
  node["damage"](area.searchArea);
  way["damage"](area.searchArea);
  
  // Puntos de reunión o ensamblaje ante emergencias
  node["emergency"="assembly_point"](area.searchArea);
  way["emergency"="assembly_point"](area.searchArea);
);
out body;
>;
out skel qt;

para sustraer los datos descargados:

 python manage.py importar_zonas_local zonas_afectadas_la_guaira_osm.geojson