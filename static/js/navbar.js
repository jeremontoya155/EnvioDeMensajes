function toggleNav() {
    const sidebar = document.getElementById("mySidebar");
    const toggle = document.getElementById("toggle");
    
    if (sidebar.classList.contains('collapsed')) {
        // Abrir el menú lateral
        sidebar.classList.remove('collapsed');
        toggle.classList.remove('fa-bars');
        toggle.classList.add('fa-times');
    } else {
        // Cerrar el menú lateral
        sidebar.classList.add('collapsed');
        toggle.classList.remove('fa-times');
        toggle.classList.add('fa-bars');
    }
}