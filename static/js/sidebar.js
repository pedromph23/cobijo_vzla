/**
 * Control del sidebar (menú lateral).
 *
 * Responsabilidades:
 * - Gestionar apertura/cierre en móvil.
 * - Gestionar colapso/expansión en escritorio.
 * - Mantener aria-expanded sincronizado.
 * - Cerrar el menú móvil mediante overlay o Escape.
 *
 * El ajuste global de breakpoints pertenece a responsive.js.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        const btnToggle = document.getElementById('btn-toggle-sidebar');
        const btnClose = document.getElementById('btn-close-sidebar');

        if (!sidebar || !btnToggle) return;

        const BREAKPOINT_MOVIL = 768;

        function esDesktop() {
            return window.innerWidth > BREAKPOINT_MOVIL;
        }

        function sincronizarAria() {
            const isOpen = esDesktop()
                ? !sidebar.classList.contains('collapsed')
                : sidebar.classList.contains('open');
            btnToggle.setAttribute('aria-expanded', String(isOpen));
        }

        function cerrarMobile() {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
            sincronizarAria();
        }

        function abrirMobile() {
            sidebar.classList.add('open');
            if (overlay) overlay.classList.add('active');
            sincronizarAria();
        }

        btnToggle.addEventListener('click', function (event) {
            event.preventDefault();

            if (esDesktop()) {
                sidebar.classList.toggle('collapsed');
                sincronizarAria();
            } else {
                sidebar.classList.contains('open') ? cerrarMobile() : abrirMobile();
            }

            // Permite a Leaflet recalcular el espacio disponible después de la animación.
            window.setTimeout(function () {
                window.dispatchEvent(new Event('resize'));
            }, 300);
        });

        if (btnClose) {
            btnClose.addEventListener('click', cerrarMobile);
        }

        if (overlay) {
            overlay.addEventListener('click', cerrarMobile);
        }

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !esDesktop()) {
                cerrarMobile();
            }
        });

        window.addEventListener('resize', sincronizarAria, { passive: true });
        sincronizarAria();
    });
})();
