/**
 * Fallback de idioma para instrucciones de navegación de Cobijo VZLA.
 *
 * OSRM/LRM puede devolver instrucciones textuales en inglés aunque la
 * interfaz solicite español. Este módulo traduce únicamente la parte
 * verbal de la instrucción y conserva intactos los nombres de las vías.
 */
(() => {
    'use strict';

    const REGLAS = [
        [/^you\s+have\s+arrived\s+at\s+your\s+destination(?:,\s+on\s+the\s+(left|right))?\.?$/i, (_, lado) => `Ha llegado a su destino${lado ? `, a la ${lado === 'left' ? 'izquierda' : 'derecha'}` : ''}`],
        [/^arrive(?:d)?\s+at\s+your\s+destination(?:,\s+on\s+the\s+(left|right))?\.?$/i, (_, lado) => `Ha llegado a su destino${lado ? `, a la ${lado === 'left' ? 'izquierda' : 'derecha'}` : ''}`],
        [/^make\s+a\s+sharp\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la izquierda hacia ${via}`],
        [/^make\s+a\s+sharp\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la derecha hacia ${via}`],
        [/^make\s+a\s+slight\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire ligeramente a la izquierda hacia ${via}`],
        [/^make\s+a\s+slight\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire ligeramente a la derecha hacia ${via}`],
        [/^turn\s+sharp\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la izquierda hacia ${via}`],
        [/^turn\s+sharp\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la derecha hacia ${via}`],
        [/^turn\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire a la izquierda hacia ${via}`],
        [/^turn\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire a la derecha hacia ${via}`],
        [/^turn\s+left\s+towards\s+(.+)$/i, (_, via) => `Gire a la izquierda hacia ${via}`],
        [/^turn\s+right\s+towards\s+(.+)$/i, (_, via) => `Gire a la derecha hacia ${via}`],
        [/^turn\s+left\s+to\s+stay\s+on\s+(.+)$/i, (_, via) => `Gire a la izquierda para continuar por ${via}`],
        [/^turn\s+right\s+to\s+stay\s+on\s+(.+)$/i, (_, via) => `Gire a la derecha para continuar por ${via}`],
        [/^turn\s+left\s+(.+)$/i, (_, resto) => `Gire a la izquierda ${resto}`],
        [/^turn\s+right\s+(.+)$/i, (_, resto) => `Gire a la derecha ${resto}`],
        [/^continue\s+onto\s+(.+)$/i, (_, via) => `Continúe por ${via}`],
        [/^continue\s+on\s+(.+)$/i, (_, via) => `Continúe por ${via}`],
        [/^continue\s+left\s+onto\s+(.+)$/i, (_, via) => `Continúe hacia la izquierda por ${via}`],
        [/^continue\s+right\s+onto\s+(.+)$/i, (_, via) => `Continúe hacia la derecha por ${via}`],
        [/^continue\s+straight\s+onto\s+(.+)$/i, (_, via) => `Continúe recto por ${via}`],
        [/^continue\s+towards\s+(.+)$/i, (_, destino) => `Continúe hacia ${destino}`],
        [/^continue\s+straight\s+towards\s+(.+)$/i, (_, destino) => `Continúe recto hacia ${destino}`],
        [/^go\s+straight\s+towards\s+(.+)$/i, (_, destino) => `Continúe recto hacia ${destino}`],
        [/^go\s+straight\s+(.+)$/i, (_, resto) => `Continúe recto ${resto}`],
        [/^head\s+(north|south|east|west|northeast|northwest|southeast|southwest)(?:\s+towards\s+(.+))?$/i, (_, dir, destino) => `Siga hacia ${direccion(dir)}${destino ? `, hacia ${destino}` : ''}`],
        [/^keep\s+left(?:\s+towards\s+(.+))?$/i, (_, destino) => `Manténgase a la izquierda${destino ? ` hacia ${destino}` : ''}`],
        [/^keep\s+right(?:\s+towards\s+(.+))?$/i, (_, destino) => `Manténgase a la derecha${destino ? ` hacia ${destino}` : ''}`],
        [/^take\s+the\s+(\d+(?:st|nd|rd|th))\s+exit(?:\s+towards\s+(.+))?$/i, (_, salida, destino) => `Tome la ${numeroSalida(salida)} salida${destino ? ` hacia ${destino}` : ''}`],
        [/^take\s+the\s+exit(?:\s+towards\s+(.+))?$/i, (_, destino) => `Tome la salida${destino ? ` hacia ${destino}` : ''}`],
        [/^enter\s+the\s+roundabout(?:\s+and\s+take\s+the\s+(\d+(?:st|nd|rd|th))\s+exit)?(?:\s+towards\s+(.+))?$/i, (_, salida, destino) => `Entre en la rotonda${salida ? ` y tome la ${numeroSalida(salida)} salida` : ''}${destino ? ` hacia ${destino}` : ''}`],
        [/^make\s+a\s+u[-\s]?turn(?:\s+onto\s+(.+))?$/i, (_, via) => `Realice un cambio de sentido${via ? ` hacia ${via}` : ''}`],
        [/^u[-\s]?turn(?:\s+onto\s+(.+))?$/i, (_, via) => `Realice un cambio de sentido${via ? ` hacia ${via}` : ''}`],
        [/^slight\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire ligeramente a la izquierda hacia ${via}`],
        [/^slight\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire ligeramente a la derecha hacia ${via}`],
        [/^sharp\s+left\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la izquierda hacia ${via}`],
        [/^sharp\s+right\s+onto\s+(.+)$/i, (_, via) => `Gire fuertemente a la derecha hacia ${via}`],
        [/^onto\s+(.+)$/i, (_, via) => `Hacia ${via}`],
    ];

    const DIRECCIONES = {
        north: 'el norte', south: 'el sur', east: 'el este', west: 'el oeste',
        northeast: 'el noreste', northwest: 'el noroeste',
        southeast: 'el sureste', southwest: 'el suroeste',
    };

    function direccion(valor) {
        return DIRECCIONES[String(valor).toLowerCase()] || valor;
    }

    function numeroSalida(valor) {
        const mapa = { '1st': '1.ª', '2nd': '2.ª', '3rd': '3.ª' };
        if (mapa[String(valor).toLowerCase()]) return mapa[String(valor).toLowerCase()];
        return `${parseInt(valor, 10)}.ª`;
    }

    function traducir(texto) {
        const original = String(texto ?? '').replace(/\s+/g, ' ').trim();
        if (!original) return original;
        for (const [regex, reemplazo] of REGLAS) {
            if (!regex.test(original)) continue;
            return original.replace(regex, (...args) => reemplazo(...args));
        }
        return original
            .replace(/\bto stay on\b/gi, 'para continuar por')
            .replace(/\btowards\b/gi, 'hacia')
            .replace(/\bonto\b/gi, 'hacia')
            .replace(/\bthe\b/gi, 'la')
            .replace(/\bgo straight\b/gi, 'continúe recto')
            .replace(/\bcontinue\b/gi, 'continúe')
            .trim();
    }

    function traducirElemento(elemento) {
        if (!elemento || elemento.dataset.navTraduccionVe === '1') return;
        const actual = elemento.textContent || '';
        const traducido = traducir(actual);
        if (traducido && traducido !== actual) elemento.textContent = traducido;
        elemento.dataset.navTraduccionVe = '1';
    }

    function traducirInterfaz() {
        document.querySelectorAll(
            '#nav-hud-text, .nav-ruta-paso-main-ve strong, .leaflet-routing-alt tr td'
        ).forEach(traducirElemento);
    }

    function instalar() {
        traducirInterfaz();
        const objetivo = document.querySelector('.map-main-container') || document.body;
        const observer = new MutationObserver(() => traducirInterfaz());
        observer.observe(objetivo, { childList: true, subtree: true, characterData: true });
        window.setInterval(traducirInterfaz, 1200);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
