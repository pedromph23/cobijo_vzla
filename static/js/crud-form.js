/* Selector de ubicación y geometría compartido para formularios CRUD. */
(function () {
    'use strict';

    const mapElement = document.getElementById('crud-location-map');
    const geometryElement = document.getElementById('crud-geometry-map');
    const input = document.querySelector('.crud-location-value input');
    const geometryInput = document.querySelector('.crud-geometry-value input, .crud-geometry-field input[type="hidden"]');
    const geocodeButtons = document.querySelectorAll('[data-location-action="geocode"]');
    const defaultCenter = window.CobijoMap ? window.CobijoMap.center : [8.5, -66.0];

    /*
     * GEOCODIFICACIÓN
     *
     * Este bloque no depende de que Leaflet haya podido crear el mapa.
     * Antes estaba dentro de la inicialización del mapa y un fallo de esta
     * última impedía registrar el click/Enter del botón de geocodificación.
     * El formulario puede geocodificar primero y representar el resultado
     * en el mapa después.
     */
    let locationMap = null;
    let locationMarker = null;
    let lastGeocodedAddress = '';
    let geocoding = false;

    const status = document.getElementById('crud-location-status');
    const setStatus = (message) => {
        if (status) status.textContent = message;
    };

    const setLocationValue = (lat, lng, zoom = true, message = 'Ubicación seleccionada correctamente') => {
        if (!input) return false;
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            setStatus('La ubicación encontrada no es válida.');
            return false;
        }

        input.value = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));

        if (locationMap && typeof L !== 'undefined') {
            if (!locationMarker) locationMarker = L.marker([lat, lng]).addTo(locationMap);
            else locationMarker.setLatLng([lat, lng]);
            if (zoom) locationMap.setView([lat, lng], Math.max(locationMap.getZoom(), 16));
        }

        setStatus(message);
        return true;
    };

    const geocodificar = async (sourceInput, button) => {
        if (!sourceInput || geocoding) return;

        const texto = sourceInput.value.trim();
        if (!texto) {
            setStatus('Escribe el nombre o dirección para ubicarlo en el mapa.');
            sourceInput.focus();
            return;
        }

        const endpoint = button?.dataset.geocodeUrl;
        if (!endpoint) {
            setStatus('No está disponible el servicio de ubicación.');
            console.error('CobijoVzla: falta data-geocode-url en el botón de ubicación.');
            return;
        }

        geocoding = true;
        geocodeButtons.forEach(item => {
            item.setAttribute('aria-busy', 'true');
            item.classList.add('is-loading');
        });
        setStatus(`Buscando «${texto}» en Venezuela…`);

        try {
            const params = new URLSearchParams({ direccion: texto });
            const response = await fetch(`${endpoint}?${params.toString()}`, {
                method: 'GET',
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
                cache: 'no-store',
            });

            let result = null;
            try {
                result = await response.json();
            } catch (_) {
                result = null;
            }

            if (!response.ok || !result?.ok || !result?.found) {
                const detail = result?.detail || `No encontramos «${texto}». Puedes seleccionar el punto manualmente.`;
                setStatus(detail);
                console.warn('CobijoVzla: geocodificación sin resultado', response.status, result);
                return;
            }

            const lat = Number(result.lat);
            const lng = Number(result.lng);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                setStatus('El servicio devolvió una ubicación inválida.');
                return;
            }

            lastGeocodedAddress = texto;
            setLocationValue(
                lat,
                lng,
                true,
                result.display_name ? `Ubicado: ${result.display_name}` : 'Lugar ubicado automáticamente'
            );
        } catch (error) {
            console.error('Error al geocodificar ubicación:', error);
            setStatus('No se pudo consultar el servicio de ubicación. Puedes seleccionar el punto manualmente.');
        } finally {
            geocoding = false;
            geocodeButtons.forEach(item => {
                item.removeAttribute('aria-busy');
                item.classList.remove('is-loading');
            });
        }
    };

    /* Los botones quedan operativos aunque el mapa tenga algún problema. */
    geocodeButtons.forEach(button => {
        const sourceInput = document.getElementById(button.dataset.locationInput);
        if (!sourceInput) {
            console.error('CobijoVzla: no se encontró el campo', button.dataset.locationInput);
            return;
        }

        button.disabled = false;
        button.removeAttribute('disabled');

        sourceInput.addEventListener('input', () => {
            const texto = sourceInput.value.trim();
            if (texto && texto !== lastGeocodedAddress) {
                setStatus('Pulsa «Ubicar en el mapa» para localizar este lugar.');
            }
        });

        sourceInput.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter') return;
            event.preventDefault();
            event.stopPropagation();
            geocodificar(sourceInput, button);
        });

        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            geocodificar(sourceInput, button);
        });
    });

    /* MAPA DE UBICACIÓN: independiente de la geocodificación. */
    if (input && mapElement && typeof L !== 'undefined') {
        locationMap = window.CobijoMap
            ? window.CobijoMap.create('crud-location-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
            : L.map(mapElement).setView(defaultCenter, 6);

        if (locationMap) {
            const initial = (input.value || '').match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
            if (initial) {
                const a = Number(initial[1]);
                const b = Number(initial[2]);
                const lat = Math.abs(a) <= 90 ? a : b;
                const lng = Math.abs(a) <= 90 ? b : a;
                if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
                    setLocationValue(lat, lng, false, 'Ubicación cargada');
                }
            }

            locationMap.on('click', event => {
                setLocationValue(event.latlng.lat, event.latlng.lng);
            });

            const locate = document.querySelector('[data-location-action="locate"]');
            if (locate && navigator.geolocation) {
                locate.addEventListener('click', () => {
                    setStatus('Obteniendo ubicación…');
                    navigator.geolocation.getCurrentPosition(
                        position => setLocationValue(position.coords.latitude, position.coords.longitude),
                        () => {
                            setStatus('No se pudo obtener tu ubicación. Selecciona un punto en el mapa.');
                            locationMap.setView(defaultCenter, 8);
                        },
                        { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
                    );
                });
            }
        }
    }

    /* MAPA DE GEOMETRÍA PARA ZONAS AFECTADAS. */
    if (geometryElement && geometryInput && typeof L !== 'undefined') {
        const geometryStatus = document.getElementById('crud-geometry-status');
        const drawButton = document.querySelector('[data-geometry-action="draw"]');
        const clearButton = document.querySelector('[data-geometry-action="clear"]');
        const map = window.CobijoMap
            ? window.CobijoMap.create('crud-geometry-map', { zoom: 6, minZoom: 5, maxZoom: 19 })
            : L.map(geometryElement).setView(defaultCenter, 6);
        if (!map) return;

        let drawing = false;
        let points = [];
        let polygon = null;
        let vertices = [];

        const setGeometryStatus = (message) => {
            if (geometryStatus) geometryStatus.textContent = message;
        };

        const clearVisual = () => {
            if (polygon) {
                map.removeLayer(polygon);
                polygon = null;
            }
            vertices.forEach(marker => map.removeLayer(marker));
            vertices = [];
        };

        const toWkt = (coords) => {
            const closed = coords.concat([coords[0]]);
            return `SRID=4326;POLYGON ((${closed.map(([lat, lng]) => `${lng.toFixed(6)} ${lat.toFixed(6)}`).join(', ')}))`;
        };

        const render = () => {
            clearVisual();
            if (points.length) vertices = points.map(([lat, lng]) => L.circleMarker([lat, lng], { radius: 5 }).addTo(map));
            if (points.length >= 3) {
                polygon = L.polygon(points, { weight: 3, fillOpacity: 0.2 }).addTo(map);
                geometryInput.value = toWkt(points);
                geometryInput.dispatchEvent(new Event('change', { bubbles: true }));
                setGeometryStatus(`Zona definida · ${points.length} puntos`);
            } else if (points.length) {
                geometryInput.value = '';
                setGeometryStatus(`${points.length} punto(s) · agrega al menos uno más para cerrar la zona`);
            } else {
                geometryInput.value = '';
                setGeometryStatus('Dibuja la zona sobre el mapa');
            }
        };

        const loadExisting = () => {
            const value = geometryInput.value || '';
            const match = value.match(/POLYGON\s*\(\((.+)\)\)/i);
            if (!match) return;
            const parsed = match[1].split(',').map(pair => pair.trim().split(/\s+/).map(Number));
            const coords = parsed.slice(0, -1).filter(pair => pair.length >= 2 && pair.every(Number.isFinite));
            if (coords.length < 3) return;
            points = coords.map(([lng, lat]) => [lat, lng]);
            render();
            map.fitBounds(points, { padding: [30, 30] });
            setGeometryStatus('Zona cargada · puedes limpiarla y dibujarla de nuevo');
        };

        const stopDrawing = () => {
            drawing = false;
            if (drawButton) drawButton.classList.remove('active');
            setGeometryStatus(points.length >= 3 ? 'Zona definida' : 'Dibuja la zona sobre el mapa');
        };

        const startDrawing = () => {
            drawing = true;
            points = [];
            clearVisual();
            geometryInput.value = '';
            if (drawButton) drawButton.classList.add('active');
            setGeometryStatus('Haz clic en el mapa para marcar los vértices. Pulsa sobre el primer punto para cerrar.');
        };

        map.on('click', event => {
            if (!drawing) return;
            const point = [event.latlng.lat, event.latlng.lng];
            if (points.length >= 3 && map.distance(event.latlng, L.latLng(points[0])) < 100) {
                render();
                stopDrawing();
                return;
            }
            points.push(point);
            render();
        });

        if (drawButton) drawButton.addEventListener('click', startDrawing);
        if (clearButton) clearButton.addEventListener('click', () => {
            drawing = false;
            points = [];
            geometryInput.value = '';
            clearVisual();
            setGeometryStatus('Zona eliminada. Puedes dibujar una nueva.');
        });

        loadExisting();
    }
})();
