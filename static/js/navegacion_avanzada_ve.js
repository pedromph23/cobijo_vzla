/**
 * Navegación avanzada Cobijo VZLA.
 * Complementa el motor existente sin reemplazarlo.
 * - Vista de conducción: seguimiento de posición + orientación por rumbo.
 * - Velocímetro GPS.
 * - ETA y distancia sincronizadas con el HUD existente cuando están disponibles.
 * - Detección de desvío y recálculo seguro hacia el destino actual.
 * - Carril/límite de velocidad solo cuando el proveedor de ruta entregue esos datos;
 *   nunca se inventan valores.
 */
(() => {
    'use strict';

    const OFF_ROUTE_METERS = 85;
    const OFF_ROUTE_CONFIRMATIONS = 3;
    const RECALC_COOLDOWN_MS = 15000;
    const NAV_ZOOM = 17;
    let desviaciones = 0;
    let ultimoRecalculo = 0;
    let ultimaPosicion = null;
    let ultimaRuta = null;
    let ultimoDestino = null;
    let watchOriginal = null;
    let panel = null;

    const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

    function distanciaMetros(a, b) {
        if (!a || !b) return Infinity;
        const R = 6371000;
        const p1 = a.lat * Math.PI / 180;
        const p2 = b.lat * Math.PI / 180;
        const dp = (b.lat - a.lat) * Math.PI / 180;
        const dl = (b.lng - a.lng) * Math.PI / 180;
        const x = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
        return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
    }

    function rumbo(a, b) {
        if (!a || !b) return null;
        const p1 = a.lat * Math.PI / 180;
        const p2 = b.lat * Math.PI / 180;
        const dl = (b.lng - a.lng) * Math.PI / 180;
        const y = Math.sin(dl) * Math.cos(p2);
        const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
        return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
    }

    function puntoMasCercanoALaRuta(pos, ruta) {
        if (!ruta?.coordinates?.length) return Infinity;
        let minimo = Infinity;
        ruta.coordinates.forEach((coord) => {
            if (!Array.isArray(coord) || coord.length < 2) return;
            minimo = Math.min(minimo, distanciaMetros(pos, { lat: Number(coord[1]), lng: Number(coord[0]) }));
        });
        return minimo;
    }

    function obtenerDestino() {
        if (ultimoDestino) return ultimoDestino;
        try {
            if (window.rutaControl?.getWaypoints) {
                const puntos = window.rutaControl.getWaypoints();
                const ultimo = puntos?.[puntos.length - 1]?.latLng;
                if (ultimo) return { lat: ultimo.lat, lng: ultimo.lng };
            }
        } catch (_) {}
        return null;
    }

    function actualizarVelocimetro(speedMps, accuracy) {
        const velocidad = Math.max(0, Number(speedMps) || 0) * 3.6;
        const valor = document.getElementById('nav-advanced-speed-value');
        const precision = document.getElementById('nav-advanced-speed-accuracy');
        if (valor) valor.textContent = Math.round(velocidad);
        if (precision) precision.textContent = Number.isFinite(accuracy) ? `GPS ±${Math.round(accuracy)} m` : 'GPS';
    }

    function actualizarRumbo(pos) {
        if (!ultimaPosicion) return;
        const heading = rumbo(ultimaPosicion, pos);
        if (heading == null || !window.marcadorUsuarioNav) return;
        const el = window.marcadorUsuarioNav.getElement?.();
        if (el) el.style.setProperty('--nav-heading', `${heading}deg`);
        const mapa = window.mapaPrincipal;
        if (mapa && window.navegacionActiva) {
            mapa.setView([pos.lat, pos.lng], Math.max(mapa.getZoom(), NAV_ZOOM), { animate: true, duration: .35 });
        }
    }

    function actualizarDatosDeRuta(route) {
        if (!route) return;
        ultimaRuta = route;
        const summary = route.summary || {};
        const distanciaKm = Number(summary.totalDistance || 0) / 1000;
        const tiempoMin = Number(summary.totalTime || 0) / 60;
        const distancia = document.getElementById('nav-hud-distance');
        const tiempo = document.getElementById('nav-hud-time');
        const eta = document.getElementById('nav-hud-eta');
        if (distancia && distanciaKm > 0) distancia.textContent = distanciaKm < 10 ? `${distanciaKm.toFixed(1)} km` : `${Math.round(distanciaKm)} km`;
        if (tiempo && tiempoMin >= 0) tiempo.textContent = `${Math.max(1, Math.round(tiempoMin))} min`;
        if (eta && tiempoMin > 0) {
            const fecha = new Date(Date.now() + tiempoMin * 60000);
            eta.textContent = fecha.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        }

        const meta = route.instructions || [];
        const primera = meta[0] || {};
        const lanes = primera.lanes || primera.attributes?.lanes || route.lanes;
        const maxspeed = primera.maxspeed || primera.attributes?.maxspeed || route.maxspeed;
        mostrarMetadatosViales(lanes, maxspeed);
    }

    function mostrarMetadatosViales(lanes, maxspeed) {
        if (!panel) return;
        const carriles = Array.isArray(lanes) ? lanes : null;
        const velocidad = maxspeed != null ? String(maxspeed).replace(/[^0-9.,]/g, '') : '';
        panel.querySelector('[data-nav-lanes]').textContent = carriles?.length ? `Carriles: ${carriles.length}` : 'Carriles: datos no disponibles';
        panel.querySelector('[data-nav-limit]').textContent = velocidad ? `Límite: ${esc(velocidad)} km/h` : 'Límite: datos no disponibles';
    }

    function crearPanel() {
        if (panel || !document.getElementById('nav-hud')) return;
        panel = document.createElement('div');
        panel.id = 'nav-advanced-panel';
        panel.innerHTML = `
            <div class="nav-advanced-speed"><strong id="nav-advanced-speed-value">0</strong><span>km/h</span><small id="nav-advanced-speed-accuracy">GPS</small></div>
            <div class="nav-advanced-road"><span data-nav-lanes>Carriles: datos no disponibles</span><span data-nav-limit>Límite: datos no disponibles</span></div>
            <button type="button" id="nav-advanced-perspective" aria-pressed="false" title="Vista de conducción"><i class="fas fa-location-arrow"></i></button>
        `;
        document.querySelector('.map-main-container')?.appendChild(panel);
        document.getElementById('nav-advanced-perspective')?.addEventListener('click', alternarVistaConduccion);
    }

    function alternarVistaConduccion() {
        const mapa = window.mapaPrincipal;
        const boton = document.getElementById('nav-advanced-perspective');
        if (!mapa || !boton) return;
        const activo = document.body.classList.toggle('nav-driving-view');
        boton.setAttribute('aria-pressed', String(activo));
        if (activo && ultimaPosicion) mapa.setView([ultimaPosicion.lat, ultimaPosicion.lng], NAV_ZOOM, { animate: true });
    }

    function intentarRecalcular(pos) {
        const ahora = Date.now();
        if (!window.navegacionActiva || !window.rutaControl || ahora - ultimoRecalculo < RECALC_COOLDOWN_MS) return;
        const destino = obtenerDestino();
        if (!destino) return;
        const distancia = ultimaRuta?.coordinates ? puntoMasCercanoALaRuta(pos, ultimaRuta) : Infinity;
        if (distancia <= OFF_ROUTE_METERS) {
            desviaciones = 0;
            return;
        }
        desviaciones += 1;
        if (desviaciones < OFF_ROUTE_CONFIRMATIONS) return;
        desviaciones = 0;
        ultimoRecalculo = ahora;
        try {
            window.rutaControl.setWaypoints([L.latLng(pos.lat, pos.lng), L.latLng(destino.lat, destino.lng)]);
            window.speechSynthesis?.cancel();
            if (typeof window.hablar === 'function') window.hablar('Hemos detectado un desvío. Recalculando la ruta.');
        } catch (error) {
            console.warn('[Navegación avanzada] No se pudo recalcular:', error);
        }
    }

    function procesarPosicion(posicion) {
        const pos = { lat: posicion.coords.latitude, lng: posicion.coords.longitude };
        actualizarVelocimetro(posicion.coords.speed, posicion.coords.accuracy);
        actualizarRumbo(pos);
        intentarRecalcular(pos);
        ultimaPosicion = pos;
    }

    function observarNavegacion() {
        const sincronizar = () => {
            crearPanel();
            if (!window.navegacionActiva) {
                document.body.classList.remove('nav-driving-view');
                return;
            }
            if (window.rutaActiva) actualizarDatosDeRuta(window.rutaActiva);
        };
        setInterval(sincronizar, 1000);

        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(procesarPosicion, () => {}, {
                enableHighAccuracy: true,
                maximumAge: 1000,
                timeout: 8000
            });
        }
    }

    function instalarEstilos() {
        if (document.getElementById('nav-advanced-styles')) return;
        const style = document.createElement('style');
        style.id = 'nav-advanced-styles';
        style.textContent = `
            #nav-advanced-panel { position:absolute; left:18px; bottom:24px; z-index:1250; display:flex; align-items:center; gap:12px; padding:10px 12px; border:1px solid rgba(255,255,255,.16); border-radius:16px; background:rgba(15,25,32,.90); color:#fff; box-shadow:0 12px 30px rgba(0,0,0,.24); backdrop-filter:blur(12px); }
            .nav-advanced-speed { min-width:74px; text-align:center; line-height:1; }
            .nav-advanced-speed strong { font-size:1.8rem; font-weight:850; }
            .nav-advanced-speed span { font-size:.62rem; margin-left:3px; opacity:.8; }
            .nav-advanced-speed small { display:block; margin-top:4px; font-size:.54rem; opacity:.55; }
            .nav-advanced-road { display:flex; flex-direction:column; gap:4px; font-size:.65rem; color:rgba(255,255,255,.78); }
            #nav-advanced-perspective { width:38px; height:38px; border:1px solid rgba(255,255,255,.14); border-radius:11px; background:rgba(255,255,255,.09); color:#fff; cursor:pointer; }
            #nav-advanced-perspective[aria-pressed="true"] { background:rgba(44,154,116,.45); }
            body.nav-driving-view .main-map { perspective:1100px; }
            body.nav-driving-view .leaflet-map-pane { transform-origin:center center; transform:perspective(1100px) rotateX(4deg); transition:transform .35s ease; }
            .marcador-usuario-navegacion { transform:rotate(var(--nav-heading,0deg)); transform-origin:center; }
            @media (max-width:700px) { #nav-advanced-panel { left:10px; right:10px; bottom:14px; justify-content:space-between; } .nav-advanced-road { flex:1; } }
        `;
        document.head.appendChild(style);
    }

    function instalar() {
        instalarEstilos();
        observarNavegacion();
        if (window.L) {
            const esperarRuta = setInterval(() => {
                if (window.rutaControl && !window.rutaControl.__navAdvancedHooked) {
                    window.rutaControl.__navAdvancedHooked = true;
                    window.rutaControl.on('routesfound', e => {
                        const route = e.routes?.[0];
                        if (route) actualizarDatosDeRuta(route);
                        if (route?.coordinates) ultimaRuta = route;
                        const puntos = window.rutaControl.getWaypoints?.() || [];
                        const destino = puntos[puntos.length - 1]?.latLng;
                        if (destino) ultimoDestino = { lat: destino.lat, lng: destino.lng };
                    });
                }
            }, 500);
            setTimeout(() => clearInterval(esperarRuta), 30000);
        }
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', instalar, { once:true });
    else instalar();
})();
