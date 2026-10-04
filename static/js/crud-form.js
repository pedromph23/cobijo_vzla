/* Selector de ubicación para formularios CRUD. Las coordenadas quedan ocultas. */
(function () {
    'use strict';

    const mapElement = document.getElementById('crud-location-map');
    const input = document.querySelector('.crud-location-value input');
    if (!input || !mapElement || typeof L === 'undefined') return;

    const status = document.getElementById('crud-location-status');
    const defaultCenter = window.CobijoMap ? window.CobijoMap.center : [8.5, -66.0];
    const map = window.CobijoMap
        ? window.CobijoMap.create('crud-location-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
        : L.map(mapElement).setView(defaultCenter, 6);
    if (!map) return;

    let marker = null;

    const setValue = (lat, lng, zoom = true) => {
        input.value = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (!marker) marker = L.marker([lat, lng]).addTo(map);
        else marker.setLatLng([lat, lng]);
        if (zoom) map.setView([lat, lng], Math.max(map.getZoom(), 14));
        if (status) status.textContent = `Ubicación seleccionada: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    };

    const initial = (input.value || '').match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
    if (initial) {
        const a = Number(initial[1]);
        const b = Number(initial[2]);
        const lat = Math.abs(a) <= 90 ? a : b;
        const lng = Math.abs(a) <= 90 ? b : a;
        if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) setValue(lat, lng, false);
    }

    map.on('click', (event) => setValue(event.latlng.lat, event.latlng.lng));

    const locate = document.querySelector('[data-location-action="locate"]');
    if (locate && navigator.geolocation) {
        locate.addEventListener('click', () => {
            navigator.geolocation.getCurrentPosition(
                position => setValue(position.coords.latitude, position.coords.longitude),
                () => {
                    if (status) status.textContent = 'No se pudo obtener tu ubicación. Selecciona un punto en el mapa.';
                    map.setView(defaultCenter, 8);
                }
            );
        });
    }
})();
