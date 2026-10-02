/**
 * Utilidades comunes para toda la aplicación CobijoVzla.
 *
 * Este archivo se carga en `base.html` para todas las páginas.
 * NO debe contener lógica de DOM que dependa de elementos específicos.
 */

(function (window) {
    'use strict';

    // ============================================================
    // MAPA
    // ============================================================

    /**
     * Inicializa un mapa Leaflet con soporte para tema claro/oscuro.
     * @param {string} elementId - ID del div contenedor
     * @param {[number, number]} center - [lat, lng] del centro
     * @param {number} zoom - Nivel de zoom inicial
     * @returns {L.Map|null}
     */
    function initMap(elementId, center = [10.0, -66.0], zoom = 8) {
        if (typeof L === 'undefined') {
            console.error('[main.js] Leaflet no está cargado');
            return null;
        }

        const container = document.getElementById(elementId);
        if (!container) {
            console.warn(`[main.js] No existe el elemento #${elementId}`);
            return null;
        }

        // Evita inicializar dos veces el mismo contenedor.
        if (container._leaflet_id) {
            console.warn(`[main.js] El elemento #${elementId} ya contiene un mapa`);
            return null;
        }

        const map = L.map(container, {
            center: center,
            zoom: zoom,
            zoomControl: true,
            fadeAnimation: true,
            zoomAnimation: true,
        });

        const capaEstandar = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution:
                    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
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

            if (!map.hasLayer(capa)) {
                capa.addTo(map);
            }

            const otraCapa = capa === capaOscura ? capaEstandar : capaOscura;
            if (map.hasLayer(otraCapa)) {
                map.removeLayer(otraCapa);
            }
        }

        aplicarCapaBase(document.documentElement.getAttribute('data-theme'));

        // base.html emite el evento en window. Se mantiene un único listener
        // para evitar duplicar cambios de capas cuando cambia el tema.
        window.addEventListener('themeChanged', function (e) {
            aplicarCapaBase(e.detail && e.detail.theme);
        });

        map._capaEstandar = capaEstandar;
        map._capaOscura = capaOscura;
        return map;
    }

    /**
     * Agrega una capa de calor al mapa.
     * @param {L.Map} map
     * @param {Array<{lat:number,lng:number,intensidad?:number}>} data
     * @param {object} [options]
     * @returns {L.HeatLayer|null}
     */
    function addHeatLayer(map, data, options) {
        if (!map || typeof L === 'undefined' || !L.heatLayer) {
            console.error('[main.js] Leaflet.heat no está disponible');
            return null;
        }
        if (!Array.isArray(data) || data.length === 0) {
            console.warn('[main.js] Sin datos para la capa de calor');
            return null;
        }

        options = options || {};

        const config = {
            radius: options.radius !== undefined ? options.radius : 25,
            blur: options.blur !== undefined ? options.blur : 15,
            maxZoom: options.maxZoom !== undefined ? options.maxZoom : 10,
            max: options.max !== undefined ? options.max : 1.0,
            minOpacity: options.minOpacity !== undefined ? options.minOpacity : 0.1,
            gradient: options.gradient || {
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
                const intensidad =
                    d.intensidad !== undefined ? d.intensidad : d.intensity !== undefined ? d.intensity : 0.5;
                return [Number(d.lat), Number(d.lng), Number(intensidad) || 0.5];
            });

        if (puntos.length === 0) {
            console.warn('[main.js] No hay coordenadas válidas para la capa de calor');
            return null;
        }

        const heatLayer = L.heatLayer(puntos, config);
        heatLayer.addTo(map);
        return heatLayer;
    }

    /**
     * Alterna la capa de calor (si existe, la quita; si no, la agrega).
     */
    function toggleHeatLayer(map, heatLayer, data, options) {
        if (!map) return null;

        if (heatLayer) {
            map.removeLayer(heatLayer);
            return null;
        }

        return addHeatLayer(map, data, options);
    }

    // ============================================================
    // UTILIDADES
    // ============================================================

    /**
     * Formatea un número con separadores de miles venezolanos.
     */
    function formatNumber(num) {
        const n = Number(num) || 0;
        return new Intl.NumberFormat('es-VE').format(n);
    }

    /**
     * Muestra un mensaje flotante en la esquina inferior derecha.
     * @param {string} texto
     * @param {'info'|'success'|'error'|'warning'} [tipo]
     * @param {number} [duracion] - ms antes de ocultarlo (default: 5000)
     */
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
                'position: fixed',
                'bottom: 20px',
                'right: 20px',
                'z-index: 9999',
                'padding: 12px 20px',
                'border-radius: 8px',
                'box-shadow: 0 4px 12px rgba(0,0,0,0.2)',
                'font-size: 0.9rem',
                'transition: opacity 0.3s ease',
                'max-width: 400px',
                'color: white',
                'pointer-events: none',
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
        }, duracion);
    }

    /**
     * Debounce genérico: retrasa la ejecución hasta que dejen de llamar.
     */
    function debounce(fn, delay) {
        if (typeof fn !== 'function') {
            throw new TypeError('debounce requiere una función');
        }

        let timer = null;
        return function () {
            const args = arguments;
            const ctx = this;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(ctx, args);
            }, delay);
        };
    }

    // ============================================================
    // EXPORTAR AL ÁMBITO GLOBAL
    // ============================================================

    window.initMap = initMap;
    window.addHeatLayer = addHeatLayer;
    window.toggleHeatLayer = toggleHeatLayer;
    window.formatNumber = formatNumber;
    window.mostrarMensaje = mostrarMensaje;
    window.debounce = debounce;
})(window);
