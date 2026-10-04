/**
 * Geocerca y métricas dinámicas para la navegación de Cobijo VZLA.
 * No sustituye OSRM/LRM ni modifica la lógica de refugios.
 */
(() => {
    'use strict';

    const GEOJSON_URL = '/static/data/venezuela.geojson';
    let poligonoVE = null;
    let controlObservado = null;
    let cargando = null;

    function puntoEnPoligono(lat, lng, ring) {
        let dentro = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            const xi = Number(ring[i][0]);
            const yi = Number(ring[i][1]);
            const xj = Number(ring[j][0]);
            const yj = Number(ring[j][1]);
            const cruza = ((yi > lat) !== (yj > lat)) &&
                (lng < (xj - xi) * (lat - yi) / ((yj - yi) || Number.EPSILON) + xi);
            if (cruza) dentro = !dentro;
        }
        return dentro;
    }

    function dentroVenezuela(lat, lng) {
        if (!poligonoVE || !Number.isFinite(lat) || !Number.isFinite(lng)) return true;
        const geometria = poligonoVE.geometry;
        if (!geometria) return true;
        if (geometria.type === 'Polygon') {
            return geometria.coordinates.some((ring, index) => {
                const enRing = puntoEnPoligono(lat, lng, ring);
                return index === 0 ? enRing : !enRing;
            });
        }
        return true;
    }

    function extraerPuntos(ruta) {
        const coords = ruta?.coordinates || [];
        return coords.map(c => ({
            lat: Number(c?.lat ?? c?.[1]),
            lng: Number(c?.lng ?? c?.lon ?? c?.[0])
        })).filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng));
    }

    function rutaDentroDeVenezuela(ruta) {
        const puntos = extraerPuntos(ruta);
        if (!puntos.length || !poligonoVE) return true;
        const paso = Math.max(1, Math.ceil(puntos.length / 1500));
        for (let i = 0; i < puntos.length; i += paso) {
            if (!dentroVenezuela(puntos[i].lat, puntos[i].lng)) return false;
        }
        return true;
    }

    function mostrarAlerta(mensaje) {
        const anterior = document.getElementById('nav-geoguard-ve');
        anterior?.remove();
        const el = document.createElement('div');
        el.id = 'nav-geoguard-ve';
        el.innerHTML = `<i class="fas fa-shield-halved"></i><div><strong>Navegación limitada a Venezuela</strong><span>${mensaje}</span></div><button type="button" aria-label="Cerrar"><i class="fas fa-times"></i></button>`;
        el.style.cssText = 'position:absolute;left:14px;right:14px;top:14px;z-index:1700;display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border-radius:14px;border:1px solid #d9a441;background:var(--bg-card,#fff);color:var(--text-primary,#24302b);box-shadow:0 14px 36px rgba(0,0,0,.22);font-size:.78rem;';
        const div = el.querySelector('div');
        div.style.cssText = 'display:flex;flex-direction:column;gap:3px;flex:1;line-height:1.35;';
        el.querySelector('button').style.cssText = 'border:0;background:transparent;color:inherit;cursor:pointer;';
        el.querySelector('button').addEventListener('click', () => el.remove());
        document.querySelector('.map-main-container')?.appendChild(el);
        setTimeout(() => el.remove(), 8000);
    }

    async function cargarPoligono() {
        if (poligonoVE) return poligonoVE;
        if (cargando) return cargando;
        cargando = fetch(GEOJSON_URL, { cache: 'force-cache', credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : null)
            .then(data => { poligonoVE = data; return data; })
            .catch(() => null)
            .finally(() => { cargando = null; });
        return cargando;
    }

    function observarRutas() {
        if (typeof rutaControl === 'undefined' || !rutaControl || rutaControl === controlObservado) return;
        controlObservado = rutaControl;
        rutaControl.on?.('routesfound', evento => {
            const ruta = evento?.routes?.[0];
            if (!ruta || !poligonoVE) return;
            if (!rutaDentroDeVenezuela(ruta)) {
                try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
                mostrarAlerta('La ruta calculada sale del territorio venezolano. Selecciona un origen y destino dentro de Venezuela.');
            }
        });
    }

    function distanciaMetros(a, b) {
        const R = 6371000;
        const p1 = a.lat * Math.PI / 180;
        const p2 = b.lat * Math.PI / 180;
        const dp = (b.lat - a.lat) * Math.PI / 180;
        const dl = (b.lng - a.lng) * Math.PI / 180;
        const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
        return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
    }

    function metricasRutaDesdePosicion() {
        if (typeof rutaActiva === 'undefined' || !rutaActiva || typeof posicionActual === 'undefined' || !posicionActual) return null;
        const puntos = extraerPuntos(rutaActiva);
        if (puntos.length < 2) return null;

        let mejor = { distancia: Infinity, indice: 0 };
        for (let i = 0; i < puntos.length - 1; i++) {
            const d = Math.min(distanciaMetros(posicionActual, puntos[i]), distanciaMetros(posicionActual, puntos[i + 1]));
            if (d < mejor.distancia) mejor = { distancia: d, indice: i };
        }

        let restante = distanciaMetros(posicionActual, puntos[mejor.indice + 1]);
        for (let i = mejor.indice + 1; i < puntos.length - 1; i++) restante += distanciaMetros(puntos[i], puntos[i + 1]);
        const total = Number(rutaActiva.summary?.totalDistance || 0);
        const totalTiempo = Number(rutaActiva.summary?.totalTime || 0);
        if (!total || !totalTiempo) return null;
        const restanteClamped = Math.max(0, Math.min(total, restante));
        return { distancia: restanteClamped, segundos: totalTiempo * (restanteClamped / total) };
    }

    function actualizarMetricas() {
        const m = metricasRutaDesdePosicion();
        if (!m) return;
        const dist = document.getElementById('nav-hud-distance');
        const tiempo = document.getElementById('nav-hud-time');
        const eta = document.getElementById('nav-hud-eta');
        const km = m.distancia / 1000;
        const minutos = Math.max(0, Math.ceil(m.segundos / 60));
        const llegada = new Date(Date.now() + m.segundos * 1000).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        if (dist) dist.textContent = `${km < 10 ? km.toFixed(1) : km.toFixed(0)} km`;
        if (tiempo) tiempo.textContent = `${minutos} min`;
        if (eta) eta.textContent = llegada;
    }

    async function instalar() {
        await cargarPoligono();
        observarRutas();
        actualizarMetricas();
        setInterval(() => { observarRutas(); actualizarMetricas(); }, 1000);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', instalar, { once: true });
    else instalar();
})();
