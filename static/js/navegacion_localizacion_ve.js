/**
 * Localización propia de Leaflet Routing Machine para Cobijo VZLA.
 *
 * LRM usa históricamente la clave `sp` para español. La aplicación, sin
 * embargo, solicita `es`; por eso registramos `es` explícitamente y dejamos
 * la navegación independiente del idioma del navegador.
 */
(() => {
    'use strict';

    function instalarLocalizacion() {
        if (!window.L?.Routing) return false;

        const localizacion = {
            directions: {
                N: 'norte',
                NE: 'noreste',
                E: 'este',
                SE: 'sureste',
                S: 'sur',
                SW: 'suroeste',
                W: 'oeste',
                NW: 'noroeste'
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
            formatOrder: function(n) {
                return `${n}.`;
            },
            ui: {
                startPlaceholder: 'Inicio',
                viaPlaceholder: 'Vía {viaNumber}',
                endPlaceholder: 'Destino'
            }
        };

        window.L.Routing.Localization = window.L.Routing.Localization || {};
        window.L.Routing.Localization.es = localizacion;

        // Compatibilidad con instalaciones de LRM que solo reconocen `sp`.
        if (!window.L.Routing.Localization.sp) {
            window.L.Routing.Localization.sp = localizacion;
        }

        return true;
    }

    if (!instalarLocalizacion()) {
        document.addEventListener('DOMContentLoaded', instalarLocalizacion, { once: true });
    }
})();
