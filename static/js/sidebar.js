document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const btnToggle = document.getElementById('btn-toggle-sidebar');
    const btnClose = document.getElementById('btn-close-sidebar');
    
    // Abrir/Cerrar sidebar
    if (btnToggle) {
        btnToggle.addEventListener('click', function(e) {
            e.preventDefault();
            if (!sidebar) return;
            
            if (window.innerWidth > 768) {
                sidebar.classList.toggle('collapsed');
            } else {
                sidebar.classList.toggle('open');
                if (overlay) overlay.classList.toggle('active');
            }
            
            // Forzar al mapa a recalcular su tamaño al mover el menú
            setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 300);
        });
    }
    
    // Botón X para cerrar en móvil
    if (btnClose) {
        btnClose.addEventListener('click', function() {
            if (sidebar) sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
        });
    }
    
    // Cerrar al hacer clic en el fondo oscuro
    if (overlay) {
        overlay.addEventListener('click', function() {
            if (sidebar) sidebar.classList.remove('open');
            this.classList.remove('active');
        });
    }
});