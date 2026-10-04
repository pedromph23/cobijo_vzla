/*
 * CobijoVzla — configuración compartida del mapa.
 * Mantiene una única configuración cartográfica para las vistas pública y administrativa.
 * Las funciones específicas de cada pantalla permanecen en sus respectivos módulos.
 */
(function () {
    'use strict';

    window.CobijoMap = window.CobijoMap || {
        center: [8.5, -66.0],
        zoom: 6,
        minZoom: 5,
        maxZoom: 18,
        tileMaxZoom: 19,
        tiles: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',

        create(containerId, options) {
            const config = Object.assign({}, this, options || {});
            const container = document.getElementById(containerId);
            if (!container || typeof L === 'undefined') return null;

            const map = L.map(container, {
                center: config.center,
                zoom: config.zoom,
                zoomControl: false,
                minZoom: config.minZoom,
                maxZoom: config.maxZoom
            });

            L.control.zoom({ position: 'bottomright' }).addTo(map);
            L.tileLayer(config.tiles, {
                attribution: config.attribution,
                referrerPolicy: 'strict-origin-when-cross-origin',
                maxZoom: config.tileMaxZoom
            }).addTo(map);

            return map;
        },

        applyTheme(theme) {
            const container = document.querySelector('.leaflet-container');
            if (!container) return;
            container.classList.toggle('mapa-tema-oscuro', theme === 'dark');
        }
    };
})();
