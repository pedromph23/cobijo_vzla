/*
 * CobijoVzla — configuración cartográfica compartida.
 * El mapa base es único; cada vista conserva sus propias capas y lógica.
 */
(function () {
    'use strict';

    const config = {
        center: [8.5, -66.0],
        zoom: 6,
        minZoom: 5,
        maxZoom: 18,
        tileMaxZoom: 19,
        tiles: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    };

    window.CobijoMap = window.CobijoMap || {};
    Object.assign(window.CobijoMap, config, {
        create(containerId, options) {
            const container = document.getElementById(containerId);
            if (!container || typeof L === 'undefined') return null;
            const settings = Object.assign({}, config, options || {});
            const map = L.map(container, {
                center: settings.center,
                zoom: settings.zoom,
                zoomControl: false,
                minZoom: settings.minZoom,
                maxZoom: settings.maxZoom
            });
            L.control.zoom({ position: 'bottomright' }).addTo(map);
            L.tileLayer(settings.tiles, {
                attribution: settings.attribution,
                referrerPolicy: 'strict-origin-when-cross-origin',
                maxZoom: settings.tileMaxZoom
            }).addTo(map);
            return map;
        },

        normalize(map) {
            if (!map || typeof L === 'undefined') return map;
            map.setMinZoom(config.minZoom);
            map.setMaxZoom(config.maxZoom);
            map.options.zoomControl = false;
            if (!map.zoomControl) L.control.zoom({ position: 'bottomright' }).addTo(map);
            return map;
        }
    });
})();
