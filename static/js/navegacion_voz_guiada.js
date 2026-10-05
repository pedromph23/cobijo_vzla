/**
 * Voz guiada de navegación para Cobijo VZLA.
 *
 * Se integra sobre la síntesis existente sin reemplazar el motor de rutas.
 * Modos:
 *   - full: todas las instrucciones habladas.
 *   - alerts: solo avisos de maniobra inmediata y llegada.
 *   - muted: no se reproduce voz.
 *
 * El control aparece automáticamente cuando se muestra el HUD de navegación.
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
        const icono = control.querySelector('i');
        const texto = control.querySelector('.nav-voz-label');
        control.setAttribute('aria-label', config.label);
        control.title = config.label;
        control.dataset.modo = modo;
        if (icono) icono.className = `fas ${config.icon}`;
        if (texto) texto.textContent = config.label;
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

    function crearControl() {
        if (control || !document.querySelector('.map-main-container')) return;

        control = document.createElement('button');
        control.type = 'button';
        control.className = 'nav-voz-control';
        control.innerHTML = '<i class="fas fa-volume-up" aria-hidden="true"></i><span class="nav-voz-label">Activar sonido</span><span class="nav-voz-chevron" aria-hidden="true"><i class="fas fa-chevron-down"></i></span>';
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
            #nav-hud { position: relative; }
            .nav-voz-control { position: relative; display:flex; align-items:center; gap:7px; min-height:38px; padding:8px 11px; border:1px solid rgba(255,255,255,.20); border-radius:12px; background:rgba(20,28,35,.86); color:#fff; cursor:pointer; box-shadow:0 6px 18px rgba(0,0,0,.18); backdrop-filter:blur(10px); font:inherit; }
            .nav-voz-control:hover { background:rgba(30,40,50,.96); transform:translateY(-1px); }
            .nav-voz-label { font-size:.78rem; font-weight:700; white-space:nowrap; }
            .nav-voz-chevron { font-size:.65rem; opacity:.7; }
            .nav-voz-menu { position:absolute; right:48px; top:calc(100% + 8px); min-width:190px; padding:6px; border:1px solid rgba(120,130,140,.25); border-radius:14px; background:var(--bg-card,#fff); color:var(--text-primary,#263238); box-shadow:0 16px 38px rgba(0,0,0,.22); z-index:1900; }
            .nav-voz-option { width:100%; display:grid; grid-template-columns:22px 1fr 18px; align-items:center; gap:8px; padding:10px 11px; border:0; border-radius:10px; background:transparent; color:inherit; text-align:left; cursor:pointer; font:inherit; }
            .nav-voz-option:hover, .nav-voz-option.active { background:rgba(100,120,140,.12); }
            .nav-voz-option .nav-voz-check { opacity:0; }
            .nav-voz-option.active .nav-voz-check { opacity:1; }
            @media (max-width:600px) { .nav-voz-label { display:none; } .nav-voz-control { width:42px; justify-content:center; padding:8px; } .nav-voz-menu { right:0; } }
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
        if (!hud) return;
        const sincronizar = () => {
            const visible = getComputedStyle(hud).display !== 'none' && !hud.hidden;
            if (visible) {
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
