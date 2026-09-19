/**
 * Gestión del tema claro/oscuro.
 *
 * IMPORTANTE: `base.html` actualmente fuerza `data-theme="dark"` y oculta
 * el botón `#btn-toggle-theme`. Este archivo se mantiene por si en el
 * futuro se reactiva el toggle. Si el botón no existe, no hace nada.
 */
(function () {
    'use strict';

    const CLAVE_STORAGE = 'cobijo_theme';

    document.addEventListener('DOMContentLoaded', function () {
        const btnToggle = document.getElementById('btn-toggle-theme');
        const iconTheme = document.getElementById('icon-theme');
        const html = document.documentElement;

        // Si no existe el botón, no hay nada que hacer
        if (!btnToggle || !iconTheme) return;

        function aplicarTema(tema) {
            const temaSeguro = tema === 'light' ? 'light' : 'dark';
            html.setAttribute('data-theme', temaSeguro);
            try {
                localStorage.setItem(CLAVE_STORAGE, temaSeguro);
            } catch (_) {
                /* localStorage bloqueado, ignorar */
            }

            if (temaSeguro === 'dark') {
                iconTheme.className = 'fas fa-sun';
                iconTheme.style.color = '#ffcc00';
                btnToggle.setAttribute('title', 'Cambiar a modo claro');
                btnToggle.setAttribute('aria-label', 'Cambiar a modo claro');
            } else {
                iconTheme.className = 'fas fa-moon';
                iconTheme.style.color = 'white';
                btnToggle.setAttribute('title', 'Cambiar a modo oscuro');
                btnToggle.setAttribute('aria-label', 'Cambiar a modo oscuro');
            }

            document.dispatchEvent(
                new CustomEvent('themeChanged', { detail: { theme: temaSeguro } })
            );
        }

        // Cargar tema previo o preferencia del sistema
        let temaInicial = 'dark';
        try {
            const guardado = localStorage.getItem(CLAVE_STORAGE);
            if (guardado === 'dark' || guardado === 'light') {
                temaInicial = guardado;
            } else if (
                window.matchMedia &&
                window.matchMedia('(prefers-color-scheme: dark)').matches
            ) {
                temaInicial = 'dark';
            } else {
                temaInicial = 'light';
            }
        } catch (_) {
            temaInicial = 'dark';
        }
        aplicarTema(temaInicial);

        btnToggle.addEventListener('click', function (e) {
            e.preventDefault();
            const actual = html.getAttribute('data-theme');
            aplicarTema(actual === 'dark' ? 'light' : 'dark');
        });
    });
})();