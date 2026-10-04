/* Selector de ubicación compartido para formularios CRUD. Las coordenadas quedan ocultas. */
(function () {
    'use strict';

    const mapElement = document.getElementById('crud-location-map');
    const input = document.querySelector('.crud-location-value input');
    if (!input || !mapElement || typeof L === 'undefined') return;

    const status = document.getElementById('crud-location-status');
    const addressInput = document.getElementById('id_direccion');
    const defaultCenter = window.CobijoMap ? window.CobijoMap.center : [8.5, -66.0];
    const map = window.CobijoMap
        ? window.CobijoMap.create('crud-location-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
        : L.map(mapElement).setView(defaultCenter, 6);
    if (!map) return;

    let marker = null;
    let lastGeocodedAddress = '';
    let geocoding = false;

    const setStatus = (message) => {
        if (status) status.textContent = message;
    };

    const setValue = (lat, lng, zoom = true, message = 'Ubicación seleccionada correctamente') => {
        input.value = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (!marker) marker = L.marker([lat, lng]).addTo(map);
        else marker.setLatLng([lat, lng]);
        if (zoom) map.setView([lat, lng], Math.max(map.getZoom(), 14));
        setStatus(message);
    };

    const initial = (input.value || '').match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
    if (initial) {
        const a = Number(initial[1]);
        const b = Number(initial[2]);
        const lat = Math.abs(a) <= 90 ? a : b;
        const lng = Math.abs(a) <= 90 ? b : a;
        if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
            setValue(lat, lng, false);
            setStatus('Ubicación cargada');
        }
    }

    const geocodificarDireccion = async () => {
        if (!addressInput || geocoding) return;

        const address = addressInput.value.trim();
        if (!address || address === lastGeocodedAddress) return;

        geocoding = true;
        setStatus('Buscando la dirección en Venezuela…');

        try {
            const params = new URLSearchParams({ direccion: address });
            const response = await fetch(`/api/geocodificar/?${params.toString()}`, {
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
            });
            const result = await response.json();

            if (!response.ok || !result.ok || !result.found) {
                lastGeocodedAddress = address;
                setStatus(result.detail || 'No encontramos la dirección. Puedes colocar el punto manualmente en el mapa.');
                return;
            }

            lastGeocodedAddress = address;
            setValue(Number(result.lat), Number(result.lng), true, 'Dirección ubicada automáticamente');
        } catch (error) {
            setStatus('No se pudo ubicar la dirección automáticamente. Puedes seleccionar el punto en el mapa.');
        } finally {
            geocoding = false;
        }
    };

    if (addressInput) {
        addressInput.addEventListener('blur', geocodificarDireccion);
        addressInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                geocodificarDireccion();
            }
        });
    }

    map.on('click', (event) => setValue(event.latlng.lat, event.latlng.lng));

    const locate = document.querySelector('[data-location-action="locate"]');
    if (locate && navigator.geolocation) {
        locate.addEventListener('click', () => {
            setStatus('Obteniendo ubicación…');
            navigator.geolocation.getCurrentPosition(
                position => setValue(position.coords.latitude, position.coords.longitude),
                () => {
                    setStatus('No se pudo obtener tu ubicación. Selecciona un punto en el mapa.');
                    map.setView(defaultCenter, 8);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
            );
        });
    }
})();
