/**
 * Puente de compatibilidad para la navegación pública de Cobijo VZLA.
 *
 * La vista histórica crea un L.Routing.control desde la función calcularRuta
 * declarada en el template. La capa nueva de navegación expone su versión
 * mediante window.calcularRuta, pero una declaración function del template
 * conserva su binding léxico. Este puente detecta el control histórico y
 * deriva la navegación al flujo mejorado sin modificar refugios ni API.
 */
(() => {
    'use strict';

    let controlProcesado = null;
    let puenteOcupado = false;

    function revisarControl() {
        if (puenteOcupado) return;
        if (typeof window.calcularRuta !== 'function') return;
        if (typeof rutaControl === 'undefined' || !rutaControl) return;
        if (rutaControl === controlProcesado) return;

        const control = rutaControl;
        const opciones = control.options || {};

        // La navegación mejorada utiliza show:false. No interceptarla.
        if (opciones.show === false) {
            controlProcesado = control;
            return;
        }

        if (typeof control.getWaypoints !== 'function') return;

        const waypoints = control.getWaypoints();
        const destino = waypoints?.[waypoints.length - 1];
        const latLng = destino?.latLng;
        if (!latLng || !Number.isFinite(latLng.lat) || !Number.isFinite(latLng.lng)) return;

        controlProcesado = control;

        // Esperamos a que el control histórico tenga su ruta inicializada.
        // Así obtenemos el destino real seleccionado por el usuario.
        setTimeout(() => {
            if (puenteOcupado) return;
            if (typeof rutaControl === 'undefined' || rutaControl !== control) return;

            puenteOcupado = true;
            try {
                mapaPrincipal?.removeControl(control);
            } catch (_) {}

            const nombre = destino.name || destino.options?.name || 'Refugio';
            window.calcularRuta(latLng.lat, latLng.lng, nombre);

            setTimeout(() => {
                puenteOcupado = false;
            }, 1500);
        }, 0);
    }

    function instalar() {
        // El control histórico se crea después del clic del usuario.
        // Un intervalo corto permite capturarlo sin modificar la lógica existente.
        window.setInterval(revisarControl, 150);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();

/**
 * Capa de resiliencia del motor de rutas.
 *
 * El proyecto histórico apuntaba al demo público de router.project-osrm.org.
 * Para una aplicación pública no conviene depender de un único endpoint:
 * el servicio demo no ofrece garantías de latencia/uptime y aplica límites
 * de uso. Esta capa mantiene OSRM/LRM, pero usa el servidor FOSSGIS como
 * primera opción, desactiva hints y limita cada intento para evitar que la
 * interfaz quede congelada indefinidamente.
 *
 * Fallback:
 *   1. FOSSGIS routed-car (mundial, incluye Venezuela)
 *   2. OSRM demo mundial
 *
 * No cambia refugios, APIs ni la lógica de navegación; solo hace más robusta
 * la comunicación entre Leaflet Routing Machine y OSRM.
 */
(() => {
    'use strict';

    const CONFIG = Object.freeze({
        primaryServiceUrl: 'https://routing.openstreetmap.de/routed-car/route/v1',
        fallbackServiceUrl: 'https://router.project-osrm.org/route/v1',
        primaryTimeout: 12000,
        fallbackTimeout: 9000,
        retryCooldownMs: 5000,
    });

    let factoryOriginal = null;
    let instalado = false;
    let ultimaFallaPrimaria = 0;

    function crearOpciones(opciones, serviceUrl, timeout) {
        const originales = opciones || {};
        return {
            ...originales,
            serviceUrl,
            timeout,
            useHints: false,
        };
    }

    function errorNormalizado(error, mensaje) {
        if (error && typeof error === 'object') {
            return {
                ...error,
                status: Number.isFinite(Number(error.status)) ? Number(error.status) : -1,
                message: error.message || mensaje,
            };
        }
        return { status: -1, message: mensaje };
    }

    function ejecutarConFallback(router, waypoints, callback, context, routingOptions, opcionesOriginales) {
        let terminado = false;
        let intentoSecundario = false;
        let timer = null;

        const finalizar = (error, rutas) => {
            if (terminado) return;
            terminado = true;
            if (timer) window.clearTimeout(timer);
            callback.call(context || callback, error, rutas);
        };

        const iniciarFallback = (errorPrimario) => {
            if (terminado || intentoSecundario) return;
            intentoSecundario = true;
            ultimaFallaPrimaria = Date.now();

            let fallbackRouter;
            try {
                fallbackRouter = factoryOriginal.call(
                    L.Routing,
                    crearOpciones(opcionesOriginales, CONFIG.fallbackServiceUrl, CONFIG.fallbackTimeout)
                );
            } catch (error) {
                finalizar(errorNormalizado(error, 'No fue posible iniciar el motor alternativo de rutas.'), null);
                return;
            }

            try {
                fallbackRouter.route(
                    waypoints,
                    (error, rutas) => {
                        if (!error && rutas?.length) {
                            finalizar(null, rutas);
                            return;
                        }
                        finalizar(
                            errorNormalizado(
                                error || errorPrimario,
                                'El servicio de rutas no respondió correctamente.'
                            ),
                            null
                        );
                    },
                    context,
                    routingOptions
                );
            } catch (error) {
                finalizar(errorNormalizado(error, 'El motor alternativo de rutas no está disponible.'), null);
            }
        };

        timer = window.setTimeout(() => {
            iniciarFallback({
                status: -1,
                message: 'El servicio principal de rutas tardó demasiado en responder.',
            });
        }, CONFIG.primaryTimeout + 1000);

        try {
            router.__cobijoOriginalRoute(
                waypoints,
                (error, rutas) => {
                    if (!error && rutas?.length) {
                        finalizar(null, rutas);
                        return;
                    }
                    iniciarFallback(error);
                },
                context,
                routingOptions
            );
        } catch (error) {
            iniciarFallback(error);
        }
    }

    function envolverRouter(router, opcionesOriginales) {
        if (!router || router.__cobijoRouterResiliente) return router;

        const routeOriginal = router.route?.bind(router);
        if (typeof routeOriginal !== 'function') return router;

        router.__cobijoRouterResiliente = true;
        router.__cobijoOriginalRoute = routeOriginal;
        router.route = function routeResiliente(waypoints, callback, context, routingOptions) {
            return ejecutarConFallback(
                router,
                waypoints,
                callback,
                context,
                routingOptions,
                opcionesOriginales
            );
        };

        return router;
    }

    function instalarResiliencia() {
        if (instalado) return true;
        if (!window.L?.Routing?.osrmv1) return false;

        factoryOriginal = window.L.Routing.osrmv1;
        if (factoryOriginal.__cobijoResiliente) {
            instalado = true;
            return true;
        }

        const factoryResiliente = function osrmv1Resiliente(opciones = {}) {
            const ahora = Date.now();
            const usaFallbackTemporal = ahora - ultimaFallaPrimaria < CONFIG.retryCooldownMs;
            const serviceUrl = usaFallbackTemporal
                ? CONFIG.fallbackServiceUrl
                : CONFIG.primaryServiceUrl;
            const timeout = usaFallbackTemporal
                ? CONFIG.fallbackTimeout
                : CONFIG.primaryTimeout;

            const opcionesFinales = crearOpciones(opciones, serviceUrl, timeout);
            const router = factoryOriginal.call(this, opcionesFinales);
            return envolverRouter(router, opciones);
        };

        factoryResiliente.__cobijoResiliente = true;
        factoryResiliente.__factoryOriginal = factoryOriginal;
        window.L.Routing.osrmv1 = factoryResiliente;
        instalado = true;
        return true;
    }

    function iniciar() {
        if (instalarResiliencia()) return;
        window.setTimeout(instalarResiliencia, 0);
        window.setTimeout(instalarResiliencia, 250);
        window.setTimeout(instalarResiliencia, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar, { once: true });
    } else {
        iniciar();
    }
})();
