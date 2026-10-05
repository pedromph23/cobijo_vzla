/**
 * Voz guiada + HUD GPS de navegación para Cobijo VZLA.
 * Se integra sobre la navegación existente sin reemplazar rutas,
 * geolocalización, instrucciones ni GeoGuard.
 */
(() => {
    'use strict';

    const STORAGE_KEY = 'cobijo:navegacion:voz-modo';
    const MODOS = {
        full: { label: 'Activar sonido', icon: 'fa-volume-up' },
        alerts: { label: 'Solo alertas', icon: 'fa-bell' },
        muted: { label: 'Silenciar', icon: 'fa-volume-mute' },
    };

    let modo = localStorage.getItem(STORAGE_KEY) || 'full';
    if (!MODOS[modo]) modo = 'full';
    let control = null;
    let menu = null;
    let speakOriginal = null;
    let hudObservado = false;

    function esAlerta(texto) {
        const valor = String(texto || '').toLowerCase().trim();
        if (!valor) return false;
        return /\b(ahora|gire|girar|realice un cambio de sentido|en\s+\d+\s*(metros?|m)|ha llegado|destino|llegado al punto)\b/i.test(valor);
    }

    function permitirVoz(texto) {
        if (modo === 'muted') return false;
        if (modo === 'alerts') return esAlerta(texto);
        return true;
    }

    function actualizarControl() {
        if (!control) return;
        const config = MODOS[modo];
        const icono = control.querySelector('.nav-voz-icon');
        const texto = control.querySelector('.nav-voz-label');
        control.setAttribute('aria-label', config.label);
        control.title = config.label;
        control.dataset.modo = modo;
        if (icono) icono.className = `fas ${config.icon} nav-voz-icon`;
        if (texto) texto.textContent = config.label;
        actualizarEstadoGPS();
    }

    function actualizarEstadoGPS() {
        const estado = document.getElementById('nav-gps-status');
        if (!estado) return;
        estado.className = 'nav-gps-status ' + modo;
        const icon = estado.querySelector('i');
        const texto = estado.querySelector('span');
        if (icon) icon.className = `fas ${MODOS[modo].icon}`;
        if (texto) texto.textContent = modo === 'full' ? 'Voz activa' : modo === 'alerts' ? 'Solo alertas' : 'Voz silenciada';
    }

    function cerrarMenu() {
        if (menu) menu.hidden = true;
        control?.setAttribute('aria-expanded', 'false');
    }

    function seleccionarModo(nuevoModo) {
        if (!MODOS[nuevoModo]) return;
        modo = nuevoModo;
        localStorage.setItem(STORAGE_KEY, modo);
        actualizarControl();
        cerrarMenu();
        if (modo === 'muted' && window.speechSynthesis) window.speechSynthesis.cancel();
    }

    function prepararHud() {
        const hud = document.getElementById('nav-hud');
        if (!hud || hud.dataset.gpsReady === 'true') return;
        hud.dataset.gpsReady = 'true';
        hud.classList.add('nav-hud-gps');

        const estado = document.createElement('div');
        estado.id = 'nav-gps-status';
        estado.className = 'nav-gps-status';
        estado.innerHTML = '<i class="fas fa-volume-up" aria-hidden="true"></i><span>Voz activa</span>';
        hud.prepend(estado);

        const etiqueta = document.createElement('div');
        etiqueta.className = 'nav-gps-live';
        etiqueta.innerHTML = '<span class="nav-gps-dot" aria-hidden="true"></span><span>NAVEGANDO</span>';
        hud.prepend(etiqueta);

        const barra = document.createElement('div');
        barra.className = 'nav-gps-progress';
        barra.innerHTML = '<span></span>';
        hud.appendChild(barra);

        actualizarEstadoGPS();
    }

    function crearControl() {
        if (control || !document.querySelector('.map-main-container')) return;

        control = document.createElement('button');
        control.type = 'button';
        control.className = 'nav-voz-control';
        control.innerHTML = '<i class="fas fa-volume-up nav-voz-icon" aria-hidden="true"></i><span class="nav-voz-label">Activar sonido</span><span class="nav-voz-chevron" aria-hidden="true"><i class="fas fa-chevron-down"></i></span>';
        control.setAttribute('aria-haspopup', 'true');
        control.setAttribute('aria-expanded', 'false');

        menu = document.createElement('div');
        menu.className = 'nav-voz-menu';
        menu.hidden = true;
        menu.setAttribute('role', 'menu');

        Object.entries(MODOS).forEach(([clave, config]) => {
            const opcion = document.createElement('button');
            opcion.type = 'button';
            opcion.className = 'nav-voz-option';
            opcion.dataset.modo = clave;
            opcion.setAttribute('role', 'menuitemradio');
            opcion.innerHTML = `<i class="fas ${config.icon}" aria-hidden="true"></i><span>${config.label}</span><i class="fas fa-check nav-voz-check" aria-hidden="true"></i>`;
            opcion.addEventListener('click', () => seleccionarModo(clave));
            menu.appendChild(opcion);
        });

        control.addEventListener('click', (evento) => {
            evento.stopPropagation();
            menu.hidden = !menu.hidden;
            control.setAttribute('aria-expanded', String(!menu.hidden));
            menu.querySelectorAll('.nav-voz-option').forEach((opcion) => {
                const activo = opcion.dataset.modo === modo;
                opcion.classList.toggle('active', activo);
                opcion.setAttribute('aria-checked', String(activo));
            });
        });

        document.addEventListener('click', (evento) => {
            if (menu && !menu.hidden && !menu.contains(evento.target) && evento.target !== control && !control.contains(evento.target)) cerrarMenu();
        });

        const hud = document.getElementById('nav-hud');
        if (hud) {
            hud.appendChild(control);
            hud.appendChild(menu);
        }

        actualizarControl();
    }

    function instalarEstilos() {
        if (document.getElementById('nav-voz-guiada-styles')) return;
        const style = document.createElement('style');
        style.id = 'nav-voz-guiada-styles';
        style.textContent = `
            #nav-hud.nav-hud-gps { position:absolute; left:50%; top:18px; transform:translateX(-50%); width:min(680px,calc(100% - 32px)); min-height:96px; box-sizing:border-box; display:grid; grid-template-columns:52px minmax(0,1fr) auto auto; grid-template-rows:auto auto; gap:8px 12px; align-items:center; padding:12px 14px 14px; border:1px solid rgba(255,255,255,.18); border-radius:20px; background:linear-gradient(135deg,rgba(19,30,39,.96),rgba(31,47,58,.93)); color:#fff; box-shadow:0 14px 38px rgba(0,0,0,.30),0 3px 12px rgba(0,0,0,.18); backdrop-filter:blur(16px); z-index:1200; overflow:visible; }
            #nav-hud.nav-hud-gps .nav-gps-live { position:absolute; top:-11px; left:18px; display:flex; align-items:center; gap:6px; padding:4px 9px; border-radius:999px; background:rgba(24,142,91,.96); color:#fff; font-size:.62rem; font-weight:800; letter-spacing:.08em; box-shadow:0 4px 12px rgba(0,0,0,.18); }
            .nav-gps-dot { width:6px; height:6px; border-radius:50%; background:#fff; box-shadow:0 0 0 3px rgba(255,255,255,.18); animation:navGpsPulse 1.6s infinite; }
            @keyframes navGpsPulse { 0%,100%{opacity:1} 50%{opacity:.45} }
            #nav-hud.nav-hud-gps .nav-hud-icon { grid-column:1; grid-row:1 / span 2; width:52px; height:52px; display:flex; align-items:center; justify-content:center; border-radius:16px; background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.12); color:#fff; font-size:1.35rem; }
            #nav-hud.nav-hud-gps .nav-hud-content { grid-column:2; grid-row:1 / span 2; min-width:0; padding:0; }
            #nav-hud.nav-hud-gps .nav-hud-instruction { font-size:clamp(.9rem,2vw,1.05rem); font-weight:800; line-height:1.25; max-height:2.7em; overflow:hidden; text-overflow:ellipsis; }
            #nav-hud.nav-hud-gps .nav-hud-meta { display:flex; flex-wrap:wrap; gap:5px 14px; margin-top:7px; color:rgba(255,255,255,.78); font-size:.73rem; }
            #nav-hud.nav-hud-gps .nav-hud-meta span { display:inline-flex; align-items:center; gap:5px; }
            #nav-hud.nav-hud-gps .nav-hud-meta strong { color:#fff; }
            #nav-hud.nav-hud-gps .nav-hud-btn { width:38px; height:38px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(255,255,255,.14); border-radius:11px; background:rgba(255,255,255,.09); color:#fff; cursor:pointer; transition:transform .18s ease,background .18s ease; }
            #nav-hud.nav-hud-gps .nav-hud-btn:hover { background:rgba(255,255,255,.17); transform:translateY(-1px); }
            #nav-hud.nav-hud-gps .nav-hud-btn-close { grid-column:4; grid-row:1; }
            #nav-hud.nav-hud-gps .nav-voz-control { grid-column:3; grid-row:1; position:relative; display:flex; align-items:center; gap:7px; min-height:38px; padding:8px 10px; border:1px solid rgba(255,255,255,.14); border-radius:11px; background:rgba(255,255,255,.09); color:#fff; cursor:pointer; font:inherit; box-shadow:none; }
            #nav-hud.nav-hud-gps .nav-voz-control:hover { background:rgba(255,255,255,.17); }
            .nav-voz-label { font-size:.72rem; font-weight:800; white-space:nowrap; }
            .nav-voz-chevron { font-size:.58rem; opacity:.7; }
            .nav-gps-status { display:none; }
            #nav-hud.nav-hud-gps .nav-gps-status { display:flex; align-items:center; gap:6px; grid-column:3; grid-row:2; justify-content:center; font-size:.62rem; font-weight:700; color:rgba(255,255,255,.72); }
            #nav-hud.nav-hud-gps .nav-gps-status.full { color:#9ee8c5; }
            #nav-hud.nav-hud-gps .nav-gps-status.alerts { color:#ffe3a0; }
            #nav-hud.nav-hud-gps .nav-gps-status.muted { color:#ffb5b5; }
            #nav-hud.nav-hud-gps .nav-gps-progress { position:absolute; left:14px; right:14px; bottom:5px; height:3px; overflow:hidden; border-radius:999px; background:rgba(255,255,255,.10); }
            #nav-hud.nav-hud-gps .nav-gps-progress span { display:block; width:38%; height:100%; border-radius:inherit; background:rgba(255,255,255,.65); animation:navGpsProgress 2.4s ease-in-out infinite; }
            @keyframes navGpsProgress { 0%{transform:translateX(-120%)} 100%{transform:translateX(280%)} }
            .nav-voz-menu { position:absolute; right:48px; top:calc(100% + 8px); min-width:190px; padding:6px; border:1px solid rgba(120,130,140,.25); border-radius:14px; background:var(--bg-card,#fff); color:var(--text-primary,#263238); box-shadow:0 16px 38px rgba(0,0,0,.22); z-index:1900; }
            .nav-voz-option { width:100%; display:grid; grid-template-columns:22px 1fr 18px; align-items:center; gap:8px; padding:10px 11px; border:0; border-radius:10px; background:transparent; color:inherit; text-align:left; cursor:pointer; font:inherit; }
            .nav-voz-option:hover, .nav-voz-option.active { background:rgba(100,120,140,.12); }
            .nav-voz-option .nav-voz-check { opacity:0; }
            .nav-voz-option.active .nav-voz-check { opacity:1; }
            @media (max-width:700px) {
                #nav-hud.nav-hud-gps { top:10px; width:calc(100% - 20px); grid-template-columns:46px minmax(0,1fr) 38px 38px; gap:7px; padding:11px 10px 13px; border-radius:17px; }
                #nav-hud.nav-hud-gps .nav-hud-icon { width:46px; height:46px; border-radius:13px; }
                #nav-hud.nav-hud-gps .nav-hud-meta { gap:4px 9px; font-size:.68rem; }
                #nav-hud.nav-hud-gps .nav-voz-control { width:38px; height:38px; min-height:38px; padding:0; justify-content:center; }
                #nav-hud.nav-hud-gps .nav-voz-label, #nav-hud.nav-hud-gps .nav-voz-chevron { display:none; }
                #nav-hud.nav-hud-gps .nav-gps-status { grid-column:3; }
                #nav-hud.nav-hud-gps .nav-hud-btn-close { grid-column:4; }
                .nav-voz-menu { right:0; }
            }
        `;
        document.head.appendChild(style);
    }

    function instalarInterceptadorVoz() {
        if (!window.speechSynthesis?.speak || speakOriginal) return;
        speakOriginal = window.speechSynthesis.speak.bind(window.speechSynthesis);
        window.speechSynthesis.speak = function (utterance) {
            const texto = utterance && typeof utterance.text === 'string' ? utterance.text : '';
            if (!permitirVoz(texto)) return;
            return speakOriginal(utterance);
        };
    }

    function observarHud() {
        const hud = document.getElementById('nav-hud');
        if (!hud || hudObservado) return;
        hudObservado = true;
        const sincronizar = () => {
            const visible = getComputedStyle(hud).display !== 'none' && !hud.hidden;
            if (visible) {
                prepararHud();
                crearControl();
                actualizarControl();
            } else if (menu) {
                cerrarMenu();
            }
        };
        new MutationObserver(sincronizar).observe(hud, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
        sincronizar();
    }

    function instalar() {
        instalarEstilos();
        instalarInterceptadorVoz();
        observarHud();
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', instalar, { once: true });
    else instalar();
})();
