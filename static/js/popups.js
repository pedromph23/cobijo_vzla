function crearPopupRefugio(refugio) {
    const servicios = Array.isArray(refugio.servicios) ? refugio.servicios : [];
    const iconosServicios = {
        agua: '<i class="fas fa-water"></i>',
        comida: '<i class="fas fa-utensils"></i>',
        medicina: '<i class="fas fa-pills"></i>'
    };
    
    const serviciosHtml = servicios.map(s => 
        `<span title="${s}">${iconosServicios[s] || s}</span>`
    ).join(' ');
    
    return `
        <div class="popup-card">
            <div class="popup-header">
                <div class="popup-icon refugio"><i class="fas fa-home"></i></div>
                <span class="popup-title">${refugio.nombre}</span>
            </div>
            <div class="popup-body">
                <div class="popup-row">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${refugio.direccion}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-users"></i>
                    <span>Capacidad: ${refugio.capacidad_disponible}/${refugio.capacidad_total}</span>
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
                <button class="popup-btn como-llegar" onclick="comoLlegar(${refugio.lat}, ${refugio.lng})">
                    <i class="fas fa-directions"></i> Cómo llegar
                </button>
                <button class="popup-btn mas-info">
                    <i class="fas fa-info-circle"></i> Más info
                </button>
            </div>
        </div>
    `;
}

function crearPopupZona(zona) {
    const nivelColor = {
        alto: '#dc3545',
        medio: '#ffc107',
        bajo: '#28a745'
    };
    
    return `
        <div class="popup-card">
            <div class="popup-header">
                <div class="popup-icon zona"><i class="fas fa-exclamation-triangle"></i></div>
                <span class="popup-title">${zona.nombre}</span>
            </div>
            <div class="popup-body">
                <div class="popup-row">
                    <i class="fas fa-tag" style="color:${nivelColor[zona.nivel_alerta]}"></i>
                    <span>Alerta: ${zona.nivel_alerta.toUpperCase()}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-user-injured"></i>
                    <span>Heridos: ${zona.heridos || 0}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-skull-crossbones"></i>
                    <span>Fallecidos: ${zona.fallecidos || 0}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-people-arrows"></i>
                    <span>Damnificados: ${zona.damnificados || 0}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-info-circle"></i>
                    <span>${zona.descripcion || 'Sin descripción'}</span>
                </div>
            </div>
            <div class="popup-actions">
                <button class="popup-btn mas-info" style="width:100%">
                    <i class="fas fa-clipboard-list"></i> Ver detalles
                </button>
            </div>
        </div>
    `;
}

function crearPopupDemanda(demanda) {
    const vulColor = demanda.vulnerabilidad > 0.7 ? '#dc3545' : 
                     demanda.vulnerabilidad > 0.4 ? '#ffc107' : '#28a745';
    
    return `
        <div class="popup-card">
            <div class="popup-header">
                <div class="popup-icon demanda"><i class="fas fa-users"></i></div>
                <span class="popup-title">${demanda.nombre}</span>
            </div>
            <div class="popup-body">
                <div class="popup-row">
                    <i class="fas fa-users"></i>
                    <span>Población: ${demanda.poblacion || 0}</span>
                </div>
                <div class="popup-row">
                    <i class="fas fa-shield-alt" style="color:${vulColor}"></i>
                    <span>Vulnerabilidad: ${Math.round(demanda.vulnerabilidad * 100)}%</span>
                </div>
            </div>
            <div class="popup-actions">
                <button class="popup-btn mas-info" style="width:100%">
                    <i class="fas fa-list"></i> Ver necesidades
                </button>
            </div>
        </div>
    `;
}

function comoLlegar(lat, lng) {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(pos) {
            const url = `https://www.openstreetmap.org/directions?from=${pos.coords.latitude},${pos.coords.longitude}&to=${lat},${lng}`;
            window.open(url, '_blank');
        }, function() {
            // Si no hay geolocalización, mostrar coordenadas
            alert(`Coordenadas del refugio: ${lat}, ${lng}`);
        });
    } else {
        alert(`Coordenadas del refugio: ${lat}, ${lng}`);
    }
}