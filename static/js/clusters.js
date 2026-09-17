function initClusters(map) {
    const clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        removeOutsideVisibleBounds: true,
        animate: true,
        maxClusterRadius: function(zoom) {
            return zoom < 5 ? 80 : 60;
        },
        iconCreateFunction: function(cluster) {
            const count = cluster.getChildCount();
            let size = 'small';
            let colorClass = 'marker-cluster-small';
            
            if (count > 20) {
                size = 'large';
                colorClass = 'marker-cluster-large';
            } else if (count > 5) {
                size = 'medium';
                colorClass = 'marker-cluster-medium';
            }
            
            return L.divIcon({
                html: `<div><span>${count}</span></div>`,
                className: `marker-cluster ${colorClass}`,
                iconSize: L.point(40, 40)
            });
        }
    });
    
    map.addLayer(clusterGroup);
    return clusterGroup;
}