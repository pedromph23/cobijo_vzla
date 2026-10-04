/* CobijoVzla — comportamiento compartido de formularios CRUD. */
(function () {
    'use strict';

    const defaultCenter = window.CobijoMap ? window.CobijoMap.center : [8.5, -66.0];
    let locationMap = null;
    let locationMarker = null;
    let geocoding = false;

    const status = document.getElementById('crud-location-status');
    const setStatus = (message) => {
        if (status) status.textContent = message;
    };

    function setLocationValue(lat, lng, zoom = true, message = 'Ubicación seleccionada correctamente') {
        const input = document.querySelector('.crud-location-value input');
        if (!input || !Number.isFinite(lat) || !Number.isFinite(lng)) {
            setStatus('La ubicación encontrada no es válida.');
            return false;
        }

        // PostGIS espera la representación lng,lat en estos formularios.
        input.value = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));

        if (locationMap && typeof L !== 'undefined') {
            if (!locationMarker) {
                locationMarker = L.marker([lat, lng]).addTo(locationMap);
            } else {
                locationMarker.setLatLng([lat, lng]);
            }
            if (zoom) locationMap.setView([lat, lng], Math.max(locationMap.getZoom(), 16));
        }

        setStatus(message);
        return true;
    }

    async function geocode(button) {
        if (!button || geocoding) return;

        const inputId = button.getAttribute('data-location-input');
        const sourceInput = inputId ? document.getElementById(inputId) : null;
        const endpoint = button.getAttribute('data-geocode-url');
        const texto = sourceInput ? sourceInput.value.trim() : '';

        if (!sourceInput) {
            setStatus('No se encontró el campo que se desea ubicar.');
            console.error('CobijoVzla: data-location-input inválido:', inputId);
            return;
        }

        if (!endpoint) {
            setStatus('No está disponible el servicio de ubicación.');
            console.error('CobijoVzla: falta data-geocode-url.');
            return;
        }

        if (!texto) {
            setStatus('Escribe el nombre o dirección para ubicarlo en el mapa.');
            sourceInput.focus();
            return;
        }

        geocoding = true;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        setStatus(`Buscando «${texto}» en Venezuela…`);

        try {
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('direccion', texto);

            const response = await fetch(url.href, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                cache: 'no-store'
            });

            const contentType = response.headers.get('content-type') || '';
            const result = contentType.includes('application/json')
                ? await response.json()
                : null;

            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    setStatus('Tu sesión ya no es válida. Recarga la página e inténtalo nuevamente.');
                } else {
                    setStatus(result?.detail || `No se pudo ubicar «${texto}».`);
                }
                console.warn('CobijoVzla: error HTTP de geocodificación:', response.status, result);
                return;
            }

            if (!result?.ok || !result?.found) {
                setStatus(result?.detail || `No encontramos «${texto}» en Venezuela. Puedes seleccionar el punto en el mapa.`);
                return;
            }

            const lat = Number(result.lat);
            const lng = Number(result.lng);
            if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
                setStatus('El servicio devolvió una ubicación inválida.');
                console.error('CobijoVzla: coordenadas inválidas:', result);
                return;
            }

            const message = result.display_name
                ? `Ubicado: ${result.display_name}`
                : 'Lugar ubicado automáticamente';

            setLocationValue(lat, lng, true, message);
        } catch (error) {
            console.error('CobijoVzla: error de geocodificación:', error);
            setStatus('No se pudo consultar el servicio de ubicación. Puedes seleccionar el punto manualmente.');
        } finally {
            geocoding = false;
            button.disabled = false;
            button.removeAttribute('aria-busy');
        }
    }

    /*
     * Los botones se conectan directamente una sola vez.
     * No usamos un listener delegado para evitar que otros handlers del
     * documento interfieran con el click del botón.
     */
    document.querySelectorAll('[data-location-action="geocode"]').forEach(button => {
        button.type = 'button';
        button.disabled = false;
        button.removeAttribute('disabled');

        button.addEventListener('click', function (event) {
            event.preventDefault();
            geocode(button);
        });

        const sourceInput = button.getAttribute('data-location-input')
            ? document.getElementById(button.getAttribute('data-location-input'))
            : null;

        if (sourceInput) {
            sourceInput.addEventListener('keydown', function (event) {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                geocode(button);
            });
        }
    });

    /* Mapa de ubicación. No condiciona ni bloquea la geocodificación. */
    const mapElement = document.getElementById('crud-location-map');
    const input = document.querySelector('.crud-location-value input');

    if (input && mapElement && typeof L !== 'undefined') {
        locationMap = window.CobijoMap
            ? window.CobijoMap.create('crud-location-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
            : L.map(mapElement).setView(defaultCenter, 6);

        if (locationMap) {
            const raw = input.value || '';
            const parts = raw.replace(',', ' ').trim().split(/\s+/).map(Number);

            if (parts.length >= 2 && parts.every(Number.isFinite)) {
                const lng = parts[0];
                const lat = parts[1];
                if (Math.abs(lng) <= 180 && Math.abs(lat) <= 90) {
                    setLocationValue(lat, lng, false, 'Ubicación cargada');
                }
            }

            locationMap.on('click', event => setLocationValue(event.latlng.lat, event.latlng.lng));
        }

        const locate = document.querySelector('[data-location-action="locate"]');
        if (locate && navigator.geolocation) {
            locate.addEventListener('click', event => {
                event.preventDefault();
                setStatus('Obteniendo ubicación…');
                navigator.geolocation.getCurrentPosition(
                    position => setLocationValue(position.coords.latitude, position.coords.longitude),
                    () => setStatus('No se pudo obtener tu ubicación. Selecciona un punto en el mapa.'),
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
                );
            });
        }
    }

    /* Mapa de geometría para zonas afectadas. */
    const geometryElement = document.getElementById('crud-geometry-map');
    const geometryInput = document.querySelector('.crud-geometry-value input, .crud-geometry-field input[type="hidden"]');

    if (geometryElement && geometryInput && typeof L !== 'undefined') {
        const geometryStatus = document.getElementById('crud-geometry-status');
        const drawButton = document.querySelector('[data-geometry-action="draw"]');
        const clearButton = document.querySelector('[data-geometry-action="clear"]');
        const map = window.CobijoMap
            ? window.CobijoMap.create('crud-geometry-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
            : L.map(geometryElement).setView(defaultCenter, 6);
        let drawing = false;
        let points = [];
        let polygon = null;
        let vertices = [];

        const gstatus = message => { if (geometryStatus) geometryStatus.textContent = message; };
        const clearVisual = () => {
            if (polygon) map.removeLayer(polygon);
            polygon = null;
            vertices.forEach(marker => map.removeLayer(marker));
            vertices = [];
        };
        const wkt = coords => {
            const closed = coords.concat([coords[0]]);
            return `SRID=4326;POLYGON ((${closed.map(([lat, lng]) => `${lng.toFixed(6)} ${lat.toFixed(6)}`).join(', ')}))`;
        };
        const render = () => {
            clearVisual();
            vertices = points.map(([lat, lng]) => L.circleMarker([lat, lng], { radius: 5 }).addTo(map));
            if (points.length >= 3) {
                polygon = L.polygon(points, { weight: 3, fillOpacity: 0.2 }).addTo(map);
                geometryInput.value = wkt(points);
                geometryInput.dispatchEvent(new Event('change', { bubbles: true }));
                gstatus(`Zona definida · ${points.length} puntos`);
            } else {
                gstatus(points.length ? `${points.length} punto(s) · agrega otro para cerrar` : 'Dibuja la zona sobre el mapa');
            }
        };
        map.on('click', event => {
            if (!drawing) return;
            if (points.length >= 3 && map.distance(event.latlng, L.latLng(points[0])) < 100) {
                drawing = false;
                render();
                return;
            }
            points.push([event.latlng.lat, event.latlng.lng]);
            render();
        });
        if (drawButton) drawButton.addEventListener('click', () => {
            drawing = true;
            points = [];
            clearVisual();
            geometryInput.value = '';
            gstatus('Haz clic en el mapa para marcar los vértices y cierra sobre el primer punto.');
        });
        if (clearButton) clearButton.addEventListener('click', () => {
            drawing = false;
            points = [];
            geometryInput.value = '';
            clearVisual();
            gstatus('Zona eliminada. Puedes dibujar una nueva.');
        });
    }
})();
