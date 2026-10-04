/**
 * Mejoras de UX y seguridad de navegación para Cobijo VZLA.
 *
 * Esta capa no reemplaza el motor de rutas: trabaja sobre la navegación
 * existente y evita tocar la lógica de refugios, zonas y API.
 */
(() => {
    'use strict';

    const BOUNDS_VE = {
        south: 0.60,
        west: -73.50,
        north: 12.25,
        east: -58.05,
    };

    const RUTA_GUARD = {
        tolerance: 0.08,
        maxPointsToCheck: 2500,
    };

    let controlObservado = null;
    let panelColapsado = false;
    let avisoRutaMostrado = false;

    function dentroBounds(lat, lng) {
        return Number.isFinite(lat) && Number.isFinite(lng) &&
            lat >= BOUNDS_VE.south && lat <= BOUNDS_VE.north &&
            lng >= BOUNDS_VE.west && lng <= BOUNDS_VE.east;
    }

    function puntoRutaValido(coord) {
        const lat = Number(coord?.lat ?? coord?.[1]);
        const lng = Number(coord?.lng ?? coord?.lon ?? coord?.[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return true;

        return dentroBounds(
            Math.min(BOUNDS_VE.north, Math.max(BOUNDS_VE.south, lat)),
            Math.min(BOUNDS_VE.east, Math.max(BOUNDS_VE.west, lng))
        );
    }

    function validarRutaVenezuela(ruta) {
        const coords = ruta?.coordinates || [];
        if (!coords.length) return true;

        const salto = Math.max(1, Math.ceil(coords.length / RUTA_GUARD.maxPointsToCheck));
        for (let i = 0; i < coords.length; i += salto) {
            const coord = coords[i];
            const lat = Number(coord?.lat ?? coord?.[1]);
            const lng = Number(coord?.lng ?? coord?.lon ?? coord?.[0]);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

            if (lat < BOUNDS_VE.south - RUTA_GUARD.tolerance ||
                lat > BOUNDS_VE.north + RUTA_GUARD.tolerance ||
                lng < BOUNDS_VE.west - RUTA_GUARD.tolerance ||
                lng > BOUNDS_VE.east + RUTA_GUARD.tolerance) {
                return false;
            }
        }
        return true;
    }

    function mostrarAvisoRuta() {
        if (avisoRutaMostrado) return;
        avisoRutaMostrado = true;

        const existente = document.getElementById('nav-ve-ruta-fuera-area');
        existente?.remove();

        const aviso = document.createElement('div');
        aviso.id = 'nav-ve-ruta-fuera-area';
        aviso.className = 'nav-ve-ruta-alerta';
        aviso.innerHTML = `
            <i class="fas fa-map-location-dot" aria-hidden="true"></i>
            <div>
                <strong>Ruta fuera del área de cobertura</strong>
                <span>La ruta calculada sale del territorio de operación de Cobijo VZLA. Prueba nuevamente desde una ubicación y destino dentro de Venezuela.</span>
            </div>
            <button type="button" aria-label="Cerrar aviso"><i class="fas fa-times"></i></button>
        `;
        aviso.querySelector('button')?.addEventListener('click', () => {
            aviso.remove();
            avisoRutaMostrado = false;
        });
        document.querySelector('.map-main-container')?.appendChild(aviso);
        setTimeout(() => {
            aviso.remove();
            avisoRutaMostrado = false;
        }, 9000);
    }

    function marcarPasoActual() {
        const pasos = [...document.querySelectorAll('.nav-ruta-paso-ve')];
        if (!pasos.length) return;

        const activo = pasos.findIndex(el => el.classList.contains('actual'));
        const contador = document.getElementById('nav-ruta-progreso-ve');
        if (contador) {
            contador.textContent = activo >= 0
                ? `Paso ${activo + 1} de ${pasos.length}`
                : `${pasos.length} indicaciones`;
        }
    }

    function agregarControlesPanel() {
        const panel = document.getElementById('nav-ruta-panel-ve');
        if (!panel || panel.dataset.uxVe === '1') return;
        panel.dataset.uxVe = '1';

        const header = panel.querySelector('.nav-ruta-header-ve');
        if (header) {
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.id = 'nav-ruta-minimizar-ve';
            boton.className = 'nav-ruta-minimizar-ve';
            boton.setAttribute('aria-label', 'Minimizar indicaciones');
            boton.title = 'Minimizar indicaciones';
            boton.innerHTML = '<i class="fas fa-chevron-down" aria-hidden="true"></i>';
            boton.addEventListener('click', alternarPanel);
            header.insertBefore(boton, header.lastElementChild);
        }

        const kicker = panel.querySelector('.nav-ruta-kicker-ve');
        if (kicker) {
            const progreso = document.createElement('span');
            progreso.id = 'nav-ruta-progreso-ve';
            progreso.className = 'nav-ruta-progreso-ve';
            kicker.append(' · ');
            kicker.appendChild(progreso);
        }

        marcarPasoActual();
    }

    function alternarPanel() {
        const panel = document.getElementById('nav-ruta-panel-ve');
        if (!panel) return;

        panelColapsado = !panelColapsado;
        panel.classList.toggle('colapsado', panelColapsado);
        const boton = document.getElementById('nav-ruta-minimizar-ve');
        if (boton) {
            boton.innerHTML = panelColapsado
                ? '<i class="fas fa-chevron-up" aria-hidden="true"></i>'
                : '<i class="fas fa-chevron-down" aria-hidden="true"></i>';
            boton.setAttribute('aria-label', panelColapsado ? 'Mostrar indicaciones' : 'Minimizar indicaciones');
            boton.title = panelColapsado ? 'Mostrar indicaciones' : 'Minimizar indicaciones';
        }
    }

    function mejorarPanelVisual() {
        const panel = document.getElementById('nav-ruta-panel-ve');
        if (!panel) return;
        agregarControlesPanel();
        marcarPasoActual();
    }

    function vigilarRuta() {
        if (typeof rutaControl === 'undefined' || !rutaControl || rutaControl === controlObservado) return;

        controlObservado = rutaControl;
        rutaControl.on?.('routesfound', evento => {
            const ruta = evento?.routes?.[0];
            if (!ruta) return;

            if (!validarRutaVenezuela(ruta)) {
                try { mapaPrincipal?.removeControl(rutaControl); } catch (_) {}
                const estado = document.getElementById('nav-ruta-estado-ve');
                if (estado) {
                    estado.innerHTML = '<i class="fas fa-triangle-exclamation"></i><span>La ruta propuesta sale del área de cobertura de Venezuela.</span>';
                }
                mostrarAvisoRuta();
                return;
            }

            // Una ruta válida vuelve a habilitar el aviso para futuros cálculos.
            avisoRutaMostrado = false;
            setTimeout(mejorarPanelVisual, 0);
        });

        rutaControl.on?.('routingerror', () => {
            const estado = document.getElementById('nav-ruta-estado-ve');
            if (estado) {
                estado.innerHTML = '<i class="fas fa-triangle-exclamation"></i><span>No se pudo calcular la ruta. Inténtalo nuevamente.</span>';
            }
        });
    }

    function observarInterfaz() {
        const objetivo = document.querySelector('.map-main-container') || document.body;
        const observer = new MutationObserver(() => {
            mejorarPanelVisual();
            vigilarRuta();
            marcarPasoActual();
        });
        observer.observe(objetivo, { childList: true, subtree: true });
    }

    function instalarEstilosUX() {
        if (document.getElementById('nav-ve-ux-styles')) return;
        const style = document.createElement('style');
        style.id = 'nav-ve-ux-styles';
        style.textContent = `
            .nav-ruta-panel-ve{width:min(360px,calc(100% - 28px));max-height:min(68vh,650px);right:14px;top:68px}
            .nav-ruta-header-ve{gap:5px}
            .nav-ruta-header-ve>div:first-child{flex:1;min-width:0}
            .nav-ruta-kicker-ve{display:block;font-size:.64rem}
            .nav-ruta-progreso-ve{letter-spacing:0;text-transform:none;font-size:.61rem;font-weight:600;opacity:.75}
            .nav-ruta-minimizar-ve{order:1!important;border:0;background:rgba(22,143,114,.09)!important;color:#168f72!important;width:30px!important;height:30px!important;border-radius:8px!important;cursor:pointer;margin-right:2px}
            .nav-ruta-header-ve button#nav-ruta-cerrar-ve{order:2}
            .nav-ruta-panel-ve.colapsado{max-height:62px}
            .nav-ruta-panel-ve.colapsado .nav-ruta-resumen-ve,
            .nav-ruta-panel-ve.colapsado .nav-ruta-estado-ve,
            .nav-ruta-panel-ve.colapsado .nav-ruta-pasos-ve,
            .nav-ruta-panel-ve.colapsado .nav-ruta-acciones-ve{display:none}
            .nav-ruta-panel-ve.colapsado .nav-ruta-header-ve{border-bottom:0;padding-bottom:15px}
            .nav-ve-ruta-alerta{position:absolute;left:14px;right:14px;top:14px;z-index:1600;display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border:1px solid #e3a33b;border-radius:13px;background:var(--bg-card,#fff);color:var(--text-primary,#24302b);box-shadow:0 14px 36px rgba(0,0,0,.22)}
            .nav-ve-ruta-alerta>i{color:#b97809;font-size:1.1rem;margin-top:2px}
            .nav-ve-ruta-alerta div{display:flex;flex-direction:column;gap:3px;flex:1}
            .nav-ve-ruta-alerta strong{font-size:.8rem}
            .nav-ve-ruta-alerta span{font-size:.72rem;line-height:1.35}
            .nav-ve-ruta-alerta button{border:0;background:transparent;color:inherit;cursor:pointer}
            [data-theme="dark"] .nav-ve-ruta-alerta{background:#182421;color:#e6efeb;border-color:#8b6b2d}
            @media(max-width:768px){
                .nav-ruta-panel-ve{left:10px;right:10px;bottom:72px;top:auto;width:auto;max-height:50vh}
                .nav-ruta-panel-ve.colapsado{max-height:58px}
            }
        `;
        document.head.appendChild(style);
    }

    function instalar() {
        instalarEstilosUX();
        observarInterfaz();
        mejorarPanelVisual();
        vigilarRuta();

        // El control de LRM se crea después de este script al calcular una ruta.
        // El intervalo solo vive mientras la página del mapa esté abierta.
        window.setInterval(() => {
            mejorarPanelVisual();
            vigilarRuta();
            marcarPasoActual();
        }, 700);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
