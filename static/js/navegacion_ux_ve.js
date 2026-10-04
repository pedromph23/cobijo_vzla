/**
 * Mejoras UX del panel de navegación de Cobijo VZLA.
 *
 * La validación geográfica y las métricas dinámicas pertenecen a
 * navegacion_geoguard_ve.js. Esta capa se limita a mejorar el panel visual,
 * evitando listeners y polling duplicados sobre el mismo rutaControl.
 */
(() => {
    'use strict';

    let panelColapsado = false;

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
        if (panel.dataset.uxVe !== '1') {
            panel.dataset.uxVe = '1';
            const header = panel.querySelector('.nav-ruta-header-ve');
            if (header && !document.getElementById('nav-ruta-minimizar-ve')) {
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
            if (kicker && !document.getElementById('nav-ruta-progreso-ve')) {
                const progreso = document.createElement('span');
                progreso.id = 'nav-ruta-progreso-ve';
                progreso.className = 'nav-ruta-progreso-ve';
                kicker.append(' · ');
                kicker.appendChild(progreso);
            }
        }
        marcarPasoActual();
    }

    function observarInterfaz() {
        const objetivo = document.querySelector('.map-main-container') || document.body;
        let programado = false;
        const observer = new MutationObserver(() => {
            if (programado) return;
            programado = true;
            requestAnimationFrame(() => {
                programado = false;
                mejorarPanelVisual();
            });
        });
        observer.observe(objetivo, { childList: true, subtree: true });
        mejorarPanelVisual();
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
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
