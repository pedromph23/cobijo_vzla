/**
 * Navegación pública de Cobijo VZLA.
 *
 * Capa de mejora sobre el mapa existente:
 * - restringe navegación a la zona geográfica de Venezuela (validación de bounds);
 * - genera instrucciones en español de forma independiente del idioma de LRM/OSRM;
 * - reemplaza el panel estándar de Leaflet Routing Machine por un panel compacto;
 * - separa "calcular ruta" de "iniciar navegación";
 * - detecta desvíos y solicita recálculo;
 * - permite pausar/reanudar el seguimiento automático del mapa;
 *
 * El routing se delega al único transporte de CobijoRouting, instalado por
 * navegacion_proxy_ve.js. Este archivo conserva la UX, GPS y navegación.
 */
(() => {
    'use strict';

    const VE_BOUNDS = {
        south: 0.60,
        west: -73.50,
        north: 12.25,
        east: -58.05,
    };

    const NAV_CONFIG = {
        offRouteMeters: 120,
        recalcCooldownMs: 12000,
        arrivalMeters: 30,
        mapFollowZoom: 16,
        gps: {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 3000,
        },
    };

    let navegacionMejoradaInstalada = false;
    let navegacionEnCurso = false;
    let seguimientoMapa = true;
    let recalcEnCurso = false;
    let ultimaRecalibracion = 0;
    let destinoActual = null;
    let rutaMejorada = null;
    let pasoMejorado = 0;
    let watchMejorado = null;
    let instruccionesMejoradas = [];
    let rutaPanel = null;

    function estaEnVenezuela(lat, lng) {
        return Number.isFinite(lat) &&
            Number.isFinite(lng) &&
            lat >= VE_BOUNDS.south &&
            lat <= VE_BOUNDS.north &&
            lng >= VE_BOUNDS.west &&
            lng <= VE_BOUNDS.east;
    }

    function validarPuntoVenezuela(lat, lng, etiqueta = 'La ubicación') {
        if (estaEnVenezuela(lat, lng)) return true;
        mostrarAvisoVenezuela(
            `${etiqueta} está fuera del área de operación de Cobijo VZLA. ` +
            'La navegación está disponible únicamente dentro de Venezuela.'
        );
        return false;
    }

    function mostrarAvisoVenezuela(mensaje) {
        const existente = document.getElementById('aviso-geografico-ve');
        if (existente) existente.remove();
        const aviso = document.createElement('div');
        aviso.id = 'aviso-geografico-ve';
        aviso.className = 'nav-ve-alert';
        aviso.innerHTML = `
            <div class="nav-ve-alert-icon"><i class="fas fa-map-marker-alt"></i></div>
            <div class="nav-ve-alert-content">
                <strong>Área de cobertura</strong>
                <span>${escaparHtml(mensaje)}</span>
            </div>
            <button type="button" aria-label="Cerrar aviso"><i class="fas fa-times"></i></button>
        `;
        aviso.querySelector('button')?.addEventListener('click', () => aviso.remove());
        document.querySelector('.map-main-container')?.appendChild(aviso);
        setTimeout(() => aviso.remove(), 7000);
    }

    function escaparHtml(valor) {
        return String(valor ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function normalizarTipoPaso(paso) {
        return String(paso?.type || paso?.instruction || '')
            .trim().toLowerCase().replace(/[\s_-]+/g, '');
    }

    function nombreVia(paso) {
        return String(paso?.road || paso?.name || paso?.street || '').trim();
    }

    function formatearDistancia(metros) {
        const valor = Number(metros) || 0;
        if (valor < 1000) return `${Math.max(1, Math.round(valor))} m`;
        return `${(valor / 1000).toFixed(valor >= 10000 ? 1 : 2).replace('.', ',')} km`;
    }

    function verboGiro(tipo) {
        const mapa = {
            sharpleft: 'Gire fuertemente a la izquierda',
            sharpright: 'Gire fuertemente a la derecha',
            slightleft: 'Gire ligeramente a la izquierda',
            slightright: 'Gire ligeramente a la derecha',
            left: 'Gire a la izquierda',
            right: 'Gire a la derecha',
            uturn: 'Realice un cambio de sentido',
            reverse: 'Realice un cambio de sentido',
        };
        return mapa[tipo] || null;
    }

    function traducirPaso(paso, indice, total) {
        const tipo = normalizarTipoPaso(paso);
        const via = nombreVia(paso);
        const sufijoVia = via ? ` hacia ${escaparHtml(via)}` : '';
        if (typeMatches(tipo, ['destinationreached', 'arrive', 'arrived'])) return 'Ha llegado a su destino';
        if (typeMatches(tipo, ['depart', 'start'])) return via ? `Salga y continúe por ${escaparHtml(via)}` : 'Inicie la ruta y continúe';
        if (typeMatches(tipo, ['roundabout', 'rotary'])) {
            const salida = paso?.exit ? ` y tome la salida ${paso.exit}` : '';
            return `Entre en la rotonda${salida}${sufijoVia}`;
        }
        if (typeMatches(tipo, ['merge'])) return via ? `Incorpórese a ${escaparHtml(via)}` : 'Incorpórese a la vía';
        if (typeMatches(tipo, ['fork'])) return via ? `Tome la bifurcación hacia ${escaparHtml(via)}` : 'Tome la bifurcación indicada';
        if (typeMatches(tipo, ['continue', 'straight', 'head'])) return via ? `Continúe por ${escaparHtml(via)}` : 'Continúe recto';
        const giro = verboGiro(tipo);
        if (giro) return via ? `${giro} hacia ${escaparHtml(via)}` : giro;
        const original = String(paso?.text || '').trim();
        if (original) return traducirTextoFallback(original, via);
        return indice === total - 1 ? 'Continúe hasta el destino' : 'Continúe por la ruta indicada';
    }

    function typeMatches(tipo, candidatos) {
        return candidatos.some(c => tipo === c || tipo.includes(c));
    }

    function traducirTextoFallback(texto, via = '') {
        const limpio = texto.replace(/\s+/g, ' ').trim();
        const reglas = [
            [/^head\s+south\b/i, 'Siga hacia el sur'],
            [/^head\s+north\b/i, 'Siga hacia el norte'],
            [/^head\s+east\b/i, 'Siga hacia el este'],
            [/^head\s+west\b/i, 'Siga hacia el oeste'],
            [/^make\s+a\s+slight\s+right\b/i, 'Gire ligeramente a la derecha'],
            [/^make\s+a\s+slight\s+left\b/i, 'Gire ligeramente a la izquierda'],
            [/^turn\s+right\b/i, 'Gire a la derecha'],
            [/^turn\s+left\b/i, 'Gire a la izquierda'],
            [/^continue\b/i, 'Continúe'],
            [/^arrive\b/i, 'Ha llegado a su destino'],
        ];
        for (const [regex, reemplazo] of reglas) {
            if (regex.test(limpio)) return via ? `${reemplazo} hacia ${escaparHtml(via)}` : reemplazo;
        }
        return limpio;
    }

    function prepararInstrucciones(ruta) {
        return (ruta?.instructions || []).map((paso, indice, todos) => {
            const text = traducirPaso(paso, indice, todos.length);
            return { ...paso, text, textoPlano: quitarHtml(text) };
        });
    }

    function quitarHtml(texto) {
        const div = document.createElement('div');
        div.innerHTML = texto;
        return div.textContent || div.innerText || '';
    }

    function crearPanelRuta() {
        rutaPanel?.remove();
        const panel = document.createElement('section');
        panel.id = 'nav-ruta-panel-ve';
        panel.className = 'nav-ruta-panel-ve';
        panel.setAttribute('aria-label', 'Indicaciones de la ruta');
        panel.innerHTML = `
            <div class="nav-ruta-header-ve">
                <div><span class="nav-ruta-kicker-ve">Ruta al refugio</span><strong id="nav-ruta-destino-ve">Destino</strong></div>
                <button id="nav-ruta-cerrar-ve" type="button" aria-label="Cerrar instrucciones"><i class="fas fa-times"></i></button>
            </div>
            <div class="nav-ruta-resumen-ve">
                <div><span>Distancia</span><strong id="nav-ruta-dist-ve">--</strong></div>
                <div><span>Tiempo</span><strong id="nav-ruta-tiempo-ve">--</strong></div>
                <div><span>Llegada</span><strong id="nav-ruta-eta-ve">--</strong></div>
            </div>
            <div class="nav-ruta-estado-ve" id="nav-ruta-estado-ve"><i class="fas fa-route"></i><span>Ruta calculada. Revisa las indicaciones antes de iniciar.</span></div>
            <div class="nav-ruta-pasos-ve" id="nav-ruta-pasos-ve"></div>
            <div class="nav-ruta-acciones-ve">
                <button id="nav-ruta-iniciar-ve" class="nav-ruta-btn-primary-ve" type="button"><i class="fas fa-location-arrow"></i> Iniciar navegación</button>
                <button id="nav-ruta-seguir-ve" class="nav-ruta-btn-secondary-ve" type="button"><i class="fas fa-crosshairs"></i> Seguir mi ubicación</button>
            </div>
        `;
        document.querySelector('.map-main-container')?.appendChild(panel);
        rutaPanel = panel;
        panel.querySelector('#nav-ruta-cerrar-ve')?.addEventListener('click', cancelarNavegacionMejorada);
        panel.querySelector('#nav-ruta-iniciar-ve')?.addEventListener('click', iniciarNavegacionMejorada);
        panel.querySelector('#nav-ruta-seguir-ve')?.addEventListener('click', () => {
            seguimientoMapa = true;
            actualizarBotonSeguimiento();
            if (posicionActual && estaEnVenezuela(posicionActual.lat, posicionActual.lng)) {
                mapaPrincipal?.flyTo([posicionActual.lat, posicionActual.lng], NAV_CONFIG.mapFollowZoom, { duration: 0.7 });
            }
        });
        mapaPrincipal?.on('dragstart', () => {
            if (navegacionEnCurso) {
                seguimientoMapa = false;
                actualizarBotonSeguimiento();
            }
        });
    }

    function actualizarBotonSeguimiento() {
        const btn = document.getElementById('nav-ruta-seguir-ve');
        if (!btn) return;
        btn.innerHTML = seguimientoMapa
            ? '<i class="fas fa-crosshairs"></i> Seguimiento activo'
            : '<i class="fas fa-crosshairs"></i> Volver a seguir mi ubicación';
        btn.classList.toggle('activo', seguimientoMapa);
    }

    function renderizarPanelRuta(ruta, destino) {
        crearPanelRuta();
        const instrucciones = prepararInstrucciones(ruta);
        instruccionesMejoradas = instrucciones;
        const totalDistance = Number(ruta.summary?.totalDistance || 0);
        const totalTime = Number(ruta.summary?.totalTime || 0);
        const eta = new Date(Date.now() + totalTime * 1000);
        const etaStr = eta.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        document.getElementById('nav-ruta-destino-ve').textContent = destino.nombre;
        document.getElementById('nav-ruta-dist-ve').textContent = formatearDistancia(totalDistance);
        document.getElementById('nav-ruta-tiempo-ve').textContent = `${Math.max(1, Math.round(totalTime / 60))} min`;
        document.getElementById('nav-ruta-eta-ve').textContent = etaStr;
        const pasos = document.getElementById('nav-ruta-pasos-ve');
        pasos.innerHTML = '';
        instrucciones.forEach((paso, indice) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'nav-ruta-paso-ve';
            item.dataset.index = String(indice);
            item.innerHTML = `<span class="nav-ruta-paso-icon-ve"><i class="fas ${iconoPaso(paso)}"></i></span><span class="nav-ruta-paso-main-ve"><strong>${paso.text}</strong><small>${formatearDistancia(paso.distance || 0)}</small></span>`;
            item.addEventListener('click', () => hablar(paso.textoPlano));
            pasos.appendChild(item);
        });
        actualizarEstadoPanel(
            navegacionEnCurso ? 'Ruta recalculada. Continúa siguiendo las indicaciones.' : 'Ruta lista. Puedes revisar los pasos o iniciar la navegación.',
            navegacionEnCurso ? 'fa-rotate' : 'fa-circle-check'
        );
        actualizarBotonSeguimiento();
    }

    function iconoPaso(paso) {
        const tipo = normalizarTipoPaso(paso);
        if (typeMatches(tipo, ['destinationreached', 'arrive', 'arrived'])) return 'fa-flag-checkered';
        if (typeMatches(tipo, ['roundabout', 'rotary'])) return 'fa-rotate-right';
        if (typeMatches(tipo, ['sharpleft'])) return 'fa-arrow-turn-up fa-flip-horizontal';
        if (typeMatches(tipo, ['sharpright'])) return 'fa-arrow-turn-up';
        if (typeMatches(tipo, ['slightleft'])) return 'fa-arrow-turn-up fa-rotate-270';
        if (typeMatches(tipo, ['slightright'])) return 'fa-arrow-turn-up fa-rotate-90';
        if (typeMatches(tipo, ['left'])) return 'fa-arrow-left';
        if (typeMatches(tipo, ['right'])) return 'fa-arrow-right';
        if (typeMatches(tipo, ['merge'])) return 'fa-code-merge';
        if (typeMatches(tipo, ['fork'])) return 'fa-code-branch';
        return 'fa-arrow-up';
    }

    function actualizarEstadoPanel(texto, icono = 'fa-route') {
        const estado = document.getElementById('nav-ruta-estado-ve');
        if (estado) estado.innerHTML = `<i class="fas ${icono}"></i><span>${escaparHtml(texto)}</span>`;
    }

    function actualizarPasoPanel(indice) {
        const pasos = document.querySelectorAll('.nav-ruta-paso-ve');
        pasos.forEach((el, i) => {
            el.classList.toggle('actual', i === indice);
            if (i === indice) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        });
    }

    function crearRouterNavegacion() {
        if (window.CobijoRouting?.crearRouter) return window.CobijoRouting.crearRouter();
        if (window.L?.Routing?.osrmv1) return window.L.Routing.osrmv1();
        throw new Error('El motor de rutas de CobijoVzla no está disponible.');
    }

    function reemplazarRutaControl(destLat, destLng, destNombre) {
        if (rutaControl) {
            try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
            rutaControl = null;
        }

        const control = L.Routing.control({
            waypoints: [L.latLng(posicionActual.lat, posicionActual.lng), L.latLng(destLat, destLng)],
            routeWhileDragging: false,
            addWaypoints: false,
            show: false,
            language: 'es',
            router: crearRouterNavegacion(),
            lineOptions: {
                styles: [
                    { color: '#168f72', opacity: 0.95, weight: 6 },
                    { color: '#ffffff', opacity: 0.55, weight: 10 }
                ]
            },
            createMarker: function(i, waypoint, n) {
                if (i === 0) return L.marker(waypoint.latLng, { icon: L.divIcon({ html: '<div class="ruta-origen-ve"></div>', className: 'ruta-origen-icon', iconSize: [24, 24], iconAnchor: [12, 12] }) });
                if (i === n - 1) return L.marker(waypoint.latLng, { icon: L.divIcon({ html: '<div class="ruta-destino-ve"><i class="fas fa-house"></i></div>', className: 'ruta-destino-icon', iconSize: [34, 34], iconAnchor: [17, 17] }) });
                return null;
            }
        }).addTo(mapaPrincipal);

        rutaControl = control;
        control.on('routesfound', (e) => {
            const ruta = e.routes?.[0];
            recalcEnCurso = false;
            if (!ruta) {
                actualizarEstadoPanel('No se encontró una ruta válida.', 'fa-triangle-exclamation');
                return;
            }
            rutaMejorada = ruta;
            pasoMejorado = 0;
            renderizarPanelRuta(ruta, { lat: destLat, lng: destLng, nombre: destNombre });
            if (navegacionEnCurso) {
                document.getElementById('nav-hud').style.display = 'flex';
                const primerPaso = instruccionesMejoradas[0];
                if (primerPaso) hablar(`Ruta recalculada. ${primerPaso.textoPlano}`);
            } else {
                document.getElementById('nav-hud').style.display = 'none';
            }
        });
        control.on('routingerror', () => {
            actualizarEstadoPanel('No se pudo calcular la ruta. Verifica la conexión e inténtalo nuevamente.', 'fa-triangle-exclamation');
            recalcEnCurso = false;
        });
        return control;
    }

    function calcularRutaMejorada(destLat, destLng, destNombre) {
        if (!validarPuntoVenezuela(Number(destLat), Number(destLng), 'El refugio')) return;
        detenerNavegacionMejorada(false);
        if (!window.isSecureContext) {
            alert('La geolocalización requiere HTTPS o localhost.');
            return;
        }
        crearPanelRuta();
        actualizarEstadoPanel('Obteniendo tu ubicación...', 'fa-location-dot');
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                if (!validarPuntoVenezuela(lat, lng, 'Tu ubicación actual')) return;
                posicionActual = { lat, lng };
                destinoActual = { lat: Number(destLat), lng: Number(destLng), nombre: destNombre || 'Refugio' };
                actualizarEstadoPanel('Calculando la mejor ruta...', 'fa-spinner fa-spin');
                try {
                    reemplazarRutaControl(destinoActual.lat, destinoActual.lng, destinoActual.nombre);
                } catch (error) {
                    recalcEnCurso = false;
                    actualizarEstadoPanel(error?.message || 'No se pudo iniciar el motor de rutas.', 'fa-triangle-exclamation');
                }
            },
            (err) => {
                const mensajes = { 1: 'Permiso de ubicación denegado.', 2: 'No fue posible determinar tu ubicación.', 3: 'Se agotó el tiempo para obtener tu ubicación.' };
                actualizarEstadoPanel(mensajes[err.code] || 'No se pudo obtener tu ubicación.', 'fa-triangle-exclamation');
            },
            NAV_CONFIG.gps
        );
    }

    function iniciarNavegacionMejorada() {
        if (!rutaMejorada || !destinoActual) return;
        navegacionEnCurso = true;
        seguimientoMapa = true;
        pasoMejorado = 0;
        actualizarBotonSeguimiento();
        document.getElementById('nav-hud').style.display = 'flex';
        document.getElementById('nav-controls').style.display = 'block';
        actualizarEstadoPanel('Navegación activa. Siga las indicaciones.', 'fa-location-arrow');
        const primerPaso = instruccionesMejoradas[0];
        if (primerPaso) hablar(`Iniciando navegación hacia ${destinoActual.nombre}. ${primerPaso.textoPlano || 'Siga las indicaciones.'}`);
        if (watchMejorado !== null) navigator.geolocation.clearWatch(watchMejorado);
        watchMejorado = navigator.geolocation.watchPosition(
            actualizarPosicionMejorada,
            (err) => console.warn('[Nav VE] Error GPS:', err),
            NAV_CONFIG.gps
        );
    }

    function detenerNavegacionMejorada(ocultarPanel = true) {
        navegacionEnCurso = false;
        recalcEnCurso = false;
        if (watchMejorado !== null) {
            navigator.geolocation.clearWatch(watchMejorado);
            watchMejorado = null;
        }
        if (rutaControl) {
            try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
            rutaControl = null;
        }
        rutaMejorada = null;
        destinoActual = null;
        pasoMejorado = 0;
        if (ocultarPanel) rutaPanel?.remove();
        if (ocultarPanel) rutaPanel = null;
        const hud = document.getElementById('nav-hud');
        if (hud) hud.style.display = 'none';
        const controls = document.getElementById('nav-controls');
        if (controls) controls.style.display = 'none';
    }

    function cancelarNavegacionMejorada() {
        detenerNavegacionMejorada(true);
        window.speechSynthesis?.cancel();
    }

    function actualizarPosicionMejorada(pos) {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (!validarPuntoVenezuela(lat, lng, 'Tu ubicación actual')) {
            detenerNavegacionMejorada(false);
            return;
        }
        posicionActual = { lat, lng };
        if (!marcadorUsuarioNav) {
            marcadorUsuarioNav = L.marker([lat, lng], { icon: L.divIcon({ html: '<div class="usuario-nav-ve"></div>', className: 'usuario-nav-icon', iconSize: [22, 22], iconAnchor: [11, 11] }) }).addTo(mapaPrincipal);
        } else {
            marcadorUsuarioNav.setLatLng([lat, lng]);
        }
        if (seguimientoMapa) mapaPrincipal?.flyTo([lat, lng], NAV_CONFIG.mapFollowZoom, { duration: 0.5 });
        if (!destinoActual || !rutaMejorada) return;
        const distanciaDestino = mapaPrincipal.distance([lat, lng], [destinoActual.lat, destinoActual.lng]);
        if (distanciaDestino <= NAV_CONFIG.arrivalMeters) {
            actualizarEstadoPanel('Ha llegado a su destino.', 'fa-flag-checkered');
            hablar(`Ha llegado a ${destinoActual.nombre}.`);
            detenerNavegacionMejorada(false);
            return;
        }
        const coords = rutaMejorada.coordinates || [];
        if (coords.length < 2) return;
        let distanciaRuta = Infinity;
        let indiceCercano = pasoMejorado;
        for (let i = Math.max(0, pasoMejorado - 2); i < coords.length; i += 1) {
            const d = mapaPrincipal.distance([lat, lng], coords[i]);
            if (d < distanciaRuta) {
                distanciaRuta = d;
                indiceCercano = i;
            }
        }
        if (distanciaRuta > NAV_CONFIG.offRouteMeters && !recalcEnCurso && Date.now() - ultimaRecalibracion >= NAV_CONFIG.recalcCooldownMs) {
            recalcEnCurso = true;
            ultimaRecalibracion = Date.now();
            actualizarEstadoPanel('Te has alejado de la ruta. Recalculando...', 'fa-route');
            reemplazarRutaControl(destinoActual.lat, destinoActual.lng, destinoActual.nombre);
            return;
        }
        pasoMejorado = Math.max(pasoMejorado, indiceCercano);
        actualizarPasoPanel(Math.min(pasoMejorado, Math.max(0, instruccionesMejoradas.length - 1)));
        const paso = instruccionesMejoradas[Math.min(pasoMejorado, Math.max(0, instruccionesMejoradas.length - 1))];
        if (paso) {
            const distanciaPaso = Number(paso.distance) || 0;
            const clave = `${pasoMejorado}:${paso.textoPlano}`;
            if (distanciaPaso <= 80 && !pasosAnunciados[clave]) {
                pasosAnunciados[clave] = true;
                hablar(paso.textoPlano);
            }
            const hudText = document.getElementById('nav-hud-text');
            const hudDist = document.getElementById('nav-hud-distance');
            const hudTime = document.getElementById('nav-hud-time');
            const hudEta = document.getElementById('nav-hud-eta');
            if (hudText) hudText.textContent = paso.textoPlano;
            if (hudDist) hudDist.textContent = formatearDistancia(distanciaPaso);
            if (hudTime) hudTime.textContent = `${Math.max(1, Math.round((Number(paso.time) || 0) / 60))} min`;
            if (hudEta) hudEta.textContent = new Date(Date.now() + (Number(paso.time) || 0) * 1000).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        }
    }

    function instalarEstilos() {
        if (document.getElementById('nav-ve-inline-styles')) return;
        const style = document.createElement('style');
        style.id = 'nav-ve-inline-styles';
        style.textContent = `
            .nav-ruta-panel-ve { position: absolute; top: 18px; right: 18px; z-index: 1000; width: min(380px, calc(100% - 36px)); background: var(--surface, #fff); color: var(--text, #1f2937); border: 1px solid var(--border, rgba(0,0,0,.08)); border-radius: 18px; box-shadow: 0 18px 48px rgba(0,0,0,.18); overflow: hidden; }
            .nav-ruta-header-ve { display:flex; justify-content:space-between; gap:12px; padding:16px 18px; background: linear-gradient(135deg, rgba(22,143,114,.16), rgba(0,102,204,.08)); }
            .nav-ruta-header-ve strong { display:block; margin-top:4px; font-size:1.05rem; }
            .nav-ruta-kicker-ve { display:block; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; opacity:.65; }
            .nav-ruta-header-ve button { border:0; background:transparent; font-size:1rem; cursor:pointer; color:inherit; }
            .nav-ruta-resumen-ve { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; padding:12px 18px; }
            .nav-ruta-resumen-ve div { display:flex; flex-direction:column; gap:2px; }
            .nav-ruta-resumen-ve span { font-size:.72rem; opacity:.65; }
            .nav-ruta-pasos-ve { max-height:240px; overflow:auto; padding:0 12px 10px; }
            .nav-ruta-paso-ve { width:100%; display:flex; align-items:center; gap:10px; padding:10px 8px; border:0; border-radius:12px; background:transparent; color:inherit; text-align:left; cursor:pointer; }
            .nav-ruta-paso-ve:hover,.nav-ruta-paso-ve.actual { background:rgba(22,143,114,.09); }
            .nav-ruta-paso-icon-ve { width:32px; height:32px; display:grid; place-items:center; border-radius:10px; background:rgba(22,143,114,.12); color:#168f72; flex:0 0 auto; }
            .nav-ruta-paso-main-ve { min-width:0; display:flex; flex-direction:column; gap:2px; }
            .nav-ruta-paso-main-ve strong { font-size:.86rem; }
            .nav-ruta-paso-main-ve small { opacity:.65; }
            .nav-ruta-estado-ve { display:flex; gap:8px; align-items:flex-start; padding:10px 18px; font-size:.82rem; opacity:.8; }
            .nav-ruta-acciones-ve { display:flex; gap:8px; padding:12px 18px 16px; }
            .nav-ruta-acciones-ve button { flex:1; border:0; border-radius:12px; padding:10px 12px; cursor:pointer; font-weight:700; }
            .nav-ruta-btn-primary-ve { background:#168f72; color:#fff; }
            .nav-ruta-btn-secondary-ve { background:rgba(22,143,114,.1); color:inherit; }
            .nav-ruta-btn-secondary-ve.activo { outline:2px solid rgba(22,143,114,.25); }
            .nav-ve-alert { position:absolute; top:18px; left:18px; right:18px; z-index:1100; display:flex; align-items:center; gap:12px; padding:12px 14px; border-radius:14px; background:var(--surface,#fff); border:1px solid rgba(220,53,69,.28); box-shadow:0 12px 30px rgba(0,0,0,.15); }
            .nav-ve-alert-icon { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; background:rgba(220,53,69,.1); color:#dc3545; flex:0 0 auto; }
            .nav-ve-alert-content { min-width:0; flex:1; display:flex; flex-direction:column; gap:2px; }
            .nav-ve-alert-content span { font-size:.84rem; opacity:.78; }
            .nav-ve-alert button { border:0; background:transparent; color:inherit; cursor:pointer; }
            @media (max-width: 700px) { .nav-ruta-panel-ve { top:10px; right:10px; width:calc(100% - 20px); } .nav-ruta-acciones-ve { flex-direction:column; } }
        `;
        document.head.appendChild(style);
    }

    function instalarNavegacionMejorada() {
        if (navegacionMejoradaInstalada) return;
        if (typeof mapaPrincipal === 'undefined' || !mapaPrincipal) return;
        instalarEstilos();
        window.calcularRuta = calcularRutaMejorada;
        navegacionMejoradaInstalada = true;
        console.info('[Navegación VE] Mejora instalada: español + cobertura Venezuela + panel propio + recálculo.');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(instalarNavegacionMejorada, 0));
    } else {
        setTimeout(instalarNavegacionMejorada, 0);
    }
})();
