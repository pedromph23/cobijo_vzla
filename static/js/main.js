/**
 * Funciones comunes para toda la aplicación.
 */

/**
 * Inicializa un mapa Leaflet con soporte para tema oscuro
 */
function initMap(elementId, center = [10.0, -66.0], zoom = 8) {
    if (typeof L === 'undefined') {
        console.error('Leaflet no está cargado');
        return null;
    }
    
    const map = L.map(elementId, {
        center: center,
        zoom: zoom,
        zoomControl: true,
        fadeAnimation: true,
        zoomAnimation: true
    });
    
    // Capa base estándar
    const capaEstandar = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19
    });

    const capaOscura = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19,
        subdomains: 'abcd'
    });
    
    // Aplicar tema según preferencia
    const temaActual = document.documentElement.getAttribute('data-theme');
    if (temaActual === 'dark') {
        capaOscura.addTo(map);
    } else {
        capaEstandar.addTo(map);
    }
    
    // Escuchar cambios de tema
    document.addEventListener('themeChanged', function(e) {
        if (e.detail.theme === 'dark') {
            map.removeLayer(capaEstandar);
            capaOscura.addTo(map);
        } else {
            map.removeLayer(capaOscura);
            capaEstandar.addTo(map);
        }
    });
    
    // Guardar referencia a las capas
    map._capaEstandar = capaEstandar;
    map._capaOscura = capaOscura;
    
    return map;
}

/**
 * Agrega una capa de calor al mapa
 */
function addHeatLayer(map, data, options = {}) {
    if (typeof L === 'undefined' || !L.heatLayer) {
        console.error('Leaflet.heat no está cargado');
        return null;
    }
    
    const configuracion = {
        radius: options.radius || 25,
        blur: options.blur || 15,
        maxZoom: options.maxZoom || 10,
        max: options.max || 1.0,
        minOpacity: options.minOpacity || 0.1,
        gradient: options.gradient || {
            0.2: '#00ff00',
            0.4: '#ffff00',
            0.6: '#ff9900',
            0.8: '#ff3300',
            1.0: '#cc0000'
        }
    };
    
    const heatLayer = L.heatLayer(
        data.map(d => [d.lat, d.lng, d.intensidad || 0.5]),
        configuracion
    );
    
    heatLayer.addTo(map);
    return heatLayer;
}

/**
 * Alternar capa de calor
 */
function toggleHeatLayer(map, heatLayer, data) {
    if (heatLayer) {
        map.removeLayer(heatLayer);
        return null;
    }
    
    return addHeatLayer(map, data);
}

/**
 * Formatea un número según las convenciones venezolanas
 */
function formatNumber(num) {
    return new Intl.NumberFormat('es-VE').format(num || 0);
}

/**
 * Muestra un mensaje flotante
 */
function mostrarMensaje(texto, tipo = 'info') {
    let contenedor = document.getElementById('mensaje-flotante');
    
    if (!contenedor) {
        contenedor = document.createElement('div');
        contenedor.id = 'mensaje-flotante';
        contenedor.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            font-size: 0.9rem;
            transition: opacity 0.3s ease;
            max-width: 400px;
        `;
        document.body.appendChild(contenedor);
    }
    
    contenedor.textContent = texto;
    contenedor.style.opacity = '1';
    
    // Colores según tipo
    const colores = {
        success: '#28a745',
        error: '#dc3545',
        warning: '#ffc107',
        info: '#0066cc'
    };
    
    contenedor.style.backgroundColor = colores[tipo] || colores.info;
    contenedor.style.color = 'white';
    
    // Ocultar después de 5 segundos
    clearTimeout(contenedor._timeout);
    contenedor._timeout = setTimeout(() => {
        contenedor.style.opacity = '0';
    }, 5000);
}