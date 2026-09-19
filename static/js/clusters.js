/**
 * Inicialización de clústeres de marcadores (Leaflet.markercluster).
 *
 * Uso:
 *     const clusters = initClusters(miMapa);
 *     clusters.addLayer(marker);
 */
(function () {
    'use strict';

    /**
     * @param {L.Map} map
     * @returns {L.MarkerClusterGroup|null}
     */
    function initClusters(map) {
        if (typeof L === 'undefined' || !L.markerClusterGroup) {
            console.error('[clusters.js] Leaflet.markercluster no disponible');
            return null;
        }
        if (!map) {
            console.error('[clusters.js] Se requiere un mapa válido');
            return null;
        }

        const clusterGroup = L.markerClusterGroup({
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            spiderfyOnMaxZoom: true,
            removeOutsideVisibleBounds: true,
            animate: true,
            maxClusterRadius: function (zoom) {
                return zoom < 5 ? 80 : 60;
            },
            iconCreateFunction: function (cluster) {
                const count = cluster.getChildCount();
                let colorClass = 'marker-cluster-small';
                if (count > 20) {
                    colorClass = 'marker-cluster-large';
                } else if (count > 5) {
                    colorClass = 'marker-cluster-medium';
                }
                return L.divIcon({
                    html: `<div><span>${count}</span></div>`,
                    className: `marker-cluster ${colorClass}`,
                    iconSize: L.point(40, 40),
                });
            },
        });

        map.addLayer(clusterGroup);
        return clusterGroup;
    }

    window.initClusters = initClusters;
})();