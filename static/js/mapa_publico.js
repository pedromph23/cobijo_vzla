/**
 * Mapa Público - CobijoVzla
 * JavaScript optimizado para el mapa público interactivo
 */

let mapaPrincipal = null;
let minimapa = null;
let clusterRefugios = null;
let capaZonas = null;
let capaCalor = null;
let marcadorUbicacion = null;
let infoCard = null;
let debounceTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    inicializarMapa();
    inicializarMinimapa();
    configurarEventos();
    cargarDatos();
    
    // Forzar redibujado de Leaflet inicial para evitar áreas grises
    setTimeout(() => {
        if(mapaPrincipal) mapaPrincipal.invalidateSize();
    }, 500);
});

function inicializarMapa() {
    if (typeof L === 'undefined') return;
    
    mapaPrincipal = L.map('mapa', {
        center: [8.5, -66.0],
        zoom: 7,
        zoomControl: false,
        minZoom: 5,
        maxZoom: 18
    });
    
    L.control.zoom({ position: 'bottomright' }).addTo(mapaPrincipal);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19
        }).addTo(mapaPrincipal);
    
    clusterRefugios = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 50,
        iconCreateFunction: crearIconoCluster
    });
    mapaPrincipal.addLayer(clusterRefugios);
    
    capaZonas = L.layerGroup().addTo(mapaPrincipal);
}

function crearIconoCluster(cluster) {
    const count = cluster.getChildCount();
    let color = count < 10 ? '#28a745' : count < 50 ? '#ffc107' : '#dc3545';
    
    return L.divIcon({
        html: `<div style="background:${color};border-radius:50%;width:45px;height:45px;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;border:3px solid white;box-shadow:0 2px 10px rgba(0,0,0,0.4);">${count}</div>`,
        className: 'cluster-personalizado',
        iconSize: L.point(45, 45),
        iconAnchor: L.point(22, 22)
    });
}

function crearMarcadorRefugio(refugio) {
    const color = refugio.operativo ? '#0066cc' : '#6c757d';
    const icono = L.divIcon({
        html: `<div style="background:${color};border-radius:50%;width:35px;height:35px;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);"><i class="fas fa-home" style="color:white;font-size:14px;"></i></div>`,
        className: 'marcador-refugio',
        iconSize: [35, 35],
        iconAnchor: [17, 17]
    });
    
    const marker = L.marker([refugio.lat, refugio.lng], { icon: icono });
    
    marker.on('click', function() {
        const servicios = Array.isArray(refugio.servicios) ? refugio.servicios.join(', ') : 'No especificados';
        const contenido = `
            <div style="margin-bottom:8px;"><strong><i class="fas fa-map-marker-alt"></i> Dirección:</strong> ${refugio.direccion || 'No disponible'}</div>
            <div style="margin-bottom:8px;"><strong><i class="fas fa-users"></i> Capacidad:</strong> ${refugio.capacidad_disponible}/${refugio.capacidad_total} disponibles</div>
            <div style="margin-bottom:8px;"><strong><i class="fas fa-concierge-bell"></i> Servicios:</strong> ${servicios}</div>
            <div style="margin-bottom:8px;"><strong><i class="fas fa-phone"></i> Teléfono:</strong> ${refugio.telefono || 'No disponible'}</div>
            <div><strong><i class="fas fa-circle"></i> Estado:</strong> <span style="color:${refugio.operativo ? '#28a745' : '#dc3545'};">${refugio.operativo ? '✅ Operativo' : '❌ No operativo'}</span></div>
        `;
        mostrarInfoCard(`<i class="fas fa-home"></i> ${refugio.nombre}`, contenido);
    });
    
    return marker;
}

