document.addEventListener('DOMContentLoaded', function() {
    console.log('Panel admin cargado');
    inicializarPestanas();
    inicializarMapa();
    actualizarEstadisticas();
});

function inicializarPestanas() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');
            
            if (this.dataset.tab === 'reportes') cargarResultados();
            if (this.dataset.tab === 'datos') actualizarEstadisticas();
            if (this.dataset.tab === 'mapa') setTimeout(() => window.mapaAdmin && window.mapaAdmin.invalidateSize(), 100);
        });
    });
}

function inicializarMapa() {
    const div = document.getElementById('mapa-admin');
    if (!div || typeof L === 'undefined') return;
    
    window.mapaAdmin = L.map('mapa-admin', { center: [10.0, -66.0], zoom: 8 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(window.mapaAdmin);
    
    window.capasMapa = {
        demandas: L.layerGroup().addTo(window.mapaAdmin),
        candidatos: L.layerGroup().addTo(window.mapaAdmin),
        refugios: L.layerGroup().addTo(window.mapaAdmin),
        zonas: L.layerGroup().addTo(window.mapaAdmin)
    };
    
    cargarDatosMapa();
}

function cargarDatosMapa() {
    fetch('/api/datos-mapa/')
        .then(r => r.json())
        .then(data => {
            data.puntos_demanda.forEach(p => {
                if (p.lat) L.circleMarker([p.lat, p.lng], {radius: 5, color: '#0066cc'}).bindPopup(p.nombre).addTo(window.capasMapa.demandas);
            });
            data.sitios_candidatos.forEach(s => {
                if (s.lat) L.marker([s.lat, s.lng]).bindPopup(s.nombre).addTo(window.capasMapa.candidatos);
            });
            data.refugios.forEach(r => {
                if (r.lat) L.marker([r.lat, r.lng]).bindPopup(r.nombre).addTo(window.capasMapa.refugios);
            });
            data.zonas_afectadas.forEach(z => {
                if (z.geojson) {
                    try {
                        const g = JSON.parse(z.geojson);
                        if (g.type === 'Point') {
                            L.circle([g.coordinates[1], g.coordinates[0]], {radius: 1000, color: '#dc3545'}).bindPopup(z.nombre).addTo(window.capasMapa.zonas);
                        }
                    } catch(e) {}
                }
            });
        });
}

function actualizarEstadisticas() {
    fetch('/api/estadisticas/')
        .then(r => r.json())
        .then(data => {
            const map = {
                'stat-estados': data.estados,
                'stat-parroquias': data.parroquias,
                'stat-demandas': data.puntos_demanda,
                'stat-sitios': data.sitios_candidatos,
                'stat-refugios': data.refugios,
                'stat-zonas': data.zonas_afectadas
            };
            Object.keys(map).forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = map[id] || 0;
            });
        });
}

function cargarResultados() {
    fetch('/api/listar-resultados/')
        .then(r => r.json())
        .then(data => {
            const tbody = document.querySelector('#tabla-resultados tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            data.forEach(r => {
                tbody.innerHTML += `<tr><td>${r.id}</td><td>${r.fecha}</td><td>${r.escenario}</td><td>${r.resumen.distancia_total}km</td><td>${r.resumen.poblacion_atendida}</td><td>${r.resumen.porcentaje_cubierto}%</td></tr>`;
            });
        });
}

function generarReporte(tipo, contenido) {
    const msg = document.getElementById('mensaje-reporte');
    msg.style.display = 'block';
    msg.className = 'mensaje-reporte loading';
    msg.innerHTML = 'Generando...';
    
    fetch(`/api/reportes/generar/?tipo=${tipo}&contenido=${contenido}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                msg.className = 'mensaje-reporte success';
                msg.innerHTML = data.mensaje;
                window.open('/api/reportes/descargar/' + data.archivo + '/', '_blank');
            } else {
                msg.className = 'mensaje-reporte error';
                msg.innerHTML = data.error || 'Error';
            }
        })
        .catch(err => {
            msg.className = 'mensaje-reporte error';
            msg.innerHTML = err.message;
        });
}

window.generarReporte = generarReporte;
window.actualizarEstadisticas = actualizarEstadisticas;
window.cargarResultados = cargarResultados;