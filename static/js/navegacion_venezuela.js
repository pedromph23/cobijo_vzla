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
 * No modifica la API ni la lógica de refugios/zonas.
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
            .trim()
            .toLowerCase()
            .replace(/[\s_-]+/g, '');
    }

    function nombreVia(paso) {
        const road = paso?.road || paso?.name || paso?.street || '';
        return String(road).trim();
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

        if (typeMatches(tipo, ['destinationreached', 'arrive', 'arrived'])) {
            return 'Ha llegado a su destino';
        }

        if (typeMatches(tipo, ['depart', 'start'])) {
            return via ? `Salga y continúe por ${escaparHtml(via)}` : 'Inicie la ruta y continúe';
        }

        if (typeMatches(tipo, ['roundabout', 'rotary'])) {
            const salida = paso?.exit ? ` y tome la salida ${paso.exit}` : '';
            return `Entre en la rotonda${salida}${sufijoVia}`;
        }

        if (typeMatches(tipo, ['merge'])) {
            return via ? `Incorpórese a ${escaparHtml(via)}` : 'Incorpórese a la vía';
        }

        if (typeMatches(tipo, ['fork'])) {
            return via ? `Tome la bifurcación hacia ${escaparHtml(via)}` : 'Tome la bifurcación indicada';
        }

        if (typeMatches(tipo, ['continue', 'straight', 'head'])) {
            return via ? `Continúe por ${escaparHtml(via)}` : 'Continúe recto';
        }

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
            if (regex.test(limpio)) {
                return via ? `${reemplazo} hacia ${escaparHtml(via)}` : reemplazo;
            }
        }
        return limpio;
    }

    function prepararInstrucciones(ruta) {
        return (ruta?.instructions || []).map((paso, indice, todos) => {
            const text = traducirPaso(paso, indice, todos.length);
            return {
                ...paso,
                text,
                textoPlano: quitarHtml(text),
            };
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
                <div>
                    <span class="nav-ruta-kicker-ve">Ruta al refugio</span>
                    <strong id="nav-ruta-destino-ve">Destino</strong>
                </div>
                <button id="nav-ruta-cerrar-ve" type="button" aria-label="Cerrar instrucciones">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="nav-ruta-resumen-ve">
                <div><span>Distancia</span><strong id="nav-ruta-dist-ve">--</strong></div>
                <div><span>Tiempo</span><strong id="nav-ruta-tiempo-ve">--</strong></div>
                <div><span>Llegada</span><strong id="nav-ruta-eta-ve">--</strong></div>
            </div>
            <div class="nav-ruta-estado-ve" id="nav-ruta-estado-ve">
                <i class="fas fa-route"></i>
                <span>Ruta calculada. Revisa las indicaciones antes de iniciar.</span>
            </div>
            <div class="nav-ruta-pasos-ve" id="nav-ruta-pasos-ve"></div>
            <div class="nav-ruta-acciones-ve">
                <button id="nav-ruta-iniciar-ve" class="nav-ruta-btn-primary-ve" type="button">
                    <i class="fas fa-location-arrow"></i> Iniciar navegación
                </button>
                <button id="nav-ruta-seguir-ve" class="nav-ruta-btn-secondary-ve" type="button">
                    <i class="fas fa-crosshairs"></i> Seguir mi ubicación
                </button>
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
            item.innerHTML = `
                <span class="nav-ruta-paso-icon-ve"><i class="fas ${iconoPaso(paso)}"></i></span>
                <span class="nav-ruta-paso-main-ve">
                    <strong>${paso.text}</strong>
                    <small>${formatearDistancia(paso.distance || 0)}</small>
                </span>
            `;
            item.addEventListener('click', () => hablar(paso.textoPlano));
            pasos.appendChild(item);
        });

        actualizarEstadoPanel(
            navegacionEnCurso
                ? 'Ruta recalculada. Continúa siguiendo las indicaciones.'
                : 'Ruta lista. Puedes revisar los pasos o iniciar la navegación.',
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

    function reemplazarRutaControl(destLat, destLng, destNombre) {
        if (rutaControl) {
            try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
            rutaControl = null;
        }

        const control = L.Routing.control({
            waypoints: [
                L.latLng(posicionActual.lat, posicionActual.lng),
                L.latLng(destLat, destLng)
            ],
            routeWhileDragging: false,
            addWaypoints: false,
            show: false,
            language: 'es',
            router: L.Routing.osrmv1({
                serviceUrl: 'https://router.project-osrm.org/route/v1',
                profile: 'driving'
            }),
            lineOptions: {
                styles: [
                    { color: '#168f72', opacity: 0.95, weight: 6 },
                    { color: '#ffffff', opacity: 0.55, weight: 10 }
                ]
            },
            createMarker: function(i, waypoint, n) {
                if (i === 0) {
                    return L.marker(waypoint.latLng, {
                        icon: L.divIcon({
                            html: '<div class="ruta-origen-ve"></div>',
                            className: 'ruta-origen-icon',
                            iconSize: [24, 24],
                            iconAnchor: [12, 12]
                        })
                    });
                }
                if (i === n - 1) {
                    return L.marker(waypoint.latLng, {
                        icon: L.divIcon({
                            html: '<div class="ruta-destino-ve"><i class="fas fa-house"></i></div>',
                            className: 'ruta-destino-icon',
                            iconSize: [34, 34],
                            iconAnchor: [17, 17]
                        })
                    });
                }
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
                destinoActual = {
                    lat: Number(destLat),
                    lng: Number(destLng),
                    nombre: destNombre || 'Refugio'
                };

                actualizarEstadoPanel('Calculando la mejor ruta...', 'fa-spinner fa-spin');
                reemplazarRutaControl(destinoActual.lat, destinoActual.lng, destinoActual.nombre);
            },
            (err) => {
                const mensajes = {
                    1: 'Permiso de ubicación denegado.',
                    2: 'No fue posible determinar tu ubicación.',
                    3: 'Se agotó el tiempo para obtener tu ubicación.'
                };
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
        instruccionesMejoradas = prepararInstrucciones(rutaMejorada);
        actualizarBotonSeguimiento();

        const btn = document.getElementById('nav-ruta-iniciar-ve');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-location-arrow"></i> Navegación activa';
            btn.disabled = true;
        }

        document.getElementById('nav-hud').style.display = 'flex';
        actualizarHUDMejorado();
        hablar(`Iniciando navegación hacia ${destinoActual.nombre}. ${instruccionesMejoradas[0]?.textoPlano || 'Siga las indicaciones.'}`);

        if (watchMejorado !== null) navigator.geolocation.clearWatch(watchMejorado);
        watchMejorado = navigator.geolocation.watchPosition(
            actualizarPosicionMejorada,
            (err) => {
                console.warn('[Nav VE] Error GPS:', err);
                actualizarEstadoPanel('Se perdió temporalmente la señal GPS.', 'fa-location-crosshairs');
            },
            NAV_CONFIG.gps
        );
    }

    function actualizarPosicionMejorada(pos) {
        if (!navegacionEnCurso || !destinoActual) return;

        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (!validarPuntoVenezuela(lat, lng, 'Tu ubicación actual')) {
            detenerNavegacionMejorada(false);
            return;
        }

        posicionActual = { lat, lng };

        if (!marcadorUsuarioNav) {
            marcadorUsuarioNav = L.marker([lat, lng], {
                icon: L.divIcon({
                    html: '<div class="marcador-nav-usuario-ve"></div>',
                    className: 'marcador-nav-usuario',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                }),
                zIndexOffset: 1000
            }).addTo(mapaPrincipal);
        } else {
            marcadorUsuarioNav.setLatLng([lat, lng]);
        }

        const distanciaDestino = calcularDistancia(lat, lng, destinoActual.lat, destinoActual.lng);
        if (distanciaDestino <= NAV_CONFIG.arrivalMeters) {
            hablar('Ha llegado a su destino. Navegación finalizada.');
            finalizarNavegacionMejorada();
            return;
        }

        if (rutaMejorada) {
            const distanciaRuta = distanciaMinimaARuta(lat, lng, rutaMejorada.coordinates || []);
            if (distanciaRuta > NAV_CONFIG.offRouteMeters) {
                solicitarRecalculo(lat, lng);
                return;
            }
        }

        avanzarPasoSegunPosicion(lat, lng);
        actualizarHUDMejorado();

        if (seguimientoMapa && mapaPrincipal) {
            mapaPrincipal.panTo([lat, lng], { animate: true, duration: 0.35 });
        }
    }

    function distanciaMinimaARuta(lat, lng, coordinates) {
        if (!coordinates.length) return 0;
        let minima = Infinity;
        for (const coord of coordinates) {
            const distancia = calcularDistancia(lat, lng, coord.lat, coord.lng);
            if (distancia < minima) minima = distancia;
            if (minima <= NAV_CONFIG.offRouteMeters) break;
        }
        return minima;
    }

    function solicitarRecalculo(lat, lng) {
        const ahora = Date.now();
        if (recalcEnCurso || ahora - ultimaRecalibracion < NAV_CONFIG.recalcCooldownMs) return;

        ultimaRecalibracion = ahora;
        recalcEnCurso = true;
        actualizarEstadoPanel('Te saliste de la ruta. Recalculando...', 'fa-rotate');

        if (!destinoActual) {
            recalcEnCurso = false;
            return;
        }

        reemplazarRutaControl(destinoActual.lat, destinoActual.lng, destinoActual.nombre);
    }

    function avanzarPasoSegunPosicion(lat, lng) {
        if (!instruccionesMejoradas.length) return;
        const actual = instruccionesMejoradas[Math.min(pasoMejorado, instruccionesMejoradas.length - 1)];
        const coord = rutaMejorada?.coordinates?.[actual.index || 0];
        if (!coord) return;

        const distancia = calcularDistancia(lat, lng, coord.lat, coord.lng);
        if (distancia <= 35 && pasoMejorado < instruccionesMejoradas.length - 1) {
            pasoMejorado += 1;
            const siguiente = instruccionesMejoradas[pasoMejorado];
            hablar(siguiente.textoPlano);
        }
    }

    function actualizarHUDMejorado() {
        if (!rutaMejorada || !instruccionesMejoradas.length) return;
        const paso = instruccionesMejoradas[Math.min(pasoMejorado, instruccionesMejoradas.length - 1)];
        const coord = rutaMejorada.coordinates?.[paso.index || 0];

        let distanciaPaso = 0;
        if (coord && posicionActual) {
            distanciaPaso = calcularDistancia(posicionActual.lat, posicionActual.lng, coord.lat, coord.lng);
        }

        const texto = document.getElementById('nav-hud-text');
        const distancia = document.getElementById('nav-hud-distance');
        const tiempo = document.getElementById('nav-hud-time');
        const eta = document.getElementById('nav-hud-eta');
        const flecha = document.getElementById('nav-hud-arrow');

        if (texto) texto.innerHTML = `<span class="nav-hud-distance-ve">${formatearDistancia(distanciaPaso)}</span> — ${paso.text}`;
        if (distancia) distancia.textContent = formatearDistancia(rutaMejorada.summary?.totalDistance || 0);
        if (tiempo) tiempo.textContent = `${Math.max(1, Math.round((rutaMejorada.summary?.totalTime || 60) / 60))} min`;
        if (eta) {
            const etaDate = new Date(Date.now() + (rutaMejorada.summary?.totalTime || 60) * 1000);
            eta.textContent = etaDate.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
        }
        if (flecha) flecha.className = `fas ${iconoPaso(paso)}`;

        actualizarPasoPanel(pasoMejorado);
    }

    function finalizarNavegacionMejorada() {
        detenerNavegacionMejorada(false);
        actualizarEstadoPanel('Has llegado al refugio. Navegación finalizada.', 'fa-circle-check');
        const btn = document.getElementById('nav-ruta-iniciar-ve');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-circle-check"></i> Llegaste al destino';
        }
        document.getElementById('nav-hud').style.display = 'none';
    }

    function detenerNavegacionMejorada(cancelarRutaCompleta = true) {
        if (watchMejorado !== null) {
            navigator.geolocation.clearWatch(watchMejorado);
            watchMejorado = null;
        }
        navegacionEnCurso = false;
        recalcEnCurso = false;

        if (typeof detenerVoz === 'function') detenerVoz();

        if (cancelarRutaCompleta && rutaControl) {
            try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
            rutaControl = null;
            rutaMejorada = null;
        }
    }

    function cancelarNavegacionMejorada() {
        detenerNavegacionMejorada(true);
        destinoActual = null;
        instruccionesMejoradas = [];
        pasoMejorado = 0;
        rutaPanel?.remove();
        rutaPanel = null;
        document.getElementById('nav-hud').style.display = 'none';
        if (marcadorUsuarioNav) {
            mapaPrincipal.removeLayer(marcadorUsuarioNav);
            marcadorUsuarioNav = null;
        }
        document.getElementById('nav-controls').style.display = 'none';
    }

    function instalarEstilos() {
        if (document.getElementById('nav-ve-styles')) return;
        const style = document.createElement('style');
        style.id = 'nav-ve-styles';
        style.textContent = `
            .nav-ruta-panel-ve {
                position:absolute; right:18px; top:72px; z-index:1200;
                width:min(390px,calc(100% - 36px)); max-height:min(72vh,680px);
                display:flex; flex-direction:column; overflow:hidden;
                background:var(--bg-card,#fff); color:var(--text-primary,#24302b);
                border:1px solid var(--border-color,#dbe5df); border-radius:18px;
                box-shadow:0 16px 45px rgba(20,50,40,.22);
                backdrop-filter:blur(12px);
            }
            .nav-ruta-header-ve{display:flex;align-items:center;justify-content:space-between;padding:15px 16px 12px;border-bottom:1px solid var(--border-color,#e4ebe7)}
            .nav-ruta-header-ve>div{min-width:0;display:flex;flex-direction:column;gap:2px}
            .nav-ruta-kicker-ve{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;color:#5c8778;font-weight:700}
            .nav-ruta-header-ve strong{font-size:1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
            .nav-ruta-header-ve button{border:0;background:transparent;color:var(--text-secondary,#66736e);width:34px;height:34px;border-radius:9px;cursor:pointer}
            .nav-ruta-resumen-ve{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border-color,#e4ebe7)}
            .nav-ruta-resumen-ve>div{background:var(--bg-card,#fff);padding:10px 8px;text-align:center;display:flex;flex-direction:column;gap:2px}
            .nav-ruta-resumen-ve span{font-size:.65rem;text-transform:uppercase;color:var(--text-secondary,#74807b)}
            .nav-ruta-resumen-ve strong{font-size:.92rem}
            .nav-ruta-estado-ve{display:flex;align-items:center;gap:8px;padding:10px 14px;font-size:.78rem;background:rgba(22,143,114,.08);color:#286957}
            .nav-ruta-pasos-ve{overflow:auto;padding:4px 8px;flex:1;min-height:80px}
            .nav-ruta-paso-ve{width:100%;display:flex;align-items:center;gap:10px;text-align:left;padding:10px 8px;border:0;border-bottom:1px solid var(--border-color,#edf1ef);background:transparent;color:inherit;cursor:pointer;border-radius:10px}
            .nav-ruta-paso-ve:hover,.nav-ruta-paso-ve.actual{background:rgba(22,143,114,.08)}
            .nav-ruta-paso-icon-ve{width:34px;height:34px;flex:0 0 34px;border-radius:10px;background:rgba(22,143,114,.12);color:#168f72;display:flex;align-items:center;justify-content:center}
            .nav-ruta-paso-main-ve{display:flex;justify-content:space-between;gap:10px;align-items:center;min-width:0;flex:1}
            .nav-ruta-paso-main-ve strong{font-size:.8rem;line-height:1.25;font-weight:600}
            .nav-ruta-paso-main-ve small{font-size:.7rem;white-space:nowrap;color:var(--text-secondary,#6f7b76)}
            .nav-ruta-acciones-ve{display:grid;grid-template-columns:1fr;gap:7px;padding:10px;border-top:1px solid var(--border-color,#e4ebe7);background:var(--bg-card,#fff)}
            .nav-ruta-btn-primary-ve,.nav-ruta-btn-secondary-ve{min-height:44px;border-radius:11px;border:1px solid transparent;font-weight:700;cursor:pointer}
            .nav-ruta-btn-primary-ve{background:#168f72;color:#fff}
            .nav-ruta-btn-primary-ve:disabled{opacity:.65;cursor:default}
            .nav-ruta-btn-secondary-ve{background:rgba(22,143,114,.08);color:#168f72;border-color:rgba(22,143,114,.22)}
            .nav-ruta-btn-secondary-ve.activo{background:rgba(22,143,114,.14)}
            .nav-ve-alert{position:absolute;left:18px;right:18px;top:18px;z-index:1400;display:flex;align-items:center;gap:10px;padding:11px 13px;border-radius:13px;background:var(--bg-card,#fff);color:var(--text-primary,#24302b);border:1px solid #f0c36a;box-shadow:0 10px 30px rgba(0,0,0,.18)}
            .nav-ve-alert-icon{width:32px;height:32px;border-radius:9px;background:#fff2cf;color:#a56a00;display:flex;align-items:center;justify-content:center;flex:0 0 32px}
            .nav-ve-alert-content{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1}
            .nav-ve-alert-content strong{font-size:.8rem}.nav-ve-alert-content span{font-size:.72rem;line-height:1.3}
            .nav-ve-alert button{border:0;background:transparent;color:inherit;cursor:pointer;width:30px;height:30px}
            .ruta-origen-ve{width:18px;height:18px;border-radius:50%;background:#168f72;border:3px solid #fff;box-shadow:0 0 12px rgba(22,143,114,.65)}
            .ruta-destino-ve{width:30px;height:30px;border-radius:50%;background:#e06a55;border:3px solid #fff;box-shadow:0 0 12px rgba(224,106,85,.55);display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px}
            .marcador-nav-usuario-ve{width:20px;height:20px;border-radius:50%;background:#168f72;border:3px solid #fff;box-shadow:0 0 18px rgba(22,143,114,.65)}
            .nav-hud-distance-ve{font-weight:800;color:#2b9c7e}
            [data-theme="dark"] .nav-ruta-panel-ve{background:#182421;color:#e6efeb;border-color:#2f403a}
            [data-theme="dark"] .nav-ruta-resumen-ve>div,[data-theme="dark"] .nav-ruta-acciones-ve{background:#182421}
            [data-theme="dark"] .nav-ruta-estado-ve{background:rgba(46,174,141,.12);color:#9bd9c5}
            [data-theme="dark"] .nav-ruta-paso-ve{border-color:#2a3934}
            [data-theme="dark"] .nav-ruta-paso-ve:hover,[data-theme="dark"] .nav-ruta-paso-ve.actual{background:rgba(46,174,141,.12)}
            @media(max-width:768px){
                .nav-ruta-panel-ve{left:10px;right:10px;top:auto;bottom:78px;width:auto;max-height:52vh}
                .nav-ve-alert{left:10px;right:10px;top:10px}
            }
        `;
        document.head.appendChild(style);
    }

    function instalar() {
        if (navegacionMejoradaInstalada) return;
        if (typeof mapaPrincipal === 'undefined') return;

        instalarEstilos();
        window.calcularRuta = calcularRutaMejorada;
        navegacionMejoradaInstalada = true;
        console.info('[Navegación VE] Mejora instalada: español + cobertura Venezuela + panel propio + recálculo.');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
