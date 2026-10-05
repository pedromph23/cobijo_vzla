/*
 * CobijoVzla — configuración cartográfica compartida.
 * Un único punto de entrada para mapas Leaflet; cada vista conserva sus capas.
 *
 * La cartografía base usa OpenStreetMap en todas las vistas para mantener
 * consistencia entre inicio, panel y formularios CRUD.
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
        attribution: '&copy; OpenStreetMap contributors'
    };

    function configureDefaultMarkerIcon() {
        if (typeof L === 'undefined' || !L.divIcon) return;
        if (L.Icon.Default.prototype._cobijoConfigured) return;

        L.Marker.prototype.options.icon = L.divIcon({
            className: 'cobijo-default-marker',
            html: '<span aria-hidden="true"><i class="fas fa-location-dot"></i></span>',
            iconSize: [34, 42],
            iconAnchor: [17, 42],
            popupAnchor: [0, -38]
        });
        L.Icon.Default.prototype._cobijoConfigured = true;
    }

    function createBaseLayer(map, settings) {
        const existing = map._cobijoBaseLayer;
        if (existing) map.removeLayer(existing);

        const layer = L.tileLayer(settings.tiles, {
            attribution: settings.attribution,
            referrerPolicy: 'strict-origin-when-cross-origin',
            maxZoom: settings.tileMaxZoom
        }).addTo(map);

        map._cobijoBaseLayer = layer;
        return layer;
    }

    function refreshSize(map) {
        if (!map) return;
        window.requestAnimationFrame(() => map.invalidateSize({ pan: false }));
        window.setTimeout(() => map.invalidateSize({ pan: false }), 150);
    }

    window.CobijoMap = window.CobijoMap || {};
    Object.assign(window.CobijoMap, config, {
        configureDefaultMarkerIcon,

        create(containerId, options) {
            const container = document.getElementById(containerId);
            if (!container || typeof L === 'undefined') return null;
            if (container._cobijoMap) return container._cobijoMap;
            if (container._leaflet_id) return null;

            configureDefaultMarkerIcon();
            const settings = Object.assign({}, config, options || {});
            const map = L.map(container, {
                center: settings.center,
                zoom: settings.zoom,
                zoomControl: false,
                minZoom: settings.minZoom,
                maxZoom: settings.maxZoom
            });

            L.control.zoom({ position: 'bottomright' }).addTo(map);
            createBaseLayer(map, settings);
            map._cobijoMap = map;
            map._cobijoMapContainer = container;
            refreshSize(map);
            return map;
        },

        adopt(map, options) {
            if (!map || typeof L === 'undefined') return map;
            configureDefaultMarkerIcon();
            const settings = Object.assign({}, config, options || {});
            map.setMinZoom(settings.minZoom);
            map.setMaxZoom(settings.maxZoom);
            createBaseLayer(map, settings);
            refreshSize(map);
            return map;
        },

        refresh(map) {
            refreshSize(map);
            return map;
        },

        destroy(map) {
            if (!map) return false;
            const container = map._cobijoMapContainer || map.getContainer?.();
            map.remove();
            if (container && container._cobijoMap === map) delete container._cobijoMap;
            return true;
        }
    });

    configureDefaultMarkerIcon();
})();
