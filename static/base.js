function isMobile() {
    return window.innerWidth <= 768;
}

function toggleSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const icon = document.getElementById('toggle-icon');

    // No mobile, o clique abre/fecha o drawer
    if (isMobile()) {
        if (sidebar.classList.contains('open')) {
            closeMobileSidebar();
        } else {
            openMobileSidebar();
        }
        return;
    }

    sidebar.classList.toggle('w-64');
    sidebar.classList.toggle('w-20');
    sidebar.classList.toggle('collapsed');

    // Gira o ícone
    if (sidebar.classList.contains('collapsed')) {
        icon.style.transform = 'rotate(180deg)';
    } else {
        icon.style.transform = 'rotate(0deg)';
    }
}

function openMobileSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}

// Fecha o drawer ao clicar num link de navegação (mobile)
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('#main-sidebar nav a').forEach(function(link) {
        link.addEventListener('click', function() {
            if (isMobile()) closeMobileSidebar();
        });
    });
});

/* === HELPERS GLOBAIS DE MODAIS === */

/**
 * Fecha um <dialog> pelo ID.
 * @param {string} id - ID do elemento dialog.
 */
function fecharModal(id) {
    const modal = document.getElementById(id);
    if (modal && typeof modal.close === 'function' && modal.open) {
        modal.close();
    }
}

/**
 * Fecha o modal ao clicar no backdrop (área escura fora do conteúdo).
 * Escuta cliques no próprio dialog, comparando as coordenadas.
 */
function fecharModalNoBackdrop(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            const rect = modal.getBoundingClientRect();
            const dentroHorizontal = event.clientX >= rect.left && event.clientX <= rect.right;
            const dentroVertical = event.clientY >= rect.top && event.clientY <= rect.bottom;
            if (!dentroHorizontal || !dentroVertical) {
                modal.close();
            }
        }
    });
}

// Auto-configura o fechamento por clique fora em todos os dialogs com a classe modal-config
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('dialog.modal-config').forEach(function(modal) {
        fecharModalNoBackdrop(modal.id);
    });
});

