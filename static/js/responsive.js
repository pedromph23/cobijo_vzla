/**
 * Ajustes responsive globales.
 *
 * Se ejecuta en todas las páginas y solo modifica elementos que realmente
 * existen. El control de apertura/cierre del sidebar pertenece a sidebar.js;
 * este módulo se limita a normalizar el layout al cambiar de breakpoint.
 */
(function () {
    'use strict';

    const BREAKPOINT_MOVIL = 768;

    function esMovil() {
        return window.innerWidth <= BREAKPOINT_MOVIL;
    }

    function sincronizarSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        if (!sidebar) return;

        if (esMovil()) {
            sidebar.classList.remove('collapsed');
        } else {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
        }
    }

    function sincronizarMinimapa() {
        const minimapContainer = document.getElementById('minimap-container');
        if (!minimapContainer) return;

        if (esMovil()) {
            minimapContainer.style.width = '120px';
            minimapContainer.style.height = '90px';
        } else {
            minimapContainer.style.width = '200px';
            minimapContainer.style.height = '150px';
        }
    }

    function handleResize() {
        sincronizarSidebar();
        sincronizarMinimapa();
    }

    document.addEventListener('DOMContentLoaded', function () {
        window.addEventListener('resize', handleResize, { passive: true });
        handleResize();
    });
})();
