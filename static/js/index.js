
// Manejo de nombres de archivo
document.getElementById('mensajes_file').addEventListener('change', function(e) {
  const filename = e.target.files[0] ? e.target.files[0].name : 'Ningún archivo seleccionado';
  document.getElementById('mensajes-filename').textContent = filename;
});

document.getElementById('data_file').addEventListener('change', function(e) {
  const filename = e.target.files[0] ? e.target.files[0].name : 'Ningún archivo seleccionado';
  document.getElementById('data-filename').textContent = filename;
});

// Manejo del botón de login
document.getElementById('loginForm').addEventListener('submit', function(e) {
  const button = document.getElementById('submitBtn');
  button.classList.add('loading');
  button.textContent = '';

});
