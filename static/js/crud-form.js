/* Selector de ubicación compartido para formularios CRUD. */
(function () {
    'use strict';

    const mapElement = document.getElementById('crud-location-map');
    const input = document.querySelector('.crud-location-value input');
    if (!input || !mapElement || typeof L === 'undefined') return;

    const status = document.getElementById('crud-location-status');
    const addressInput = document.getElementById('id_direccion');
    const geocodeButton = document.querySelector('[data-location-action="geocode"]');
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
        if (!address) {
            setStatus('Escribe una dirección para ubicarla en el mapa.');
            return;
        }
        if (address === lastGeocodedAddress) {
            setStatus('La dirección ya fue ubicada en el mapa.');
            return;
        }

        geocoding = true;
        if (geocodeButton) geocodeButton.disabled = true;
        setStatus('Buscando la dirección en Venezuela…');

        try {
            const params = new URLSearchParams({ direccion: address });
            const response = await fetch(`/api/geocodificar/?${params.toString()}`, {
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
            });
            const result = await response.json();

            if (!response.ok || !result.ok || !result.found) {
                lastGeocodedAddress = '';
                setStatus(result.detail || 'No encontramos la dirección. Puedes colocar el punto manualmente.');
                return;
            }

            lastGeocodedAddress = address;
            setValue(Number(result.lat), Number(result.lng), true, 'Dirección ubicada automáticamente');
        } catch (error) {
            lastGeocodedAddress = '';
            setStatus('No se pudo ubicar la dirección. Puedes seleccionar el punto manualmente.');
        } finally {
            geocoding = false;
            if (geocodeButton) geocodeButton.disabled = !addressInput.value.trim();
        }
    };

    if (addressInput) {
        const syncAddressButton = () => {
            if (geocodeButton) geocodeButton.disabled = !addressInput.value.trim() || geocoding;
            if (addressInput.value.trim() !== lastGeocodedAddress) {
                if (lastGeocodedAddress) setStatus('La dirección cambió. Pulsa «Ubicar dirección» para actualizar el punto.');
            }
        };
        addressInput.addEventListener('input', syncAddressButton);
        addressInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                geocodificarDireccion();
            }
        });
        if (geocodeButton) geocodeButton.addEventListener('click', geocodificarDireccion);
        syncAddressButton();
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