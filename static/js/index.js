// Espera a que el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
  // Manejo de nombres de archivo para 'mensajes_file'
  const mensajesFileInput = document.getElementById('mensajes_file');
  const mensajesFilenameSpan = document.getElementById('mensajes-filename');

  if (mensajesFileInput && mensajesFilenameSpan) {
    mensajesFileInput.addEventListener('change', function(e) {
      const filename = e.target.files[0] ? e.target.files[0].name : 'Ningún archivo seleccionado';
      mensajesFilenameSpan.textContent = filename;
    });
  }

  // Manejo de nombres de archivo para 'data_file'
  const dataFileInput = document.getElementById('data_file');
  const dataFilenameSpan = document.getElementById('data-filename');

  if (dataFileInput && dataFilenameSpan) {
    dataFileInput.addEventListener('change', function(e) {
      const filename = e.target.files[0] ? e.target.files[0].name : 'Ningún archivo seleccionado';
      dataFilenameSpan.textContent = filename;
    });
  }

  // Manejo del botón de login
  const loginForm = document.getElementById('loginForm');
  const submitBtn = document.getElementById('submitBtn');

  if (loginForm && submitBtn) {
    loginForm.addEventListener('submit', function(e) {
      // Desactiva el botón y cambia su texto mientras se procesa el formulario
      submitBtn.classList.add('loading');
      submitBtn.textContent = '';
    });
  }
});