/**
 * Control del sidebar (menú lateral).
 *
 * ⚠️ ADVERTENCIA: `base.html` ya incluye esta lógica inline. Si cargas este
 * archivo Y `base.html`, el toggle se ejecutará DOS veces y parecerá no
 * funcionar. Usa uno u otro.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        const btnToggle = document.getElementById('btn-toggle-sidebar');
        const btnClose = document.getElementById('btn-close-sidebar');

        if (!sidebar || !btnToggle) return;

        function esDesktop() {
            return window.innerWidth > 768;
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

        btnToggle.addEventListener('click', function (e) {
            e.preventDefault();
            if (esDesktop()) {
                sidebar.classList.toggle('collapsed');
            } else {
                sidebar.classList.contains('open') ? cerrarMobile() : abrirMobile();
            }
            sincronizarAria();
            // Forzar recalcular tamaño del mapa
            setTimeout(function () {
                window.dispatchEvent(new Event('resize'));
            }, 300);
        });

        btnClose && btnClose.addEventListener('click', cerrarMobile);
        overlay && overlay.addEventListener('click', cerrarMobile);

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') cerrarMobile();
        });

        window.addEventListener('resize', sincronizarAria);
        sincronizarAria();
    });
})();