// =========================
//  DROPDOWN GLOBAL USUARIO
// =========================

// Esta función se ejecuta UNA sola vez
document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('user-menu-root');

    if (!root) return; // La página no tiene menú de usuario → salir silenciosamente

    const btn = root.querySelector('#user-btn');
    const dropdown = root.querySelector('#user-dropdown');

    if (!btn || !dropdown) return;

    // --- Toggle del menú ---
    btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    // --- Evitar cierre al hacer clic dentro ---
    dropdown.addEventListener('click', e => e.stopPropagation());

    // --- Cerrar si el usuario hace clic fuera ---
    document.addEventListener('click', e => {
        if (!root.contains(e.target)) dropdown.classList.add('hidden');
    });

    // --- Cerrar con ESC ---
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') dropdown.classList.add('hidden');
    });
});


// =========================
//  CONTADOR DEL CARRITO
// =========================

document.addEventListener('DOMContentLoaded', () => {
    const cartBtn = document.getElementById('cart-btn');
    if (!cartBtn) return;

    console.log("Carrito inicializado (perfil.js)");
});


// =========================
//  MODAL DE CLAVES
// =========================

// Cerrar modal
function hideKeyModal() {
    const modal = document.getElementById('key-modal');
    if (!modal) return;

    modal.removeEventListener('click', _modalClickHandler);
    document.removeEventListener('keydown', _escKeyHandler);

    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');

    if (modal._autoCloseTimer) {
        clearTimeout(modal._autoCloseTimer);
        modal._autoCloseTimer = null;
    }
}

// Click externo para cerrar
function _modalClickHandler(e) {
    if (e.target && (e.target.dataset?.modalClose !== undefined || e.target.closest('[data-modal-close]'))) {
        hideKeyModal();
    }
}

// Escape para cerrar
function _escKeyHandler(e) {
    if (e.key === 'Escape') hideKeyModal();
}

// Log mínimo
function showTemporaryMessage(text, type = 'info') {
    console[type === 'error' ? 'error' : 'log'](text);
}

        function switchTab(tabId) {
            currentActiveTab = tabId;
            
            // 1. Quitar activo de todos los enlaces
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('tab-active');
            });

            document.getElementById('personal-info-form').style.display = 'none';
            document.getElementById('placeholder-content').style.display = 'none';

            // 2. Marcar el enlace actual como activo
            document.getElementById(`nav-${tabId}`).classList.add('tab-active');

            // 3. Renderizar contenido
            document.getElementById('placeholder-content').style.display = 'block';

            if (tabId === 'personal') {
                document.getElementById('personal-info-form').style.display = 'block';
                document.getElementById('placeholder-content').style.display = 'none';
                loadUserData(); 
                toggleEditMode(false); 
            } else if (tabId === 'payment') {
                document.getElementById('placeholder-content').innerHTML = renderPaymentMethods();
            } else if (tabId === 'security') { 
                document.getElementById('placeholder-content').innerHTML = renderSecurity();
            } else if (tabId === 'history') {
    if (!userData.purchaseHistory || userData.purchaseHistory.length === 0) {
        // Cargamos del servidor y luego renderizamos
        loadPurchaseHistory();
        // Ojo: como fetch es async, hacemos el render en el .then:
        fetch('/api/purchase-history/')
            .then(r => r.json())
            .then(json => {
                if (json.ok) {
                    userData.purchaseHistory = json.items || [];
                    document.getElementById('placeholder-content').innerHTML = renderPurchaseHistory();
                    attachKeyButtonListeners();
                } else {
                    showMessage('Error cargando historial', 'error');
                }
            })
            .catch(err => { console.error(err); showMessage('Error de red', 'error'); });
    } else {
        // Ya estaba cargado, solo pintamos
        document.getElementById('placeholder-content').innerHTML = renderPurchaseHistory();
        attachKeyButtonListeners();
    }
}
            
            lucide.createIcons();
        }

        // --- INICIALIZACIÓN ---

        window.addEventListener('load', function() {
            document.getElementById('personal-info-form').onsubmit = saveProfile;
            loadPaymentMethods();
            loadPurchaseHistory();  // ← Añadir esta línea
            switchTab('personal');
            
            document.addEventListener('click', (event) => {
                const modal = document.getElementById('key-modal');
                const modalContent = document.querySelector('#key-modal .modal-content');
                if (modal && modal.classList.contains('flex') && !modalContent.contains(event.target)) {
                    hideKeyModal();
                }
            });
            
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    hideKeyModal();
                }
            });
        });