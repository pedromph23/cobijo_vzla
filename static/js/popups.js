/**
 * Generadores de HTML para popups de marcadores.
 *
 * Todas las funciones retornan strings HTML listos para `bindPopup()` o
 * `mostrarInfoCard()`. Los datos de texto se escapan para prevenir XSS.
 * Los valores numéricos usados en atributos se normalizan antes de insertarlos.
 */
(function () {
    'use strict';

    /** Escapa texto para insertarlo en HTML de forma segura. */
    function esc(texto) {
        if (texto === null || texto === undefined) return '';
        return String(texto)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /** Convierte coordenadas a números válidos para atributos HTML. */
    function coordenada(valor) {
        const numero = Number(valor);
        return Number.isFinite(numero) ? String(numero) : '';
    }

    /** Normaliza cantidades para evitar mostrar valores inesperados. */
    function cantidad(valor) {
        const numero = Number(valor);
        return Number.isFinite(numero) ? numero : 0;
    }

    function crearPopupRefugio(refugio) {
        const servicios = Array.isArray(refugio.servicios) ? refugio.servicios : [];
        const iconosServicios = {
            agua: '<i class="fas fa-water" aria-hidden="true"></i>',
            comida: '<i class="fas fa-utensils" aria-hidden="true"></i>',
            medicina: '<i class="fas fa-pills" aria-hidden="true"></i>',
        };
        const serviciosHtml = servicios
            .map(function (servicio) {
                const valor = typeof servicio === 'string' ? servicio : '';
                const clave = valor.trim().toLowerCase();
                return `<span class="popup-service" title="${esc(valor)}">${iconosServicios[clave] || esc(valor)}</span>`;
            })
            .join(' ');

        const lat = coordenada(refugio.lat);
        const lng = coordenada(refugio.lng);
        const capacidadDisponible = cantidad(refugio.capacidad_disponible);
        const capacidadTotal = cantidad(refugio.capacidad_total);
        const operativo = Boolean(refugio.operativo);

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon refugio"><i class="fas fa-home" aria-hidden="true"></i></div>
                    <span class="popup-title">${esc(refugio.nombre || 'Refugio sin nombre')}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row">
                        <i class="fas fa-map-marker-alt" aria-hidden="true"></i>
                        <span>${esc(refugio.direccion || 'Sin dirección')}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-users" aria-hidden="true"></i>
                        <span>Capacidad: ${capacidadDisponible}/${capacidadTotal}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-concierge-bell" aria-hidden="true"></i>
                        <span>${serviciosHtml || 'Sin servicios'}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-circle popup-status-dot ${operativo ? 'is-operativo' : 'is-no-operativo'}" aria-hidden="true"></i>
                        <span>${operativo ? 'Operativo' : 'No operativo'}</span>
                    </div>
                </div>
                <div class="popup-actions">
                    <button type="button" class="popup-btn como-llegar"
                            data-lat="${esc(lat)}" data-lng="${esc(lng)}"
                            ${lat && lng ? '' : 'disabled'}>
                        <i class="fas fa-directions" aria-hidden="true"></i> Cómo llegar
                    </button>
                </div>
            </div>
        `;
    }

    function crearPopupZona(zona) {
        const nivel = String(zona.nivel_alerta || '').trim().toLowerCase();
        const nivelValido = ['alto', 'medio', 'bajo'].includes(nivel) ? nivel : 'desconocido';

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon zona"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i></div>
                    <span class="popup-title">${esc(zona.nombre || 'Zona sin nombre')}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row">
                        <i class="fas fa-tag popup-alert-icon popup-alert-${nivelValido}" aria-hidden="true"></i>
                        <span>Alerta: ${esc(nivel ? nivel.toUpperCase() : 'SIN NIVEL')}</span>
                    </div>
                    <div class="popup-row"><i class="fas fa-user-injured" aria-hidden="true"></i>
                        <span>Heridos: ${cantidad(zona.heridos)}</span></div>
                    <div class="popup-row"><i class="fas fa-skull-crossbones" aria-hidden="true"></i>
                        <span>Fallecidos: ${cantidad(zona.fallecidos)}</span></div>
                    <div class="popup-row"><i class="fas fa-people-arrows" aria-hidden="true"></i>
                        <span>Damnificados: ${cantidad(zona.damnificados)}</span></div>
                    <div class="popup-row"><i class="fas fa-info-circle" aria-hidden="true"></i>
                        <span>${esc(zona.descripcion || 'Sin descripción')}</span></div>
                </div>
            </div>
        `;
    }

    function crearPopupDemanda(demanda) {
        let vulnerabilidad = Number(demanda.vulnerabilidad);
        if (!Number.isFinite(vulnerabilidad)) vulnerabilidad = 0;
        vulnerabilidad = Math.max(0, Math.min(1, vulnerabilidad));

        const nivel = vulnerabilidad > 0.7 ? 'alto' : vulnerabilidad > 0.4 ? 'medio' : 'bajo';

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon demanda"><i class="fas fa-users" aria-hidden="true"></i></div>
                    <span class="popup-title">${esc(demanda.nombre || 'Demanda sin nombre')}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row"><i class="fas fa-users" aria-hidden="true"></i>
                        <span>Población: ${cantidad(demanda.poblacion)}</span></div>
                    <div class="popup-row"><i class="fas fa-shield-alt popup-alert-icon popup-alert-${nivel}" aria-hidden="true"></i>
                        <span>Vulnerabilidad: ${Math.round(vulnerabilidad * 100)}%</span></div>
                </div>
            </div>
        `;
    }

    window.crearPopupRefugio = crearPopupRefugio;
    window.crearPopupZona = crearPopupZona;
    window.crearPopupDemanda = crearPopupDemanda;
})();
