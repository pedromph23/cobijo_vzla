document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const minimapContainer = document.getElementById('minimap-container');
    
    function handleResize() {
        if (window.innerWidth <= 768) {
            // Móvil: sidebar oculto por defecto
            sidebar.classList.remove('collapsed');
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
            
            // Minimapa más pequeño
            if (minimapContainer) {
                minimapContainer.style.width = '120px';
                minimapContainer.style.height = '90px';
            }
        } else {
            // Desktop: sidebar visible
            overlay.classList.remove('active');
            
            if (minimapContainer) {
                minimapContainer.style.width = '200px';
                minimapContainer.style.height = '150px';
            }
        }
    }
    
    window.addEventListener('resize', handleResize);
    handleResize();
});