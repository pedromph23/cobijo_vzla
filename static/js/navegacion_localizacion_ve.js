/**
 * Localización propia de Leaflet Routing Machine para Cobijo VZLA.
 *
 * LRM utiliza `sp` como clave histórica para español. Se registra además
 * `es` como alias para que la aplicación pueda pedir explícitamente español.
 *
 * También incluye un fallback para respuestas de OSRM/LRM que ya traen
 * `instruction.text` en inglés. Esto evita que una frase inglesa llegue al
 * panel o a la síntesis de voz aunque el proveedor la entregue traducida.
 */
(() => {
    'use strict';

    const REGLAS = [
        [/^head\s+south\b/i, 'Siga hacia el sur'],
        [/^head\s+north\b/i, 'Siga hacia el norte'],
        [/^head\s+east\b/i, 'Siga hacia el este'],
        [/^head\s+west\b/i, 'Siga hacia el oeste'],
        [/^continue\s+(south|north|east|west|northeast|northwest|southeast|southwest)\b/i, 'Continúe hacia $1'],
        [/^make\s+a\s+slight\s+right\b/i, 'Gire ligeramente a la derecha'],
        [/^make\s+a\s+slight\s+left\b/i, 'Gire ligeramente a la izquierda'],
        [/^slight\s+right\b/i, 'Gire ligeramente a la derecha'],
        [/^slight\s+left\b/i, 'Gire ligeramente a la izquierda'],
        [/^sharp\s+right\b/i, 'Gire fuertemente a la derecha'],
        [/^sharp\s+left\b/i, 'Gire fuertemente a la izquierda'],
        [/^turn\s+right\b/i, 'Gire a la derecha'],
        [/^turn\s+left\b/i, 'Gire a la izquierda'],
        [/^turn\s+around\b/i, 'Realice un cambio de sentido'],
        [/^u[-\s]?turn\b/i, 'Realice un cambio de sentido'],
        [/^go\s+straight\b/i, 'Continúe recto'],
        [/^continue\b/i, 'Continúe'],
        [/^arrive(?:d)?\b/i, 'Ha llegado a su destino'],
        [/^you\s+have\s+arrived\b/i, 'Ha llegado a su destino']
    ];

    const DIRECCIONES = {
        south: 'sur', north: 'norte', east: 'este', west: 'oeste',
        northeast: 'noreste', northwest: 'noroeste',
        southeast: 'sureste', southwest: 'suroeste'
    };

    function traducirTexto(texto) {
        let valor = String(texto ?? '').replace(/\s+/g, ' ').trim();
        if (!valor) return valor;

        // Conserva el nombre de la vía y cambia únicamente la orden.
        for (const [regex, reemplazo] of REGLAS) {
            if (regex.test(valor)) {
                valor = valor.replace(regex, (...args) => {
                    let salida = reemplazo;
                    const captura = args[1];
                    if (captura && DIRECCIONES[captura.toLowerCase()]) {
                        salida = salida.replace('$1', DIRECCIONES[captura.toLowerCase()]);
                    }
                    return salida;
                });
                break;
            }
        }

        valor = valor
            .replace(/\bonto\b/gi, 'hacia')
            .replace(/\bon\b/gi, 'por')
            .replace(/\btowards\b/gi, 'hacia')
            .replace(/\bto stay on\b/gi, 'para continuar por')
            .replace(/\bgo straight\b/gi, 'continúe recto')
            .replace(/\bthe\b/gi, 'la')
            .replace(/\s{2,}/g, ' ')
            .trim();

        return valor;
    }

    function instalarLocalizacion() {
        if (!window.L?.Routing) return false;

        const localizacion = {
            directions: {
                N: 'norte', NE: 'noreste', E: 'este', SE: 'sureste',
                S: 'sur', SW: 'suroeste', W: 'oeste', NW: 'noroeste'
            },
            instructions: {
                Head: ['Siga hacia {dir}', ' por {road}'],
                Continue: ['Continúe hacia {dir}', ' por {road}'],
                SlightRight: ['Gire ligeramente a la derecha', ' hacia {road}'],
                Right: ['Gire a la derecha', ' hacia {road}'],
                SharpRight: ['Gire fuertemente a la derecha', ' hacia {road}'],
                TurnAround: ['Realice un cambio de sentido'],
                SharpLeft: ['Gire fuertemente a la izquierda', ' hacia {road}'],
                Left: ['Gire a la izquierda', ' hacia {road}'],
                SlightLeft: ['Gire ligeramente a la izquierda', ' hacia {road}'],
                WaypointReached: ['Ha llegado al punto intermedio'],
                Roundabout: ['Entre en la rotonda y tome la {exitStr} salida', ' hacia {road}'],
                DestinationReached: ['Ha llegado a su destino']
            },
            formatOrder: function(n) { return `${n}.`; },
            ui: {
                startPlaceholder: 'Inicio',
                viaPlaceholder: 'Vía {viaNumber}',
                endPlaceholder: 'Destino'
            }
        };

        window.L.Routing.Localization = window.L.Routing.Localization || {};
        window.L.Routing.Localization.sp = localizacion;
        window.L.Routing.Localization.es = localizacion;
        return true;
    }

    function instalarFallbackVisualYVoz() {
        if (window.__cobijoLocalizacionVEInstalada) return;
        window.__cobijoLocalizacionVEInstalada = true;

        const traducirNodo = (nodo) => {
            if (!nodo || nodo.nodeType !== Node.ELEMENT_NODE) return;
            if (nodo.matches?.('.nav-ruta-paso-main-ve strong, #nav-hud-text')) {
                nodo.textContent = traducirTexto(nodo.textContent);
            }
            nodo.querySelectorAll?.('.nav-ruta-paso-main-ve strong, #nav-hud-text')
                .forEach(el => { el.textContent = traducirTexto(el.textContent); });
        };

        const observar = () => {
            const objetivo = document.querySelector('.map-main-container') || document.body;
            const observer = new MutationObserver(mutations => {
                for (const mutation of mutations) {
                    mutation.addedNodes.forEach(traducirNodo);
                    if (mutation.type === 'characterData' && mutation.target.parentElement) {
                        traducirNodo(mutation.target.parentElement);
                    }
                }
            });
            observer.observe(objetivo, { childList: true, subtree: true, characterData: true });
        };

        if (document.body) observar();
        else document.addEventListener('DOMContentLoaded', observar, { once: true });

        // La capa de navegación usa speechSynthesis. Traducimos únicamente
        // frases de maniobra; los nombres de calles permanecen intactos.
        if (window.speechSynthesis?.speak) {
            const hablarOriginal = window.speechSynthesis.speak.bind(window.speechSynthesis);
            window.speechSynthesis.speak = function(utterance) {
                if (utterance && typeof utterance.text === 'string') {
                    utterance.text = traducirTexto(utterance.text);
                    utterance.lang = 'es-VE';
                }
                return hablarOriginal(utterance);
            };
        }
    }

    function instalar() {
        instalarLocalizacion();
        instalarFallbackVisualYVoz();
    }

    // base.html carga este archivo después de Leaflet Routing Machine y antes
    // de la capa de navegación de Cobijo VZLA.
    if (!instalarLocalizacion()) {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalarFallbackVisualYVoz();
    }
})();
