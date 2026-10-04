/**
 * Motor de rutas de producción para CobijoVzla.
 *
 * El cliente consulta /api/publico/ruta/ (mismo origen) y recibe una ruta
 * compatible con Leaflet Routing Machine. Así el navegador no depende de
 * CORS ni de una conexión directa a router.project-osrm.org.
 */
(() => {
    'use strict';

    // El backend puede probar dos motores (hasta 7 s cada uno). El cliente
    // debe dar tiempo suficiente para que el fallback termine antes de
    // declarar la solicitud como agotada.
    const TIMEOUT_MS = 16000;
    let calculando = false;

    function escapar(valor) {
        return String(valor ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function mostrarEstado(titulo, mensaje) {
        const card = document.getElementById('info-card');
        const title = document.getElementById('info-card-title');
        const body = document.getElementById('info-card-body');
        if (!card || !title || !body) return;
        title.textContent = titulo;
        body.innerHTML = `<div style="padding:8px 0;display:flex;gap:10px;align-items:center;"><i class="fas fa-spinner fa-spin"></i><span>${escapar(mensaje)}</span></div>`;
        card.style.display = 'block';
    }

    function mostrarError(mensaje) {
        const card = document.getElementById('info-card');
        const title = document.getElementById('info-card-title');
        const body = document.getElementById('info-card-body');
        if (!card || !title || !body) return;
        title.textContent = 'No se pudo calcular la ruta';
        body.innerHTML = `<p style="margin:0 0 12px;">${escapar(mensaje)}</p><button type="button" class="btn-como-llegar" id="btn-reintentar-ruta-ve"><i class="fas fa-rotate-right"></i> Reintentar</button>`;
        body.querySelector('#btn-reintentar-ruta-ve')?.addEventListener('click', () => card.style.display = 'none');
        card.style.display = 'block';
    }

    function obtenerPosicion() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Tu navegador no admite geolocalización.'));
                return;
            }
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 30000,
            });
        });
    }

    function obtenerErrorGeolocalizacion(error) {
        if (error?.code === 1) return 'Permiso de ubicación denegado. Actívalo para calcular la ruta.';
        if (error?.code === 2) return 'No fue posible determinar tu ubicación.';
        if (error?.code === 3) return 'La ubicación tardó demasiado en responder.';
        return error?.message || 'No fue posible obtener tu ubicación.';
    }

    async function solicitarRuta(origen, destino) {
        const parametros = new URLSearchParams({
            origen_lat: origen.lat.toFixed(6),
            origen_lng: origen.lng.toFixed(6),
            destino_lat: destino.lat.toFixed(6),
            destino_lng: destino.lng.toFixed(6),
        });
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const respuesta = await fetch(`/api/publico/ruta/?${parametros.toString()}`, {
                method: 'GET',
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
                cache: 'no-store',
                signal: controller.signal,
            });
            let datos = null;
            try { datos = await respuesta.json(); } catch (_) {}
            if (!respuesta.ok || !datos?.ok || !datos?.ruta) {
                throw new Error(datos?.error || 'El servidor de rutas no respondió correctamente.');
            }
            return datos.ruta;
        } catch (error) {
            if (error?.name === 'AbortError') throw new Error('El cálculo de la ruta tardó demasiado. Inténtalo nuevamente.');
            throw error;
        } finally {
            window.clearTimeout(timer);
        }
    }

    function prepararRuta(datos) {
        const coordenadas = (datos.coordinates || []).map(([lat, lng]) => L.latLng(lat, lng));
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
        };
    }

    function crearControlRuta(ruta, origen, destino, nombre) {
        if (typeof rutaControl !== 'undefined' && rutaControl) {
            try { mapaPrincipal.removeControl(rutaControl); } catch (_) {}
            rutaControl = null;
        }

        const routerLocal = {
            route(waypoints, callback, context) {
                window.setTimeout(() => callback.call(context || this, null, [ruta]), 0);
            },
        };

        const control = L.Routing.control({
            waypoints: [L.latLng(origen.lat, origen.lng), L.latLng(destino.lat, destino.lng)],
            routeWhileDragging: false,
            addWaypoints: false,
            show: true,
            language: 'es',
            router: routerLocal,
            lineOptions: {
                styles: [
                    { color: '#00ffff', opacity: 0.9, weight: 6 },
                    { color: '#0066cc', opacity: 0.4, weight: 10 },
                ],
            },
            createMarker(i, waypoint, total) {
                if (i === 0) {
                    return L.marker(waypoint.latLng, {
                        icon: L.divIcon({
                            html: '<div style="background:#28a745;border-radius:50%;width:18px;height:18px;border:3px solid white;box-shadow:0 0 10px rgba(40,167,69,.8);"></div>',
                            className: 'ruta-origen-icon', iconSize: [24, 24], iconAnchor: [12, 12],
                        }),
                    });
                }
                if (i === total - 1) {
                    return L.marker(waypoint.latLng, {
                        icon: L.divIcon({
                            html: '<div style="background:#dc3545;border-radius:50%;width:24px;height:24px;border:3px solid white;box-shadow:0 0 10px rgba(220,53,69,.8);display:flex;align-items:center;justify-content:center;"><i class="fas fa-flag" style="color:white;font-size:11px;"></i></div>',
                            className: 'ruta-destino-icon', iconSize: [30, 30], iconAnchor: [15, 15],
                        }),
                    });
                }
                return null;
            },
        });

        rutaControl = control;
        control.on('routesfound', event => {
            const encontrada = event.routes?.[0];
            if (!encontrada) {
                mostrarError('El servidor no devolvió una ruta válida.');
                return;
            }
            calculando = false;
            if (typeof procesarRutaCalculada === 'function') {
                procesarRutaCalculada(event, nombre, destino.lat, destino.lng);
            }
        });
        control.on('routingerror', () => {
            calculando = false;
            mostrarError('No se pudo mostrar la ruta calculada. Inténtalo nuevamente.');
        });
        control.addTo(mapaPrincipal);
    }

    async function calcularRutaProduccion(destLat, destLng, destNombre) {
        if (calculando) return;
        if (!window.isSecureContext) {
            mostrarError('La navegación requiere HTTPS.');
            return;
        }

        calculando = true;
        mostrarEstado('Calculando ruta', 'Obteniendo tu ubicación…');
        try {
            const posicion = await obtenerPosicion();
            const origen = { lat: posicion.coords.latitude, lng: posicion.coords.longitude };
            const destino = { lat: Number(destLat), lng: Number(destLng) };
            mostrarEstado('Calculando ruta', 'Buscando la mejor ruta…');
            const datos = await solicitarRuta(origen, destino);
            const ruta = prepararRuta(datos);
            if (ruta.coordinates.length < 2) throw new Error('La ruta recibida no tiene suficiente información.');
            crearControlRuta(ruta, origen, destino, destNombre || 'Refugio');
        } catch (error) {
            calculando = false;
            console.error('[CobijoVzla] Error de ruta:', error);
            mostrarError(error?.message || 'No fue posible calcular la ruta.');
        }
    }

    function instalar() {
        // Captura el botón antes del listener histórico de mapa_publico.html.
        // Así no se inicia simultáneamente la petición directa a OSRM del navegador.
        document.addEventListener('click', event => {
            const boton = event.target.closest?.('.btn-como-llegar');
            if (!boton) return;
            const card = boton.closest('#info-card');
            if (!card) return;
            const titulo = document.getElementById('info-card-title')?.textContent || 'Refugio';
            const body = document.getElementById('info-card-body');
            const data = body?.dataset?.rutaLat ? {
                lat: Number(body.dataset.rutaLat),
                lng: Number(body.dataset.rutaLng),
                nombre: body.dataset.rutaNombre || titulo,
            } : null;
            if (!data || !Number.isFinite(data.lat) || !Number.isFinite(data.lng)) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            calcularRutaProduccion(data.lat, data.lng, data.nombre);
        }, true);

        // El template histórico no deja las coordenadas en el DOM. Enlazamos
        // el botón dinámico con la última opción de ruta que abrió el usuario.
        const original = window.mostrarInfoCard;
        if (typeof original === 'function') return;

        const observar = new MutationObserver(() => {
            const boton = document.querySelector('.btn-como-llegar');
            const body = document.getElementById('info-card-body');
            if (!boton || !body || body.dataset.rutaLat) return;
            // No inventamos coordenadas: las obtiene del listener de refugios
            // mediante el atributo temporal instalado abajo.
        });
        observar.observe(document.body, { childList: true, subtree: true });
    }

    // El listener de captura necesita las coordenadas. Sobrescribimos la
    // función global usada por los marcadores sin alterar la versión lexical
    // histórica: el nuevo botón guarda explícitamente lat/lng en el body.
    function parchearMostrarInfoCard() {
        const interval = window.setInterval(() => {
            if (typeof window.mostrarInfoCard !== 'function') return;
            window.clearInterval(interval);
            const original = window.mostrarInfoCard;
            window.mostrarInfoCard = function(titulo, contenido, opcionesRuta = null) {
                original.call(this, titulo, contenido, opcionesRuta);
                const body = document.getElementById('info-card-body');
                if (body && opcionesRuta) {
                    body.dataset.rutaLat = String(opcionesRuta.lat);
                    body.dataset.rutaLng = String(opcionesRuta.lng);
                    body.dataset.rutaNombre = String(opcionesRuta.nombre || 'Refugio');
                }
            };
        }, 50);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            instalar();
            parchearMostrarInfoCard();
        }, { once: true });
    } else {
        instalar();
        parchearMostrarInfoCard();
    }
})();
