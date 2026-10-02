/**
 * Gestión centralizada del tema visual de CobijoVzla.
 *
 * Responsabilidades:
 * - Mantener el tema claro como valor predeterminado.
 * - Persistir la preferencia del usuario.
 * - Sincronizar accesibilidad, icono y color del navegador.
 * - Emitir `themeChanged` para que otros módulos puedan reaccionar.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'cobijo-theme-v2';
    const LIGHT_THEME = 'light';
    const DARK_THEME = 'dark';

    function obtenerTemaGuardado() {
        try {
            return localStorage.getItem(STORAGE_KEY) === DARK_THEME
                ? DARK_THEME
                : LIGHT_THEME;
        } catch (_) {
            return LIGHT_THEME;
        }
    }

    function aplicarTema(theme, persistir = true) {
        const root = document.documentElement;
        const button = document.getElementById('btn-theme-toggle');
        const meta = document.getElementById('meta-theme-color');
        const isDark = theme === DARK_THEME;
        const temaFinal = isDark ? DARK_THEME : LIGHT_THEME;

        root.setAttribute('data-theme', temaFinal);

        if (button) {
            button.setAttribute('aria-pressed', String(isDark));
            button.setAttribute('aria-label', isDark ? 'Activar modo claro' : 'Activar modo oscuro');
            button.setAttribute('title', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');

            const icon = button.querySelector('i');
            if (icon) icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }

        if (meta) meta.setAttribute('content', isDark ? '#1b1e21' : '#f2eee7');

        if (persistir) {
            try {
                localStorage.setItem(STORAGE_KEY, temaFinal);
            } catch (_) {
                // El modo visual sigue funcionando aunque localStorage no esté disponible.
            }
        }

        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: temaFinal } }));
    }

    function inicializar() {
        const themeButton = document.getElementById('btn-theme-toggle');
        const temaInicial = document.documentElement.getAttribute('data-theme') === DARK_THEME
            ? DARK_THEME
            : obtenerTemaGuardado();

        aplicarTema(temaInicial, false);

        if (!themeButton || themeButton.dataset.themeBound === 'true') return;

        themeButton.dataset.themeBound = 'true';
        themeButton.addEventListener('click', function () {
            const actual = document.documentElement.getAttribute('data-theme');
            aplicarTema(actual === DARK_THEME ? LIGHT_THEME : DARK_THEME);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializar, { once: true });
    } else {
        inicializar();
    }
})();
