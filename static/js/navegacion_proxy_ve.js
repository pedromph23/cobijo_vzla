/**
 * Proxy de routing para CobijoVzla.
 *
 * Mantiene el flujo de navegación existente de mapa_publico.html y de los
 * módulos UX/GPS/voz. La única responsabilidad de este archivo es impedir
 * que Leaflet Routing Machine consulte directamente un motor externo.
 *
 * El router histórico L.Routing.osrmv1() queda adaptado a /api/publico/ruta/.
 */
(() => {
    'use strict';

    const TIMEOUT_MS = 16000;
    const PROXY_FLAG = '__cobijoProxy';

    function solicitarRuta(origen, destino) {
        const origenLat = Number(origen?.lat);
        const origenLng = Number(origen?.lng);
        const destinoLat = Number(destino?.lat);
        const destinoLng = Number(destino?.lng);

        if (![origenLat, origenLng, destinoLat, destinoLng].every(Number.isFinite)) {
            return Promise.reject(new Error('Las coordenadas de la ruta no son válidas.'));
        }

        const parametros = new URLSearchParams({
            origen_lat: origenLat.toFixed(6),
            origen_lng: origenLng.toFixed(6),
            destino_lat: destinoLat.toFixed(6),
            destino_lng: destinoLng.toFixed(6),
        });

        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);

        return fetch(`/api/publico/ruta/?${parametros.toString()}`, {
            method: 'GET',
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
            cache: 'no-store',
            signal: controller.signal,
        })
            .then(async respuesta => {
                let datos = null;
                try {
                    datos = await respuesta.json();
                } catch (_) {
                    // Evita que una respuesta no JSON deje el control de LRM
                    // esperando indefinidamente.
                }
                if (!respuesta.ok || !datos?.ok || !datos?.ruta) {
                    throw new Error(datos?.error || 'El servidor de rutas no respondió correctamente.');
                }
                return datos.ruta;
            })
            .catch(error => {
                if (error?.name === 'AbortError') {
                    throw new Error('El cálculo de la ruta tardó demasiado. Inténtalo nuevamente.');
                }
                throw error;
            })
            .finally(() => window.clearTimeout(timer));
    }

    function prepararRuta(datos, waypoints) {
        const coordenadas = (datos.coordinates || [])
            .filter(punto => Array.isArray(punto) && punto.length >= 2)
            .map(([lat, lng]) => L.latLng(Number(lat), Number(lng)))
            .filter(punto => Number.isFinite(punto.lat) && Number.isFinite(punto.lng));
        const puntos = Array.isArray(waypoints) ? waypoints : [];

        if (coordenadas.length < 2) {
            throw new Error('El servidor devolvió una ruta sin suficientes coordenadas.');
        }

        return {
            name: 'Ruta CobijoVzla',
            summary: datos.summary || { totalDistance: 0, totalTime: 0 },
            coordinates: coordenadas,
            instructions: (datos.instructions || []).map((paso, indice) => ({
                text: paso.text || 'Continúe por la ruta indicada',
                distance: Number(paso.distance) || 0,
                time: Number(paso.time) || 0,
                index: Number.isFinite(Number(paso.index)) ? Number(paso.index) : indice,
                type: paso.type || 'continue',
                modifier: paso.modifier || '',
                road: paso.road || '',
            })),
            inputWaypoints: puntos,
            waypoints: puntos,
        };
    }

    function crearRouterProxy() {
        return {
            route(waypoints, callback, context) {
                const puntos = Array.isArray(waypoints) ? waypoints : [];
                const origen = puntos[0]?.latLng;
                const destino = puntos[puntos.length - 1]?.latLng;
                const responder = typeof callback === 'function' ? callback : () => {};
                const contexto = context || this;
                let respondido = false;

                const responderUnaVez = (error, rutas) => {
                    if (respondido) return;
                    respondido = true;
                    responder.call(contexto, error || null, rutas || null);
                };

                if (!origen || !destino) {
                    responderUnaVez({
                        status: -1,
                        message: 'No se recibieron puntos válidos para calcular la ruta.',
                    });
                    return;
                }

                solicitarRuta(origen, destino)
                    .then(datos => prepararRuta(datos, puntos))
                    .then(ruta => responderUnaVez(null, [ruta]))
                    .catch(error => responderUnaVez({
                        status: -1,
                        message: error?.message || 'No fue posible calcular la ruta.',
                    }));
            },
        };
    }

    function instalarRouterProxy() {
        if (!window.L?.Routing?.osrmv1) return;
        if (window.L.Routing.osrmv1[PROXY_FLAG]) return;

        const routerProxy = function() {
            return crearRouterProxy();
        };
        routerProxy[PROXY_FLAG] = true;
        window.L.Routing.osrmv1 = routerProxy;

        // API interna única para que cualquier módulo nuevo pueda solicitar
        // una ruta sin volver a crear otro cliente de OSRM.
        window.CobijoRouting = Object.freeze({
            solicitarRuta,
            crearRouter: crearRouterProxy,
        });
    }

    instalarRouterProxy();
})();
