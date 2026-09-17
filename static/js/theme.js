/**
 * Gestión exclusiva del modo oscuro/claro
 */
document.addEventListener('DOMContentLoaded', function() {
    const btnToggleTheme = document.getElementById('btn-toggle-theme');
    const iconTheme = document.getElementById('icon-theme');
    const htmlElement = document.documentElement;
    
    if (!btnToggleTheme || !iconTheme) return;
    
    function aplicarTema(tema) {
        htmlElement.setAttribute('data-theme', tema);
        localStorage.setItem('cobijo_theme', tema);
        
        if (tema === 'dark') {
            iconTheme.className = 'fas fa-sun';
            iconTheme.style.color = '#ffcc00';
            btnToggleTheme.setAttribute('title', 'Cambiar a modo claro');
        } else {
            iconTheme.className = 'fas fa-moon';
            iconTheme.style.color = 'white';
            btnToggleTheme.setAttribute('title', 'Cambiar a modo oscuro');
        }
    }
    
    // Cargar tema guardado o preferencia del sistema
    const temaGuardado = localStorage.getItem('cobijo_theme');
    if (temaGuardado) {
        aplicarTema(temaGuardado);
    } else {
        const prefiereOscuro = window.matchMedia('(prefers-color-scheme: dark)').matches;
        aplicarTema(prefiereOscuro ? 'dark' : 'light');
    }
    
    // Evento Click
    btnToggleTheme.addEventListener('click', function(e) {
        e.preventDefault();
        const temaActual = htmlElement.getAttribute('data-theme');
        const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
        aplicarTema(nuevoTema);
        
        // Avisar a Leaflet que cambie las capas
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: nuevoTema } }));
    });
});