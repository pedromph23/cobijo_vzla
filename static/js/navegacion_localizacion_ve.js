/**
 * Localización propia de Leaflet Routing Machine para Cobijo VZLA.
 *
 * LRM utiliza `sp` como clave histórica para español. Se registra además
 * `es` como alias para que la aplicación pueda pedir explícitamente español.
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
        window.L.Routing.Localization.sp = localizacion;
        window.L.Routing.Localization.es = localizacion;
        return true;
    }

    // base.html carga este archivo después de Leaflet Routing Machine y antes
    // de la capa de navegación de Cobijo VZLA. El fallback permite reutilizar
    // el archivo si se mueve a otra plantilla en el futuro.
    if (!instalarLocalizacion()) {
        document.addEventListener('DOMContentLoaded', instalarLocalizacion, { once: true });
    }
})();
