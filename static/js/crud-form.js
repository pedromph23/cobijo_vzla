/* Selector de ubicación para formularios CRUD. Las coordenadas quedan ocultas. */
(function () {
    'use strict';

    const input = document.querySelector('[data-location-input="true"]');
    const mapElement = document.getElementById('crud-location-map');
    if (!input || !mapElement || typeof L === 'undefined') return;

    const defaultCenter = window.CobijoMap ? window.CobijoMap.center : [8.5, -66.0];
    const map = window.CobijoMap
        ? window.CobijoMap.create('crud-location-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
        : L.map(mapElement).setView(defaultCenter, 6);
    if (!map) return;

    let marker = null;

    const setValue = (lat, lng) => {
        input.value = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        if (!marker) marker = L.marker([lat, lng]).addTo(map);
        else marker.setLatLng([lat, lng]);
        map.setView([lat, lng], Math.max(map.getZoom(), 14));
    };

    const initial = (input.value || '').match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
    if (initial) {
        const a = Number(initial[1]);
        const b = Number(initial[2]);
        const lat = Math.abs(a) <= 90 ? a : b;
        const lng = Math.abs(a) <= 90 ? b : a;
        if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) setValue(lat, lng);
    }

    map.on('click', (event) => setValue(event.latlng.lat, event.latlng.lng));

    const locate = document.querySelector('[data-location-action="locate"]');
    if (locate && navigator.geolocation) {
        locate.addEventListener('click', () => {
            navigator.geolocation.getCurrentPosition(
                position => setValue(position.coords.latitude, position.coords.longitude),
                () => { map.setView(defaultCenter, 8); }
            );
        });
    }
})();
