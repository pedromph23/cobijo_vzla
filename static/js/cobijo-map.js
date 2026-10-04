/*
 * CobijoVzla — configuración cartográfica compartida.
 * Un único punto de entrada para mapas Leaflet; cada vista conserva sus capas.
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
        darkTiles: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attribution: '&copy; OpenStreetMap contributors'
    };

    function themeTiles(map, settings) {
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        const url = dark ? settings.darkTiles : settings.tiles;
        const attribution = dark
            ? '&copy; OpenStreetMap contributors &copy; CARTO'
            : settings.attribution;
        const existing = map._cobijoBaseLayer;
        if (existing) map.removeLayer(existing);
        const layer = L.tileLayer(url, {
            attribution,
            referrerPolicy: 'strict-origin-when-cross-origin',
            maxZoom: settings.tileMaxZoom,
            subdomains: dark ? 'abcd' : undefined
        }).addTo(map);
        map._cobijoBaseLayer = layer;
    }

    window.CobijoMap = window.CobijoMap || {};
    Object.assign(window.CobijoMap, config, {
        create(containerId, options) {
            const container = document.getElementById(containerId);
            if (!container || typeof L === 'undefined') return null;
            if (container._cobijoMap) return container._cobijoMap;
            if (container._leaflet_id) return null;

            const settings = Object.assign({}, config, options || {});
            const map = L.map(container, {
                center: settings.center,
                zoom: settings.zoom,
                zoomControl: false,
                minZoom: settings.minZoom,
                maxZoom: settings.maxZoom
            });
            L.control.zoom({ position: 'bottomright' }).addTo(map);
            themeTiles(map, settings);

            const onThemeChanged = () => themeTiles(map, settings);
            window.addEventListener('themeChanged', onThemeChanged);
            map._cobijoThemeListener = onThemeChanged;
            map._cobijoMap = map;
            map._cobijoMapContainer = container;
            return map;
        },

        adopt(map, options) {
            if (!map || typeof L === 'undefined') return map;
            const settings = Object.assign({}, config, options || {});
            map.setMinZoom(settings.minZoom);
            map.setMaxZoom(settings.maxZoom);
            themeTiles(map, settings);
            return map;
        },

        destroy(map) {
            if (!map) return false;
            if (map._cobijoThemeListener) window.removeEventListener('themeChanged', map._cobijoThemeListener);
            const container = map._cobijoMapContainer;
            map.remove();
            if (container && container._cobijoMap === map) delete container._cobijoMap;
            return true;
        }
    });
})();
