/**
 * Mejoras UX del panel de navegación de Cobijo VZLA.
 *
 * La validación geográfica y las métricas dinámicas pertenecen a
 * navegacion_geoguard_ve.js. Esta capa se limita a mejorar el panel visual,
 * evitando listeners y polling duplicados sobre el mismo rutaControl.
 *
 * Los estilos pertenecen a responsive.css; este archivo solo gestiona
 * comportamiento y estado del panel.
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

    function sincronizarEspacioInterfaz() {
        const panel = document.getElementById('nav-ruta-panel-ve');
        const activo = Boolean(panel && !panel.classList.contains('oculto') && !panel.hidden);
        document.documentElement.classList.toggle('nav-ruta-activa', activo);
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
        sincronizarEspacioInterfaz();
    }

    function mejorarPanelVisual() {
        const panel = document.getElementById('nav-ruta-panel-ve');
        if (!panel) {
            sincronizarEspacioInterfaz();
            return;
        }
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
        sincronizarEspacioInterfaz();
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
        observer.observe(objetivo, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'hidden', 'style'] });
        mejorarPanelVisual();
    }

    function instalar() {
        observarInterfaz();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
