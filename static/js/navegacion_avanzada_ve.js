/**
 * Capa avanzada de navegación. Complementa el motor existente.
 * No crea un segundo GPS ni un segundo Routing.control.
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
    let panel = null;
    let vistaConduccion = false;
    let arrastre = null;

    function estadoNavegacion() { try { return typeof navegacionActiva !== 'undefined' && navegacionActiva; } catch (_) { return false; } }
    function mapa() { try { return typeof mapaPrincipal !== 'undefined' ? mapaPrincipal : null; } catch (_) { return null; } }
    function marcador() { try { return typeof marcadorUsuarioNav !== 'undefined' ? marcadorUsuarioNav : null; } catch (_) { return null; } }
    function controlRuta() { try { return typeof rutaControl !== 'undefined' ? rutaControl : null; } catch (_) { return null; } }

    function distanciaMetros(a, b) {
        if (!a || !b) return Infinity;
        const R = 6371000, p1 = a.lat * Math.PI / 180, p2 = b.lat * Math.PI / 180;
        const dp = (b.lat - a.lat) * Math.PI / 180, dl = (b.lng - a.lng) * Math.PI / 180;
        const x = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
        return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
    }
    function rumbo(a, b) {
        if (!a || !b) return null;
        const p1 = a.lat * Math.PI / 180, p2 = b.lat * Math.PI / 180, dl = (b.lng - a.lng) * Math.PI / 180;
        const y = Math.sin(dl) * Math.cos(p2), x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
        return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
    }
    function puntoMasCercano(pos, ruta) {
        if (!ruta?.coordinates?.length) return Infinity;
        let minimo = Infinity;
        ruta.coordinates.forEach((coord) => {
            const lat = Number(coord?.lat ?? coord?.[1]), lng = Number(coord?.lng ?? coord?.[0]);
            if (Number.isFinite(lat) && Number.isFinite(lng)) minimo = Math.min(minimo, distanciaMetros(pos, { lat, lng }));
        });
        return minimo;
    }
    function actualizarVelocimetro(coords) {
        const valor = document.getElementById('nav-advanced-speed-value'), precision = document.getElementById('nav-advanced-speed-accuracy');
        if (valor) valor.textContent = Math.round(Math.max(0, Number(coords?.speed) || 0) * 3.6);
        if (precision) precision.textContent = Number.isFinite(coords?.accuracy) ? `GPS ±${Math.round(coords.accuracy)} m` : 'GPS';
    }
    function actualizarRumbo(pos) {
        if (!ultimaPosicion) return;
        const heading = rumbo(ultimaPosicion, pos), el = marcador()?.getElement?.();
        if (el && heading != null) el.style.setProperty('--nav-heading', `${heading}deg`);
        if (vistaConduccion && estadoNavegacion() && mapa()) mapa().setView([pos.lat, pos.lng], Math.max(mapa().getZoom(), NAV_ZOOM), { animate: true, duration: .25 });
    }
    function actualizarRuta(ruta) {
        if (!ruta) return;
        ultimaRuta = ruta;
        const summary = ruta.summary || {}, distanciaKm = Number(summary.totalDistance || 0) / 1000, tiempoMin = Number(summary.totalTime || 0) / 60;
        const distancia = document.getElementById('nav-hud-distance'), tiempo = document.getElementById('nav-hud-time'), eta = document.getElementById('nav-hud-eta');
        if (distancia && distanciaKm > 0) distancia.textContent = distanciaKm < 10 ? `${distanciaKm.toFixed(1)} km` : `${Math.round(distanciaKm)} km`;
        if (tiempo && tiempoMin >= 0) tiempo.textContent = `${Math.max(1, Math.round(tiempoMin))} min`;
        if (eta && tiempoMin > 0) eta.textContent = new Date(Date.now() + tiempoMin * 60000).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        const paso = ruta.instructions?.[0] || {}, lanes = paso.lanes || paso.attributes?.lanes || ruta.lanes, maxspeed = paso.maxspeed || paso.attributes?.maxspeed || ruta.maxspeed;
        const lanesNode = panel?.querySelector('[data-nav-lanes]'), limitNode = panel?.querySelector('[data-nav-limit]');
        if (lanesNode) lanesNode.textContent = Array.isArray(lanes) && lanes.length ? `Carriles: ${lanes.length}` : 'Carriles: datos no disponibles';
        if (limitNode) limitNode.textContent = maxspeed != null ? `Límite: ${String(maxspeed).replace(/[^0-9.,]/g, '')} km/h` : 'Límite: datos no disponibles';
    }

    function hacerMovible(elemento, asa) {
        if (!elemento || !asa || asa.dataset.dragReady === '1') return;
        asa.dataset.dragReady = '1';
        asa.addEventListener('pointerdown', (evento) => {
            if (evento.button !== 0) return;
            evento.preventDefault();
            const rect = elemento.getBoundingClientRect();
            arrastre = { elemento, asa, offsetX: evento.clientX - rect.left, offsetY: evento.clientY - rect.top };
            asa.setPointerCapture?.(evento.pointerId);
            elemento.classList.add('nav-panel-dragging');
        });
        asa.addEventListener('pointermove', (evento) => {
            if (!arrastre || arrastre.asa !== asa) return;
            const cont = document.querySelector('.map-main-container')?.getBoundingClientRect();
            if (!cont) return;
            let left = evento.clientX - cont.left - arrastre.offsetX, top = evento.clientY - cont.top - arrastre.offsetY;
            left = Math.max(6, Math.min(left, cont.width - elemento.offsetWidth - 6));
            top = Math.max(6, Math.min(top, cont.height - elemento.offsetHeight - 6));
            elemento.style.left = `${left}px`; elemento.style.top = `${top}px`; elemento.style.right = 'auto'; elemento.style.bottom = 'auto';
        });
        const terminar = () => { if (arrastre?.asa === asa) { elemento.classList.remove('nav-panel-dragging'); arrastre = null; } };
        asa.addEventListener('pointerup', terminar); asa.addEventListener('pointercancel', terminar);
    }

    function crearPanel() {
        if (panel || !document.querySelector('.map-main-container')) return;
        panel = document.createElement('div');
        panel.id = 'nav-advanced-panel';
        panel.innerHTML = '<button type="button" class="nav-panel-handle" title="Arrastrar panel" aria-label="Mover panel"><i class="fas fa-grip-lines"></i></button><div class="nav-advanced-speed"><strong id="nav-advanced-speed-value">0</strong><span> km/h</span><small id="nav-advanced-speed-accuracy">GPS</small></div><div class="nav-advanced-road"><span data-nav-lanes>Carriles: datos no disponibles</span><span data-nav-limit>Límite: datos no disponibles</span></div><button type="button" id="nav-advanced-perspective" aria-pressed="false" title="Vista de conducción"><i class="fas fa-location-arrow"></i></button>';
        document.querySelector('.map-main-container').appendChild(panel);
        hacerMovible(panel, panel.querySelector('.nav-panel-handle'));
        panel.querySelector('#nav-advanced-perspective').addEventListener('click', () => {
            vistaConduccion = !vistaConduccion;
            document.body.classList.toggle('nav-driving-view', vistaConduccion && estadoNavegacion());
            panel.querySelector('#nav-advanced-perspective').setAttribute('aria-pressed', String(vistaConduccion));
            if (vistaConduccion && ultimaPosicion && mapa()) mapa().setView([ultimaPosicion.lat, ultimaPosicion.lng], NAV_ZOOM, { animate: true });
        });
    }
    function detectarDestino() {
        if (ultimoDestino) return ultimoDestino;
        try { const puntos = controlRuta()?.getWaypoints?.() || [], d = puntos[puntos.length - 1]?.latLng; if (d) return { lat: d.lat, lng: d.lng, nombre: 'su destino' }; } catch (_) {}
        return null;
    }
    function intentarRecalcular(pos) {
        if (!estadoNavegacion() || !ultimaRuta) return;
        const ahora = Date.now(); if (ahora - ultimoRecalculo < RECALC_COOLDOWN_MS) return;
        const destino = detectarDestino(); if (!destino) return;
        const distancia = puntoMasCercano(pos, ultimaRuta);
        if (distancia <= OFF_ROUTE_METERS) { desviaciones = 0; return; }
        desviaciones += 1; if (desviaciones < OFF_ROUTE_CONFIRMATIONS) return;
        desviaciones = 0; ultimoRecalculo = ahora;
        try { const control = controlRuta(); if (!control || typeof L === 'undefined') return; control.setWaypoints([L.latLng(pos.lat, pos.lng), L.latLng(destino.lat, destino.lng)]); if (typeof hablar === 'function') hablar('Hemos detectado un desvío. Recalculando la ruta.'); } catch (error) { console.warn('[Navegación avanzada] Recálculo no disponible:', error); }
    }
    function instalarEstilos() {
        if (document.getElementById('nav-advanced-styles')) return;
        const style = document.createElement('style'); style.id = 'nav-advanced-styles'; style.textContent = `
            #nav-advanced-panel{position:absolute;left:18px;bottom:24px;z-index:1250;display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid rgba(255,255,255,.18);border-radius:15px;background:rgba(15,25,32,.94);color:#fff;box-shadow:0 12px 30px rgba(0,0,0,.25);backdrop-filter:blur(12px);touch-action:none;min-width:250px}.nav-panel-handle{width:28px;height:38px;border:0;border-radius:9px;background:rgba(255,255,255,.08);color:rgba(255,255,255,.75);cursor:grab}.nav-panel-handle:active{cursor:grabbing}.nav-panel-dragging{opacity:.92;box-shadow:0 18px 42px rgba(0,0,0,.34)}
            .nav-advanced-speed{min-width:70px;text-align:center;line-height:1}.nav-advanced-speed strong{font-size:1.7rem;font-weight:850}.nav-advanced-speed span{font-size:.62rem;opacity:.8}.nav-advanced-speed small{display:block;margin-top:4px;font-size:.54rem;opacity:.55}.nav-advanced-road{display:flex;flex-direction:column;gap:4px;font-size:.65rem;color:rgba(255,255,255,.78);flex:1}.nav-advanced-road span{white-space:nowrap}
            #nav-advanced-perspective{width:38px;height:38px;border:1px solid rgba(255,255,255,.14);border-radius:11px;background:rgba(255,255,255,.09);color:#fff;cursor:pointer;flex:none}#nav-advanced-perspective[aria-pressed="true"]{background:rgba(44,154,116,.45)}body.nav-driving-view .main-map{perspective:1100px}body.nav-driving-view .leaflet-map-pane{transform-origin:center center;transform:perspective(1100px) rotateX(4deg);transition:transform .35s ease}.marcador-nav-usuario{transform:rotate(var(--nav-heading,0deg));transform-origin:center}
            @media(max-width:700px){#nav-advanced-panel{left:10px;right:10px;bottom:14px;min-width:0}.nav-advanced-road{overflow:hidden}.nav-advanced-road span{overflow:hidden;text-overflow:ellipsis}.nav-panel-handle{flex:none}}
        `; document.head.appendChild(style);
    }
    function sincronizar() {
        crearPanel();
        if (!estadoNavegacion()) { document.body.classList.remove('nav-driving-view'); return; }
        try { if (typeof rutaActiva !== 'undefined' && rutaActiva) actualizarRuta(rutaActiva); } catch (_) {}
    }
    function instalar() {
        instalarEstilos(); sincronizar(); window.setInterval(sincronizar, 1000);
        if (navigator.geolocation) navigator.geolocation.watchPosition((pos) => { if (!estadoNavegacion()) return; const actual = { lat: Number(pos.coords.latitude), lng: Number(pos.coords.longitude) }; actualizarVelocimetro(pos.coords); actualizarRumbo(actual); intentarRecalcular(actual); ultimaPosicion = actual; }, () => {}, { enableHighAccuracy: true, maximumAge: 1000, timeout: 8000 });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', instalar, { once: true }); else instalar();
})();