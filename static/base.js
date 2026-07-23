function toggleSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const icon = document.getElementById('toggle-icon');
    
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