function inicializarMinimapa() {
    if (!document.getElementById('minimap') || !mapaPrincipal) return;
    
    minimapa = L.map('minimap', {
        center: [8.5, -66.0], zoom: 5, zoomControl: false, attributionControl: false, dragging: true, scrollWheelZoom: false
    });
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19
        }).addTo(minimapa);
    
    mapaPrincipal.on('move', () => {
        if (minimapa) minimapa.setView(mapaPrincipal.getCenter(), Math.max(4, mapaPrincipal.getZoom() - 3));
    });
    minimapa.on('click', (e) => mapaPrincipal.setView(e.latlng, mapaPrincipal.getZoom()));
}

function configurarEventos() {
    // Pantalla Completa
    document.getElementById('btn-expandir-mapa')?.addEventListener('click', function() {
        const mapLayout = document.querySelector('.map-layout');
        const icono = this.querySelector('i');
        
        mapLayout.classList.toggle('map-fullscreen');
        
        if (mapLayout.classList.contains('map-fullscreen')) {
            icono.classList.replace('fa-expand', 'fa-compress');
            this.title = 'Reducir mapa';
            document.body.style.overflow = 'hidden';
        } else {
            icono.classList.replace('fa-compress', 'fa-expand');
            this.title = 'Expandir mapa';
            document.body.style.overflow = '';
        }
        
        setTimeout(() => { if(mapaPrincipal) mapaPrincipal.invalidateSize(); }, 400);
    });

    // Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    document.getElementById('btn-toggle-sidebar')?.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.innerWidth > 768) {
            sidebar.classList.toggle('collapsed');
        } else {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        }
        setTimeout(() => { if(mapaPrincipal) mapaPrincipal.invalidateSize(); }, 400);
    });
    
    document.getElementById('btn-close-sidebar')?.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    });
    
    overlay?.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    });

    // Botones Varios
    document.getElementById('btn-close-minimap')?.addEventListener('click', () => {
        document.getElementById('minimap-container').style.display = 'none';
    });
    
    document.getElementById('btn-expand-minimap')?.addEventListener('click', () => {
        document.getElementById('minimap-container').classList.toggle('expanded');
        setTimeout(() => { minimapa?.invalidateSize(); mapaPrincipal?.invalidateSize(); }, 300);
    });
    
    document.getElementById('btn-minimapa-toggle')?.addEventListener('click', () => {
        const c = document.getElementById('minimap-container');
        c.style.display = c.style.display === 'none' ? 'block' : 'none';
    });
    
    document.getElementById('btn-vista-general')?.addEventListener('click', () => {
        mapaPrincipal?.flyTo([8.5, -66.0], 7, { duration: 1.5 });
    });
    
    infoCard = document.getElementById('info-card');
    document.getElementById('info-card-close')?.addEventListener('click', () => {
        if (infoCard) infoCard.style.display = 'none';
    });

    // Checkboxes
    document.getElementById('chk-refugios')?.addEventListener('change', function() {
        if (this.checked) mapaPrincipal.addLayer(clusterRefugios); else mapaPrincipal.removeLayer(clusterRefugios);
    });
    
    document.getElementById('chk-zonas')?.addEventListener('change', function() {
        if (this.checked) mapaPrincipal.addLayer(capaZonas); else mapaPrincipal.removeLayer(capaZonas);
    });
    
    document.getElementById('chk-calor')?.addEventListener('change', function() {
        if (this.checked) {
            fetch('/api/publico/mapa-calor/')
                .then(r => r.json())
                .then(data => {
                    if (data.length > 0) {
                        capaCalor = L.heatLayer(data.map(d => [d.lat, d.lng, d.intensidad || 0.5]), { radius: 30, blur: 20, maxZoom: 10, minOpacity: 0.3, gradient: {0.2: 'lime', 0.5: 'yellow', 1.0: 'red'} });
                        capaCalor.addTo(mapaPrincipal);
                    }
                });
        } else if (capaCalor) {
            mapaPrincipal.removeLayer(capaCalor);
            capaCalor = null;
        }
    });

    // Búsqueda
    const inputBuscar = document.getElementById('buscar');
    const sugerencias = document.getElementById('sugerencias');
    
    inputBuscar?.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        if (query.length < 2) { sugerencias.style.display = 'none'; return; }
        
        debounceTimer = setTimeout(() => {
            fetch(`/api/publico/buscar-lugar/?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    sugerencias.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'sugerencia-item';
                            div.innerHTML = `<i class="fas fa-map-marker-alt"></i> ${item.nombre} <small>(${item.estado})</small>`;
                            div.addEventListener('click', () => {
                                inputBuscar.value = item.nombre;
                                sugerencias.style.display = 'none';
                                mapaPrincipal.flyTo([item.lat, item.lng], 12);
                            });
                            sugerencias.appendChild(div);
                        });
                        sugerencias.style.display = 'block';
                    }
                });
        }, 300);
    });

    // Geolocalización
    document.getElementById('btn-geolocalizar')?.addEventListener('click', function() {
        if (!navigator.geolocation) return alert('Geolocalización no soportada');
        
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Obteniendo...';
        navigator.geolocation.getCurrentPosition(pos => {
            if (marcadorUbicacion) mapaPrincipal.removeLayer(marcadorUbicacion);
            marcadorUbicacion = L.marker([pos.coords.latitude, pos.coords.longitude], {
                icon: L.divIcon({ html: '<div style="background:#0066cc;border-radius:50%;width:20px;height:20px;border:4px solid white;"></div>', className: 'marcador-ubicacion' })
            }).addTo(mapaPrincipal).bindPopup('📍 Usted está aquí').openPopup();
            mapaPrincipal.flyTo([pos.coords.latitude, pos.coords.longitude], 15);
            this.innerHTML = '<i class="fas fa-location-arrow"></i> Usar mi ubicación';
        }, () => {
            this.innerHTML = '<i class="fas fa-location-arrow"></i> Usar mi ubicación';
            alert('Error al obtener ubicación');
        });
    });
}

function mostrarInfoCard(titulo, contenido) {
    if (!infoCard) return;
    document.getElementById('info-card-title').innerHTML = titulo;
    document.getElementById('info-card-body').innerHTML = contenido;
    infoCard.style.display = 'block';
}

function cargarDatos() {
    // Refugios
    fetch('/api/publico/refugios/').then(r => r.json()).then(data => {
        const count = document.getElementById('count-refugios');
        if (count) count.textContent = data.length;
        data.forEach(ref => { if(ref.lat && ref.lng) clusterRefugios.addLayer(crearMarcadorRefugio(ref)); });
    });
    
    // Zonas
    fetch('/api/publico/zonas-afectadas/').then(r => r.json()).then(data => {
        const count = document.getElementById('count-zonas');
        if (count) count.textContent = data.length;
        data.forEach(zona => {
            if(zona.lat && zona.lng) {
                const color = zona.nivel_alerta === 'alto' ? '#dc3545' : zona.nivel_alerta === 'medio' ? '#ffc107' : '#28a745';
                const circle = L.circle([zona.lat, zona.lng], { radius: 800, color: color, fillColor: color, fillOpacity: 0.35, weight: 2 });
                circle.on('click', () => mostrarInfoCard(`<i class="fas fa-exclamation-triangle"></i> ${zona.nombre}`, `
                    <div style="margin-bottom:8px;"><strong>Alerta:</strong> <span style="color:${color}">${zona.nivel_alerta.toUpperCase()}</span></div>
                    <div style="margin-bottom:8px;"><strong>Heridos:</strong> ${zona.heridos || 0}</div>
                    <div style="margin-bottom:8px;"><strong>Fallecidos:</strong> ${zona.fallecidos || 0}</div>
                    <div style="margin-bottom:8px;"><strong>Damnificados:</strong> ${zona.damnificados || 0}</div>
                    <div><strong>Descripción:</strong> ${zona.descripcion || 'Sin descripción'}</div>
                `));
                circle.addTo(capaZonas);
            }
        });
    });
}