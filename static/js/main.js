/**
 * Utilidades comunes para toda la aplicación CobijoVzla.
 *
 * Este archivo se carga desde `base.html` y no debe asumir que existen
 * elementos de una página concreta.
 */
(function (window) {
    'use strict';

    const DEFAULT_CENTER = [10.0, -66.0];
    const DEFAULT_ZOOM = 8;

    function initMap(elementId, center = DEFAULT_CENTER, zoom = DEFAULT_ZOOM) {
        if (typeof L === 'undefined') {
            console.error('[main.js] Leaflet no está cargado');
            return null;
        }

        const container = document.getElementById(elementId);
        if (!container) {
            console.warn(`[main.js] No existe el elemento #${elementId}`);
            return null;
        }

        // Si este módulo ya inicializó el contenedor, reutilizamos el mapa.
        // Evita instancias Leaflet duplicadas al volver a ejecutar una vista.
        if (container._cobijoMap) {
            return container._cobijoMap;
        }

        // Si otro módulo inicializó el mapa, no intentamos tomar control de él.
        if (container._leaflet_id) {
            console.warn(`[main.js] El elemento #${elementId} ya contiene un mapa ajeno a main.js`);
            return null;
        }

        const map = L.map(container, {
            center,
            zoom,
            zoomControl: true,
            fadeAnimation: true,
            zoomAnimation: true,
        });

        const capaEstandar = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                referrerPolicy: 'strict-origin-when-cross-origin',
                maxZoom: 19,
            }
        );

        const capaOscura = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                referrerPolicy: 'strict-origin-when-cross-origin',
                maxZoom: 19,
                subdomains: 'abcd',
            }
        );

        function aplicarCapaBase(tema) {
            const capa = tema === 'dark' ? capaOscura : capaEstandar;
            const otraCapa = tema === 'dark' ? capaEstandar : capaOscura;

            if (!map.hasLayer(capa)) capa.addTo(map);
            if (map.hasLayer(otraCapa)) map.removeLayer(otraCapa);
        }

        aplicarCapaBase(document.documentElement.getAttribute('data-theme') || 'light');

        const onThemeChanged = function (event) {
            const tema = event && event.detail ? event.detail.theme : 'light';
            aplicarCapaBase(tema);
        };
        window.addEventListener('themeChanged', onThemeChanged);

        // Referencias privadas para permitir destrucción limpia del mapa.
        map._capaEstandar = capaEstandar;
        map._capaOscura = capaOscura;
        map._cobijoThemeListener = onThemeChanged;
        map._cobijoMapContainer = container;
        container._cobijoMap = map;

        return map;
    }

    /**
     * Destruye un mapa creado por initMap y libera su listener de tema.
     * No intenta destruir mapas creados por otros módulos.
     */
    function destroyMap(map) {
        if (!map || !map._cobijoMapContainer) return false;

        const container = map._cobijoMapContainer;

        if (map._cobijoThemeListener) {
            window.removeEventListener('themeChanged', map._cobijoThemeListener);
        }

        if (typeof map.remove === 'function') {
            map.remove();
        }

        if (container._cobijoMap === map) {
            delete container._cobijoMap;
        }

        return true;
    }

    function addHeatLayer(map, data, options) {
        if (!map || typeof L === 'undefined' || !L.heatLayer) {
            console.error('[main.js] Leaflet.heat no está disponible');
            return null;
        }
        if (!Array.isArray(data) || data.length === 0) {
            console.warn('[main.js] Sin datos para la capa de calor');
            return null;
        }

        const opts = options || {};
        const config = {
            radius: opts.radius !== undefined ? opts.radius : 25,
            blur: opts.blur !== undefined ? opts.blur : 15,
            maxZoom: opts.maxZoom !== undefined ? opts.maxZoom : 10,
            max: opts.max !== undefined ? opts.max : 1.0,
            minOpacity: opts.minOpacity !== undefined ? opts.minOpacity : 0.1,
            gradient: opts.gradient || {
                0.2: '#00ff00',
                0.4: '#ffff00',
                0.6: '#ff9900',
                0.8: '#ff3300',
                1.0: '#cc0000',
            },
        };

        const puntos = data
            .filter(function (d) {
                return d && Number.isFinite(Number(d.lat)) && Number.isFinite(Number(d.lng));
            })
            .map(function (d) {
                const intensidad = d.intensidad !== undefined
                    ? d.intensidad
                    : d.intensity !== undefined
                        ? d.intensity
                        : 0.5;

                return [Number(d.lat), Number(d.lng), Number(intensidad) || 0.5];
            });

        if (!puntos.length) {
            console.warn('[main.js] No hay coordenadas válidas para la capa de calor');
            return null;
        }

        const heatLayer = L.heatLayer(puntos, config);
        heatLayer.addTo(map);
        return heatLayer;
    }

    function toggleHeatLayer(map, heatLayer, data, options) {
        if (!map) return null;

        if (heatLayer) {
            map.removeLayer(heatLayer);
            return null;
        }

        return addHeatLayer(map, data, options);
    }

    function formatNumber(num) {
        const n = Number(num) || 0;
        return new Intl.NumberFormat('es-VE').format(n);
    }

    function mostrarMensaje(texto, tipo, duracion) {
        tipo = tipo || 'info';
        duracion = duracion === undefined ? 5000 : duracion;

        let contenedor = document.getElementById('mensaje-flotante');
        if (!contenedor) {
            contenedor = document.createElement('div');
            contenedor.id = 'mensaje-flotante';
            contenedor.setAttribute('role', 'status');
            contenedor.setAttribute('aria-live', 'polite');
            contenedor.style.cssText = [
                'position:fixed',
                'bottom:20px',
                'right:20px',
                'z-index:9999',
                'padding:12px 20px',
                'border-radius:8px',
                'box-shadow:0 4px 12px rgba(0,0,0,.2)',
                'font-size:.9rem',
                'transition:opacity .3s ease',
                'max-width:400px',
                'color:#fff',
                'pointer-events:none',
            ].join(';');
            document.body.appendChild(contenedor);
        }

        const colores = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#0066cc',
        };

        contenedor.style.backgroundColor = colores[tipo] || colores.info;
        contenedor.textContent = texto == null ? '' : String(texto);
        contenedor.style.opacity = '1';

        clearTimeout(contenedor._timeout);
        contenedor._timeout = setTimeout(function () {
            contenedor.style.opacity = '0';
        }, Math.max(0, Number(duracion) || 0));
    }

    function debounce(fn, delay) {
        if (typeof fn !== 'function') {
            throw new TypeError('debounce requiere una función');
        }

        let timer = null;
        const wait = Math.max(0, Number(delay) || 0);

        function debounced() {
            const args = arguments;
            const ctx = this;
            clearTimeout(timer);
            timer = setTimeout(function () {
                timer = null;
                fn.apply(ctx, args);
            }, wait);
        }

        debounced.cancel = function () {
            clearTimeout(timer);
            timer = null;
        };

        return debounced;
    }

    window.initMap = initMap;
    window.destroyMap = destroyMap;
    window.addHeatLayer = addHeatLayer;
    window.toggleHeatLayer = toggleHeatLayer;
    window.formatNumber = formatNumber;
    window.mostrarMensaje = mostrarMensaje;
    window.debounce = debounce;
})(window);
