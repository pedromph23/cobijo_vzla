/**
 * Generadores de HTML para popups de marcadores.
 *
 * Todas las funciones retornan strings HTML listos para `bindPopup()` o
 * `mostrarInfoCard()`. Los datos se escapan para prevenir XSS.
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

    function crearPopupRefugio(refugio) {
        const servicios = Array.isArray(refugio.servicios) ? refugio.servicios : [];
        const iconosServicios = {
            agua: '<i class="fas fa-water"></i>',
            comida: '<i class="fas fa-utensils"></i>',
            medicina: '<i class="fas fa-pills"></i>',
        };
        const serviciosHtml = servicios
            .map(function (s) {
                return `<span title="${esc(s)}">${iconosServicios[s] || esc(s)}</span>`;
            })
            .join(' ');

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon refugio"><i class="fas fa-home"></i></div>
                    <span class="popup-title">${esc(refugio.nombre)}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${esc(refugio.direccion || 'Sin dirección')}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-users"></i>
                        <span>Capacidad: ${refugio.capacidad_disponible || 0}/${refugio.capacidad_total || 0}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-concierge-bell"></i>
                        <span>${serviciosHtml || 'Sin servicios'}</span>
                    </div>
                    <div class="popup-row">
                        <i class="fas fa-circle" style="color:${refugio.operativo ? 'green' : 'red'}"></i>
                        <span>${refugio.operativo ? 'Operativo' : 'No operativo'}</span>
                    </div>
                </div>
                <div class="popup-actions">
                    <button type="button" class="popup-btn como-llegar"
                            data-lat="${refugio.lat}" data-lng="${refugio.lng}">
                        <i class="fas fa-directions"></i> Cómo llegar
                    </button>
                </div>
            </div>
        `;
    }

    function crearPopupZona(zona) {
        const colores = { alto: '#dc3545', medio: '#ffc107', bajo: '#28a745' };
        const color = colores[zona.nivel_alerta] || '#6c757d';

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon zona"><i class="fas fa-exclamation-triangle"></i></div>
                    <span class="popup-title">${esc(zona.nombre)}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row">
                        <i class="fas fa-tag" style="color:${color}"></i>
                        <span>Alerta: ${esc((zona.nivel_alerta || '').toUpperCase())}</span>
                    </div>
                    <div class="popup-row"><i class="fas fa-user-injured"></i>
                        <span>Heridos: ${zona.heridos || 0}</span></div>
                    <div class="popup-row"><i class="fas fa-skull-crossbones"></i>
                        <span>Fallecidos: ${zona.fallecidos || 0}</span></div>
                    <div class="popup-row"><i class="fas fa-people-arrows"></i>
                        <span>Damnificados: ${zona.damnificados || 0}</span></div>
                    <div class="popup-row"><i class="fas fa-info-circle"></i>
                        <span>${esc(zona.descripcion || 'Sin descripción')}</span></div>
                </div>
            </div>
        `;
    }

    function crearPopupDemanda(demanda) {
        const v = demanda.vulnerabilidad || 0;
        const color = v > 0.7 ? '#dc3545' : v > 0.4 ? '#ffc107' : '#28a745';

        return `
            <div class="popup-card">
                <div class="popup-header">
                    <div class="popup-icon demanda"><i class="fas fa-users"></i></div>
                    <span class="popup-title">${esc(demanda.nombre)}</span>
                </div>
                <div class="popup-body">
                    <div class="popup-row"><i class="fas fa-users"></i>
                        <span>Población: ${demanda.poblacion || 0}</span></div>
                    <div class="popup-row"><i class="fas fa-shield-alt" style="color:${color}"></i>
                        <span>Vulnerabilidad: ${Math.round(v * 100)}%</span></div>
                </div>
            </div>
        `;
    }

    window.crearPopupRefugio = crearPopupRefugio;
    window.crearPopupZona = crearPopupZona;
    window.crearPopupDemanda = crearPopupDemanda;
})();