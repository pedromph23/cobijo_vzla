/**
 * Ajustes responsive globales.
 *
 * Se ejecuta en todas las páginas. Maneja cambios de layout según el ancho
 * de la ventana. Tolerante a la ausencia de elementos (sidebar, minimapa).
 */
(function () {
    'use strict';

    function handleResize() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        const minimapContainer = document.getElementById('minimap-container');
        const esMovil = window.innerWidth <= 768;

        // Sidebar (solo si existe)
        if (sidebar) {
            if (esMovil) {
                sidebar.classList.remove('collapsed');
                sidebar.classList.remove('open');
            }
            if (overlay) overlay.classList.remove('active');
        }

        // Minimapa (solo si existe)
        if (minimapContainer) {
            if (esMovil) {
                minimapContainer.style.width = '120px';
                minimapContainer.style.height = '90px';
            } else {
                minimapContainer.style.width = '200px';
                minimapContainer.style.height = '150px';
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        window.addEventListener('resize', handleResize);
        handleResize();
    });
})();