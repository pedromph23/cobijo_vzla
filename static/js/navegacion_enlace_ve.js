/**
 * Puente de compatibilidad para la navegación pública de Cobijo VZLA.
 *
 * La vista histórica crea un L.Routing.control desde la función calcularRuta
 * declarada en el template. La capa nueva de navegación expone su versión
 * mediante window.calcularRuta, pero una declaración function del template
 * conserva su binding léxico. Este puente detecta el control histórico y
 * deriva la navegación al flujo mejorado sin modificar refugios ni API.
 */
(() => {
    'use strict';

    let controlProcesado = null;
    let puenteOcupado = false;

    function revisarControl() {
        if (puenteOcupado) return;
        if (typeof window.calcularRuta !== 'function') return;
        if (typeof rutaControl === 'undefined' || !rutaControl) return;
        if (rutaControl === controlProcesado) return;

        const control = rutaControl;
        const opciones = control.options || {};

        // La navegación mejorada utiliza show:false. No interceptarla.
        if (opciones.show === false) {
            controlProcesado = control;
            return;
        }

        if (typeof control.getWaypoints !== 'function') return;

        const waypoints = control.getWaypoints();
        const destino = waypoints?.[waypoints.length - 1];
        const latLng = destino?.latLng;
        if (!latLng || !Number.isFinite(latLng.lat) || !Number.isFinite(latLng.lng)) return;

        controlProcesado = control;

        // Esperamos a que el control histórico tenga su ruta inicializada.
        // Así obtenemos el destino real seleccionado por el usuario.
        setTimeout(() => {
            if (puenteOcupado) return;
            if (typeof rutaControl === 'undefined' || rutaControl !== control) return;

            puenteOcupado = true;
            try {
                mapaPrincipal?.removeControl(control);
            } catch (_) {}

            const nombre = destino.name || destino.options?.name || 'Refugio';
            window.calcularRuta(latLng.lat, latLng.lng, nombre);

            setTimeout(() => {
                puenteOcupado = false;
            }, 1500);
        }, 0);
    }

    function instalar() {
        // El control histórico se crea después del clic del usuario.
        // Un intervalo corto permite capturarlo sin modificar la lógica existente.
        window.setInterval(revisarControl, 150);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', instalar, { once: true });
    } else {
        instalar();
    }
})();
