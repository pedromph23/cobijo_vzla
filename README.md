# 🏠 Cobijo VZLA

> Plataforma web geoespacial para la gestión de refugios, zonas afectadas, necesidades humanitarias, eventos y apoyo a la navegación durante situaciones de emergencia en Venezuela.

Cobijo VZLA combina Django, PostgreSQL/PostGIS, GeoDjango, APIs REST, mapas Leaflet, rutas con OSRM/Leaflet Routing Machine, optimización matemática, reportes y un panel operativo con permisos por grupo.

---

## 📋 Índice

- [1. Qué es Cobijo VZLA](#1-qué-es-cobijo-vzla)
- [2. Objetivo](#2-objetivo)
- [3. Arquitectura general](#3-arquitectura-general)
- [4. Stack tecnológico](#4-stack-tecnológico)
- [5. Funcionalidades](#5-funcionalidades)
- [6. Mapa público](#6-mapa-público)
- [7. Navegación y rutas](#7-navegación-y-rutas)
- [8. Zonas afectadas y geometrías](#8-zonas-afectadas-y-geometrías)
- [9. Panel administrativo y operativo](#9-panel-administrativo-y-operativo)
- [10. Roles y permisos](#10-roles-y-permisos)
- [11. Auditoría e historial](#11-auditoría-e-historial)
- [12. Optimización](#12-optimización)
- [13. Reportes](#13-reportes)
- [14. APIs](#14-apis)
- [15. Arquitectura de plantillas](#15-arquitectura-de-plantillas)
- [16. Catálogo completo de plantillas](#16-catálogo-completo-de-plantillas)
- [17. JavaScript relacionado con la interfaz](#17-javascript-relacionado-con-la-interfaz)
- [18. Apps Django](#18-apps-django)
- [19. Estructura del proyecto](#19-estructura-del-proyecto)
- [20. Base de datos](#20-base-de-datos)
- [21. Seguridad](#21-seguridad)
- [22. Temas visuales y accesibilidad](#22-temas-visuales-y-accesibilidad)
- [23. Instalación local](#23-instalación-local)
- [24. Variables de entorno](#24-variables-de-entorno)
- [25. Producción y despliegue](#25-producción-y-despliegue)
- [26. Mantenimiento](#26-mantenimiento)
- [27. Troubleshooting](#27-troubleshooting)
- [28. Reglas para continuar desarrollando](#28-reglas-para-continuar-desarrollando)

---

# 1. Qué es Cobijo VZLA

Cobijo VZLA es una aplicación de gestión humanitaria y geoespacial orientada a la respuesta ante emergencias en Venezuela.

La plataforma permite trabajar con información territorial real de Venezuela y con registros operativos de refugios, zonas afectadas, necesidades y eventos. El sistema separa claramente:

- **datos territoriales maestros**, como estados y parroquias;
- **datos operativos**, como refugios, zonas afectadas y puntos de demanda;
- **datos de análisis**, como heatmap e indicadores;
- **datos de optimización**, como sitios candidatos y resultados de modelos;
- **datos de navegación**, utilizados por el mapa público para calcular rutas;
- **datos de seguridad y trazabilidad**, como auditoría e historial.

La aplicación tiene dos grandes superficies:

1. **Mapa/portal público**, orientado a consulta, localización, navegación y reportes ciudadanos.
2. **Panel interno**, orientado a administración, gestión de datos, optimización, reportes y supervisión.

---

# 2. Objetivo

El objetivo es centralizar en una sola plataforma la información necesaria para responder a situaciones de emergencia:

- saber dónde están los refugios;
- conocer dónde existen zonas afectadas;
- visualizar la severidad y población afectada;
- localizar necesidades humanitarias;
- analizar territorialmente la demanda;
- estudiar dónde conviene ubicar nuevos sitios;
- generar reportes para toma de decisiones;
- permitir consulta pública de información relevante;
- ofrecer navegación hacia destinos disponibles;
- mantener trazabilidad de las operaciones administrativas.

---

# 3. Arquitectura general

```text
                         ┌─────────────────────────┐
                         │        USUARIO           │
                         │ navegador / móvil / PC   │
                         └────────────┬────────────┘
                                      │ HTTPS
                                      ▼
                    ┌─────────────────────────────────┐
                    │       RENDER / DJANGO            │
                    │ templates + views + services     │
                    │ APIs REST + autenticación         │
                    └───────────────┬─────────────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
      │ Leaflet / JS │      │ Django REST   │      │ Reportes     │
      │ mapas/rutas  │      │ APIs públicas │      │ PDF / Excel  │
      └──────┬───────┘      └───────┬───────┘      └──────────────┘
             │                       │
             └───────────────────────┼──────────────────────┐
                                     ▼                      │
                         ┌────────────────────────┐         │
                         │ PostgreSQL + PostGIS   │◄────────┘
                         │ datos + geometrías     │
                         └────────────┬───────────┘
                                      │
                                      ▼
                                  Supabase

GitHub ──► Render ──► aplicación en producción
```

## Servicios principales

| Servicio | Responsabilidad |
|---|---|
| GitHub | Código fuente, historial y colaboración |
| Render | Ejecución y despliegue de Django |
| Supabase | PostgreSQL/PostGIS utilizado por producción |
| OSRM | Motor de rutas utilizado por la navegación |
| Leaflet | Renderizado del mapa interactivo |

---

# 4. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12+ · Django 6.1 |
| API | Django REST Framework |
| Base de datos | PostgreSQL + PostGIS |
| ORM geoespacial | GeoDjango |
| Frontend | HTML5 · CSS3 · JavaScript |
| Mapas | Leaflet 1.9 |
| Clustering | Leaflet MarkerCluster |
| Heatmap | Leaflet Heat |
| Rutas | Leaflet Routing Machine + OSRM |
| Voz | Web Speech API |
| Optimización | PuLP |
| Datos | pandas · numpy |
| Geoespacial | geopy · geojson |
| PDF | ReportLab |
| Excel | openpyxl |
| Contenedores | Docker |
| Hosting | Render |
| Persistencia | Supabase/PostgreSQL |

---

# 5. Funcionalidades

## 5.1 Gestión territorial

La aplicación trabaja con la estructura territorial venezolana y permite relacionar los datos operativos con estados y parroquias.

Los datos territoriales maestros deben considerarse especialmente sensibles: **no deben sustituirse por datos ficticios ni modificarse manualmente para resolver problemas visuales**.

## 5.2 Refugios

Permite registrar y visualizar refugios existentes, su ubicación y datos operativos asociados.

En el mapa se pueden mostrar mediante marcadores y agrupación cuando existe una gran cantidad de puntos.

## 5.3 Zonas afectadas

Las zonas afectadas utilizan geometría geoespacial almacenada en PostGIS.

El modelo de zona utiliza un `PolygonField` con SRID 4326. El mapa público debe representar la geometría real mediante GeoJSON y no sustituirla por círculos artificiales.

Una zona se considera activa cuando su fecha de inicio ya comenzó y su fecha de finalización es nula o todavía no ha vencido.

La información asociada puede incluir:

- nivel de alerta;
- descripción;
- damnificados;
- heridos;
- fallecidos;
- ubicación/centroide para referencia y navegación;
- geometría para representar el área real.

## 5.4 Puntos de demanda

Representan necesidades humanitarias georreferenciadas y sirven tanto para consulta como para análisis y optimización.

## 5.5 Sitios candidatos

Representan posibles ubicaciones para infraestructura o nuevos puntos de atención y son utilizados por los modelos de optimización.

## 5.6 Eventos y reportes ciudadanos

El módulo de emergencias permite registrar eventos y reportes, mientras que el portal público proporciona una interfaz para que ciudadanos puedan enviar información.

## 5.7 Heatmap

Se calcula un índice de necesidad por territorio y puede visualizarse como mapa de calor. Existe además un mecanismo de precálculo para reducir el coste de cálculo durante la consulta.

## 5.8 Optimización

La aplicación incluye modelos de localización para ayudar a estudiar dónde ubicar nuevos recursos considerando demanda, distancias y capacidades.

## 5.9 Reportes

Los datos pueden convertirse en reportes PDF y Excel desde el panel interno.

## 5.10 Administración

Existe un panel propio separado del Django Admin para que la operación diaria no dependa directamente de la interfaz administrativa estándar de Django.

## 5.11 Auditoría

El sistema dispone de estructuras para registrar operaciones y mantener trazabilidad de cambios administrativos.

## 5.12 Temas visuales

La interfaz soporta modo claro y oscuro. Los estilos están separados en varias capas para facilitar la evolución visual sin modificar la lógica de negocio.

---

# 6. Mapa público

El mapa público es la principal interfaz de consulta de Cobijo VZLA.

Incluye, según las capas disponibles:

- refugios;
- zonas afectadas;
- puntos de demanda;
- sitios candidatos;
- heatmap;
- búsqueda;
- geolocalización;
- navegación hacia destinos;
- información contextual;
- reportes ciudadanos.

La arquitectura del mapa se basa en un motor común (`cobijo-map.js`) y módulos especializados cargados desde `base.html`. Esto es importante: **no se deben crear nuevos mapas independientes para cada funcionalidad**.

La plantilla base carga Leaflet, MarkerCluster, heatmap y el motor común del mapa. En la página pública también se cargan los módulos específicos de navegación. fileciteturn248file0

---

# 7. Navegación y rutas

La navegación pública se construye de forma modular.

## Componentes actuales

```text
cobijo-map.js
      │
      ├── mapa y capas
      │
      └── estado compartido
             │
             ▼
   módulos de navegación
             │
             ├── localización
             ├── proxy/rutas
             ├── navegación Venezuela
             ├── GeoGuard
             ├── UX de navegación
             ├── traducción
             └── voz guiada
```

La plantilla `base.html` carga estos módulos únicamente cuando la ruta corresponde al mapa público. fileciteturn248file0

## Funciones de navegación

- cálculo de ruta;
- visualización de la ruta en el mapa;
- seguimiento de ubicación mediante GPS del navegador;
- instrucciones paso a paso;
- cálculo de distancia, duración y ETA;
- navegación por voz;
- control de sonido;
- seguimiento del progreso;
- detección de llegada;
- apoyo para navegación adaptada al contexto venezolano.

### Importante sobre tráfico

El motor de rutas actual no debe documentarse como un sistema completo de tráfico en tiempo real. El recálculo por cambios de posición o desvíos puede implementarse sobre el motor existente, pero información real de congestión, accidentes o cierres requiere una fuente de tráfico compatible.

### Importante sobre límites y carriles

Los límites de velocidad y carriles solo deben mostrarse cuando el proveedor de datos los proporcione. La aplicación no debe inventar estos valores.

---

# 8. Zonas afectadas y geometrías

Esta parte requiere especial cuidado porque representa información geoespacial real.

## Flujo correcto

```text
PostGIS
  │
  │ PolygonField / SRID 4326
  ▼
API pública
  │
  │ GeoJSON
  ▼
mapa_publico.html
  │
  ▼
Leaflet GeoJSON
  │
  ▼
polígono real en el mapa
```

El mapa público debe consumir el GeoJSON de la API y dibujar la geometría almacenada.

El centroide puede utilizarse como referencia para navegación, pero **no reemplaza la geometría del polígono**.

La capa también debe tolerar que una geometría individual esté dañada sin impedir que el mapa base, refugios u otras capas continúen funcionando.

---

# 9. Panel administrativo y operativo

El sistema dispone de dos paneles principales.

## Panel de administración

`templates/admin/panel_admin.html`

Está destinado a administradores y proporciona acceso amplio a:

- mapa administrativo;
- datos;
- CRUD;
- optimización;
- carga de datos;
- reportes;
- resultados;
- operaciones administrativas.

## Panel de gestores

`templates/admin/panel_gestor.html`

Está orientado al trabajo operativo diario con permisos más limitados.

Los gestores pueden trabajar con los recursos que les sean asignados, pero no disponen de todas las capacidades administrativas.

---

# 10. Roles y permisos

## Superusuario / Staff

- acceso completo;
- Django Admin;
- panel administrativo;
- todos los modelos y operaciones permitidas por el sistema.

## Administrador

Grupo: `Administradores`

- panel administrativo;
- CRUD completo según configuración;
- optimización;
- carga de datos;
- reportes;
- gestión operativa completa.

## Gestor

Grupo: `Gestores`

Permisos operativos limitados, incluyendo según configuración:

- PuntoDemanda: ver, crear y editar;
- RefugioExistente: ver y editar;
- ZonaAfectada: ver y editar;
- Evento: ver y editar;
- Reporte: ver y editar;
- SitioCandidato: solo ver;
- ParametrosModelo: solo ver.

No debe poder borrar registros si su matriz de permisos no lo permite.

La configuración central se encuentra en `apps/mapa/permissions.py`.

---

# 11. Auditoría e historial

Cobijo VZLA incorpora mecanismos para registrar cambios administrativos y mantener trazabilidad.

Las estructuras principales incluyen:

- `RegistroAuditoria`;
- `RegistroVersion`;
- historial asociado a operaciones relevantes.

La auditoría es especialmente importante porque la plataforma trabaja con información operativa que puede afectar la toma de decisiones.

Una futura ampliación debe conservar el principio de que **cada operación importante debe poder reconstruirse sin registrar datos sensibles innecesarios**.

---

# 12. Optimización

La aplicación incluye algoritmos de localización implementados con PuLP.

Los modelos contemplan diferentes estrategias, entre ellas:

- P-mediana;
- P-centro;
- cobertura máxima;
- modelos que consideran capacidades.

El flujo conceptual es:

```text
Puntos de demanda
       │
       ├── ubicación
       ├── población/necesidad
       └── parámetros
              │
              ▼
       Modelo de optimización
              │
              ▼
       Sitios seleccionados
              │
              ▼
       Resultados
              │
              ▼
       mapa / reportes
```

Los resultados se presentan mediante la interfaz administrativa correspondiente y pueden incorporarse a los reportes.

---

# 13. Reportes

El módulo `apps/reportes` genera información exportable.

## PDF

Se utiliza ReportLab.

## Excel

Se utiliza openpyxl.

Los reportes sirven para transformar los datos operativos y resultados analíticos en documentos que pueden ser revisados o compartidos fuera de la aplicación.

Las plantillas administrativas relacionadas son:

- `templates/admin/reportes.html`;
- `templates/admin/resultados.html`.

---

# 14. APIs

La aplicación utiliza APIs internas y públicas para separar la presentación de los datos.

Entre las áreas principales están:

- APIs del mapa;
- refugios;
- zonas afectadas;
- puntos de demanda;
- eventos/reportes;
- indicadores;
- optimización;
- reportes.

## Ejemplo: zonas afectadas

```text
GET /api/publico/zonas-afectadas/
```

La respuesta debe entregar la información necesaria para que el mapa público represente la zona mediante GeoJSON.

Las APIs son parte de la arquitectura y deben mantenerse independientes de la forma visual en que una plantilla presenta la información.

---

# 15. Arquitectura de plantillas

Las plantillas Django no son páginas aisladas. Forman una jerarquía.

```text
                         base.html
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
        mapa público     paneles       autenticación
              │
              ▼
   mapa_publico_legacy.html
              │
              ▼
     mapa_publico.html
```

El objetivo de esta estructura es mantener una base común para:

- encabezado;
- navegación;
- pie de página;
- tema claro/oscuro;
- hojas de estilo;
- Leaflet;
- JavaScript global;
- módulos de navegación.

`base.html` es especialmente importante porque carga el conjunto común de CSS/JS y, para el mapa público, carga los módulos específicos de navegación. fileciteturn248file0

---

# 16. Catálogo completo de plantillas

Esta sección existe expresamente para conservar contexto antes de modificar cualquier interfaz.

## 16.1 `templates/base.html`

Es la plantilla base global.

Responsabilidades:

- estructura HTML común;
- `<head>`;
- metadatos responsive;
- favicon;
- tipografías;
- hojas CSS globales;
- encabezado;
- navegación principal;
- autenticación visual;
- selector de tema;
- contenido mediante `{% block content %}`;
- footer;
- carga de Leaflet;
- MarkerCluster;
- heatmap;
- `cobijo-map.js`;
- tema, sidebar, responsive y main JS;
- carga condicional de los módulos de navegación pública.

No debe convertirse en un contenedor de lógica de negocio.

---

## 16.2 `templates/admin/panel_admin.html`

Panel principal para administradores.

Responsabilidades:

- presentar el dashboard administrativo;
- ofrecer navegación entre módulos;
- mostrar indicadores y herramientas;
- acceder a gestión de datos;
- acceder a optimización;
- acceder a carga de datos;
- acceder a reportes/resultados;
- mostrar el mapa administrativo cuando corresponda.

Es una plantilla de composición de la interfaz administrativa, no el lugar donde deben implementarse consultas complejas a la base de datos.

---

## 16.3 `templates/admin/panel_gestor.html`

Panel operativo para usuarios del grupo `Gestores`.

Su propósito es ofrecer una interfaz simplificada y restringida por permisos para las operaciones que el gestor puede realizar.

La plantilla no debe utilizarse para saltarse las comprobaciones del backend: la seguridad real se aplica en las vistas/permisos.

---

## 16.4 `templates/admin/carga_datos.html`

Interfaz para carga/importación de información.

Se utiliza junto con las funciones de backend encargadas de validar e importar datos masivos.

Debe mantenerse separada de los formularios CRUD individuales.

---

## 16.5 `templates/admin/reportes.html`

Interfaz para seleccionar y solicitar reportes.

Su responsabilidad es presentar opciones y resultados de la generación, mientras que la creación de PDF/Excel corresponde al módulo `apps/reportes`.

---

## 16.6 `templates/admin/resultados.html`

Presenta resultados analíticos/operativos producidos por el backend.

Puede actuar como interfaz para resultados de optimización, indicadores u otras salidas calculadas.

---

## 16.7 `templates/mapa/crud/crud_list.html`

Lista genérica de registros.

Responsabilidades:

- mostrar registros paginados;
- presentar acciones permitidas;
- permitir navegación a crear/editar/eliminar cuando el permiso lo permita.

Se utiliza con las vistas CRUD genéricas de `apps/mapa/crud_views.py`.

---

## 16.8 `templates/mapa/crud/crud_form.html`

Formulario genérico para crear o editar registros.

Su objetivo es evitar duplicar una plantilla diferente para cada modelo cuando la operación puede resolverse con la infraestructura CRUD común.

La validación definitiva debe permanecer en Django/forms/modelos/backend.

---

## 16.9 `templates/mapa/crud/crud_confirm_delete.html`

Página de confirmación antes de eliminar un registro.

No constituye por sí sola una medida de seguridad: el backend debe comprobar que el usuario tiene permiso para borrar.

---

## 16.10 `templates/publico/mapa_publico.html`

Es la plantilla pública de entrada del mapa.

Actualmente extiende `mapa_publico_legacy.html`, carga `{% static %}` y contiene la integración específica necesaria para renderizar las geometrías reales de las zonas afectadas desde la API pública.

Su papel es de integración y composición. La lógica pesada del mapa debe permanecer en JavaScript especializado y en el backend.

---

## 16.11 `templates/publico/mapa_publico_legacy.html`

Es la implementación extensa del mapa público y contiene gran parte de la estructura original del mapa y su lógica asociada.

Entre sus responsabilidades se encuentran:

- contenedor del mapa;
- controles;
- capas;
- HUD de navegación;
- selección de destinos;
- rutas;
- seguimiento GPS;
- instrucciones;
- voz;
- búsqueda;
- refugios;
- zonas;
- interacción con tarjetas informativas;
- comportamiento de navegación.

### Regla importante

No debe modificarse de forma agresiva para solucionar un problema puntual. Cambios grandes en esta plantilla pueden eliminar accidentalmente funcionalidades completas del mapa.

Cuando sea posible, una nueva función debe integrarse mediante bloques, módulos JS o pequeñas modificaciones localizadas.

---

## 16.12 `templates/publico/reporte_ciudadano.html`

Formulario/interfaz pública para que un ciudadano pueda enviar un reporte.

Debe priorizar:

- facilidad de uso;
- responsive;
- mensajes claros;
- validación del formulario;
- protección CSRF;
- carga segura de archivos si existe evidencia fotográfica;
- confirmación del envío.

La persistencia y validación real pertenecen al backend.

---

## 16.13 `templates/registration/login.html`

Pantalla de inicio de sesión.

Es la puerta de entrada a las funciones autenticadas y debe permanecer coherente con el sistema visual general.

---

## 16.14 Plantillas de recuperación y cambio de contraseña

Django utiliza varias plantillas bajo `templates/registration/` para completar el flujo de autenticación:

- `password_change_form.html` — formulario de cambio de contraseña.
- `password_change_done.html` — confirmación del cambio.
- `password_reset_form.html` — solicitud de recuperación.
- `password_reset_done.html` — confirmación del envío.
- `password_reset_confirm.html` — establecimiento de la nueva contraseña.
- `password_reset_complete.html` — confirmación final.
- `password_reset_email.html` — contenido del correo de recuperación.
- `password_reset_subject.txt` — asunto del correo de recuperación.

Estas plantillas forman un conjunto y no deben considerarse páginas independientes sin relación.

---

# 17. JavaScript relacionado con la interfaz

La interfaz utiliza una arquitectura modular.

## Núcleo visual

- `cobijo-map.js` — motor común del mapa y capas.
- `main.js` — comportamiento general.
- `theme.js` — cambio entre modo claro y oscuro.
- `sidebar.js` — comportamiento del menú lateral.
- `responsive.js` — comportamiento responsive.

## Navegación

- `navegacion_localizacion_ve.js` — localización.
- `navegacion_proxy_ve.js` — integración auxiliar/proxy de rutas.
- `navegacion_venezuela.js` — lógica específica de navegación.
- `navegacion_geoguard_ve.js` — controles/protecciones asociados a la navegación.
- `navegacion_ux_ve.js` — experiencia visual/interactiva de navegación.
- `navegacion_traduccion_ve.js` — traducción/adaptación de instrucciones.
- `navegacion_voz_guiada.js` — instrucciones de voz.

Estos módulos son cargados específicamente en el mapa público desde `base.html`. fileciteturn248file0

### Regla de integración

No deben existir varios motores que compitan por:

- GPS;
- ruta;
- `Routing.control`;
- estado de navegación;
- voz.

Si una nueva funcionalidad necesita estos datos, debe consumir el estado/motor existente.

---

# 18. Apps Django

## `apps/core`

Núcleo de datos y seguridad transversal.

Incluye modelos territoriales y operativos, autenticación, auditoría, historial y comandos de gestión.

Entre los conceptos principales están:

- Estado;
- Parroquia;
- RefugioExistente;
- ZonaAfectada;
- PuntoDemanda;
- SitioCandidato;
- Parámetros de modelo;
- RegistroAuditoria;
- RegistroVersion.

## `apps/emergencias`

Gestiona eventos y reportes asociados a emergencias.

## `apps/mapa`

Gestiona:

- panel administrativo;
- panel de gestores;
- CRUD;
- permisos;
- servicios de mapa;
- APIs relacionadas con mapas.

Archivos especialmente importantes:

- `permissions.py`;
- `decorators.py`;
- `crud_views.py`;
- `urls_crud.py`;
- `services.py`;
- `views.py`;
- `urls_api.py`.

## `apps/optimizacion`

Contiene los modelos matemáticos y el cálculo del heatmap.

## `apps/publico`

Gestiona:

- mapa público;
- búsquedas;
- servicios públicos;
- reporte ciudadano;
- APIs públicas.

## `apps/reportes`

Genera PDF y Excel.

---

# 19. Estructura del proyecto

```text
cobijo_vzla/
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── render.yaml
├── requirements.txt
├── manage.py
├── README.md
│
├── cobijo_vzla/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── core/
│   ├── emergencias/
│   ├── mapa/
│   ├── optimizacion/
│   ├── publico/
│   └── reportes/
│
├── templates/
│   ├── base.html
│   ├── admin/
│   ├── mapa/crud/
│   ├── publico/
│   └── registration/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── img/
│   └── vendor/
│
└── media/
```

---

# 20. Base de datos

La base de datos de producción utiliza PostgreSQL con PostGIS.

## Principios

1. Las geometrías deben conservar SRID coherente.
2. Las relaciones territoriales deben mantenerse consistentes.
3. Los datos maestros no deben modificarse para solucionar problemas de frontend.
4. Los cambios de esquema deben hacerse mediante migraciones Django.
5. Las consultas geoespaciales deben aprovechar PostGIS.
6. No se deben introducir datos ficticios en estructuras territoriales reales.

## Geometrías

Las geometrías son parte de los datos, no solamente una decoración del mapa.

Un error visual debe investigarse siguiendo este flujo:

```text
Base de datos
   ↓
consulta / servicio
   ↓
API
   ↓
respuesta JSON / GeoJSON
   ↓
JavaScript
   ↓
Leaflet
```

Esto evita corregir un problema de datos modificando únicamente el frontend.

---

# 21. Seguridad

La aplicación contempla varias capas de seguridad:

- autenticación Django;
- grupos y permisos;
- protección CSRF;
- validación backend;
- protección contra XSS;
- protección contra path traversal;
- control de acceso en vistas;
- separación entre panel público y panel autenticado;
- variables secretas fuera del repositorio.

### Regla fundamental

Ocultar un botón en HTML **no equivale a proteger una operación**. La autorización debe existir en el backend.

---

# 22. Temas visuales y accesibilidad

La interfaz tiene modo claro y modo oscuro.

`base.html` carga varias capas de estilos para separar responsabilidades:

```text
main.css
map.css
clusters.css
popups.css
sidebar.css
responsive.css
ui-refactor.css
ui-palette.css
ui-semantic-bridge.css
ui-accessibility.css
ui-dark-overrides.css
```

El objetivo es que los cambios visuales puedan hacerse sin alterar la lógica de negocio.

## Regla para modo oscuro

Un componente no debe considerarse terminado simplemente porque se ve bien en modo claro.

Debe comprobarse:

- texto principal;
- texto secundario;
- placeholders;
- tablas;
- badges;
- botones;
- tarjetas;
- mapas y controles;
- formularios;
- estados de error/éxito/advertencia;
- elementos deshabilitados.

Especialmente en paneles administrativos, la legibilidad debe tener prioridad sobre efectos visuales.

---

# 23. Instalación local

## Requisitos

- Python 3.12+
- PostgreSQL con PostGIS
- GDAL/GEOS para GeoDjango
- Git
- Node.js si se requieren dependencias frontend

## Instalación

```bash
git clone https://github.com/pedromph23/cobijo_vzla.git
cd cobijo_vzla

python -m venv myvenv

# Windows
myvenv\Scripts\activate

# Linux/macOS
source myvenv/bin/activate

pip install -r requirements.txt

# si corresponde
npm install

# crear .env a partir del ejemplo
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser

# opcional
python manage.py precalcular_heatmap

python manage.py runserver
```

---

# 24. Variables de entorno

Ejemplo conceptual:

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432

DATABASE_URL=

GDAL_LIBRARY_PATH=
GEOS_LIBRARY_PATH=
```

Nunca introducir secretos reales en el README ni en Git.

---

# 25. Producción y despliegue

El flujo actual es:

```text
Desarrollo
   │
   ▼
Git commit
   │
   ▼
GitHub
   │
   ▼
Render Auto-Deploy
   │
   ▼
Django + Gunicorn / contenedor
   │
   ▼
Supabase PostgreSQL + PostGIS
```

Después de cambios frontend importantes se recomienda limpiar caché con:

```text
Ctrl + F5
```

porque varios archivos JS/CSS utilizan versionado de cache-busting.

---

# 26. Mantenimiento

Antes de modificar código existente:

1. identificar la plantilla;
2. identificar la vista que la renderiza;
3. identificar el JavaScript que controla la interfaz;
4. identificar el endpoint utilizado;
5. comprobar el modelo involucrado;
6. revisar si existe otra pantalla que comparte el mismo componente;
7. hacer un cambio pequeño;
8. probar la funcionalidad original;
9. probar modo claro y oscuro;
10. probar escritorio y móvil.

## Para mapas

No cambiar simultáneamente:

- motor de mapa;
- endpoint;
- geometrías;
- estilos;
- navegación;
- GPS.

Si todo cambia a la vez, es difícil determinar dónde apareció una regresión.

---

# 27. Troubleshooting

## El mapa queda en blanco

Revisar primero:

1. consola JavaScript;
2. inicialización de Leaflet;
3. `mapaPrincipal`;
4. errores en capas individuales;
5. errores en el template;
6. errores de CSS que oculten el contenedor.

Una capa defectuosa no debe impedir que el mapa base aparezca.

## Las zonas afectadas aparecen en 0

Seguir:

```text
Base de datos
↓
servicio público
↓
/api/publico/zonas-afectadas/
↓
respuesta JSON
↓
GeoJSON
↓
Leaflet
```

No modificar coordenadas manualmente antes de comprobar cada etapa.

## Aparece error 500 después de cambiar una plantilla

Revisar primero:

- etiquetas Django;
- `{% load static %}`;
- bloques heredados;
- nombres de URL;
- variables de contexto;
- sintaxis HTML/Django.

Un error de plantilla puede ocurrir antes de que cualquier JavaScript sea ejecutado.

## El GPS muestra timeout

El GPS del navegador depende del dispositivo, permisos, señal y disponibilidad de ubicación. No debe ocultarse el error sin investigar.

La navegación ya dispone de un `watchPosition()` propio. No se deben crear mecanismos paralelos que compitan por la ubicación.

## El modo oscuro pierde contraste

Revisar primero las capas:

- `ui-palette.css`;
- `ui-semantic-bridge.css`;
- `ui-accessibility.css`;
- `ui-dark-overrides.css`.

No solucionar un problema global introduciendo estilos inline en una sola plantilla si el componente es compartido.

---

# 28. Reglas para continuar desarrollando

Estas reglas son parte de la documentación viva del proyecto.

### 1. No romper lo que funciona

Toda nueva funcionalidad debe integrarse sobre la arquitectura existente siempre que sea posible.

### 2. No duplicar motores

No crear un segundo mapa, segundo GPS, segundo `Routing.control` o segundo sistema de voz cuando ya existe uno.

### 3. No modificar datos reales para resolver problemas visuales

Primero comprobar backend → API → frontend.

### 4. Las geometrías reales son prioritarias

Una zona con `PolygonField` debe representarse como polígono/GeoJSON real.

### 5. El frontend no sustituye al backend

La interfaz puede ocultar acciones, pero la autorización real siempre debe estar en Django.

### 6. No inventar datos

Si no existen carriles, límites de velocidad o tráfico en tiempo real, la interfaz debe indicarlo o no mostrar el dato.

### 7. Probar ambos temas

Cada cambio visual debe verificarse en modo claro y oscuro.

### 8. Probar móvil

El mapa y los paneles deben seguir siendo utilizables en pantallas pequeñas.

### 9. Mantener las plantillas con responsabilidades claras

Las plantillas presentan y componen. La lógica compleja debe vivir en JavaScript modular, servicios o vistas según corresponda.

### 10. Preferir cambios pequeños

Una corrección localizada es más segura que reemplazar una plantilla completa que ya contiene múltiples funcionalidades.

---

# 🧭 Estado funcional resumido

```text
                         COBIJO VZLA
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   MAPA PÚBLICO          PANEL INTERNO        AUTENTICACIÓN
        │                     │                     │
        ├─ Refugios           ├─ Admin             ├─ Login
        ├─ Zonas              ├─ Gestor            ├─ Logout
        ├─ Demanda            ├─ CRUD              ├─ Cambio clave
        ├─ Heatmap            ├─ Carga             └─ Recuperación
        ├─ Búsqueda           ├─ Optimización
        ├─ Geolocalización    ├─ Reportes
        ├─ Rutas              └─ Resultados
        ├─ Voz
        └─ Reporte ciudadano
                              │
                              ▼
                     PostgreSQL + PostGIS
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Datos reales      Geometrías       Auditoría
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                         Toma de decisiones
```

---

## 📌 Nota para futuras modificaciones

Este README debe considerarse **documentación técnica viva**. Cuando se agregue una funcionalidad importante, debe actualizarse la sección correspondiente y, si afecta la interfaz, el catálogo de plantillas y módulos JavaScript.

El objetivo no es solamente explicar cómo instalar Cobijo VZLA, sino conservar el contexto necesario para que futuras modificaciones entiendan **cómo está conectado todo el sistema y dónde debe hacerse cada cambio sin romper funcionalidades existentes**.

---

## 📄 Licencia

MIT — consultar `LICENSE`.
