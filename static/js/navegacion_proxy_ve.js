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

    function solicitarRuta(origen, destino) {
        const parametros = new URLSearchParams({
            origen_lat: Number(origen.lat).toFixed(6),
            origen_lng: Number(origen.lng).toFixed(6),
            destino_lat: Number(destino.lat).toFixed(6),
            destino_lng: Number(destino.lng).toFixed(6),
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
                    // El mensaje genérico de abajo evita dejar la navegación
                    // esperando si el servidor devuelve HTML o una respuesta vacía.
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
        const coordenadas = (datos.coordinates || []).map(([lat, lng]) => L.latLng(lat, lng));
        const puntos = Array.isArray(waypoints) ? waypoints : [];

        return {
            name: 'Ruta CobijoVzla',
            summary: datos.summary || { totalDistance: 0, totalTime: 0 },
            coordinates: coordenadas,
            instructions: (datos.instructions || []).map(paso => ({
                text: paso.text || 'Continúe por la ruta indicada',
                distance: Number(paso.distance) || 0,
                time: Number(paso.time) || 0,
                index: Number.isFinite(Number(paso.index)) ? Number(paso.index) : 0,
                type: paso.type || 'continue',
                modifier: paso.modifier || '',
                road: paso.road || '',
            })),
            inputWaypoints: puntos,
            waypoints: puntos,
        };
    }

    function instalarRouterProxy() {
        if (!window.L?.Routing?.osrmv1) return;

        const routerProxy = function() {
            return {
                route(waypoints, callback, context) {
                    const puntos = Array.isArray(waypoints) ? waypoints : [];
                    const origen = puntos[0]?.latLng;
                    const destino = puntos[puntos.length - 1]?.latLng;
                    const responder = typeof callback === 'function' ? callback : () => {};
                    const contexto = context || this;

                    if (!origen || !destino) {
                        responder.call(contexto, {
                            status: -1,
                            message: 'No se recibieron puntos válidos para calcular la ruta.',
                        });
                        return;
                    }

                    solicitarRuta(origen, destino)
                        .then(datos => prepararRuta(datos, puntos))
                        .then(ruta => responder.call(contexto, null, [ruta]))
                        .catch(error => responder.call(contexto, {
                            status: -1,
                            message: error?.message || 'No fue posible calcular la ruta.',
                        }));
                },
            };
        };

        routerProxy.__cobijoProxy = true;
        window.L.Routing.osrmv1 = routerProxy;
    }

    // No sobrescribimos window.calcularRuta. La función histórica conserva
    // toda la lógica de HUD, voz, GPS, llegada y controles de navegación.
    // Solo sustituimos el transporte de routing por el proxy Django.
    instalarRouterProxy();
})();
