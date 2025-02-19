
// Supongamos que estos son tus datos reales
const mensajes = [
  {
    fecha: '2025-01-01',
    destinatario: 'Juan',
    mensaje: 'Hola Juan',
    likes: 2,
  },
  {
    fecha: '2025-01-01',
    destinatario: 'Ana',
    mensaje: 'Hola Ana',
    likes: 5,
  },
  {
    fecha: '2025-01-02',
    destinatario: 'Pedro',
    mensaje: 'Hola Pedro',
    likes: 3,
  },
  {
    fecha: '2025-01-03',
    destinatario: 'Juan',
    mensaje: 'Otra vez Juan',
    likes: 4,
  },
  {
    fecha: '2025-01-04',
    destinatario: 'Ana',
    mensaje: 'Otra vez Ana',
    likes: 1,
  },
  {
    fecha: '2025-01-05',
    destinatario: 'Pedro',
    mensaje: 'Otra vez Pedro',
    likes: 0,
  },
  {
    fecha: '2025-01-06',
    destinatario: 'Juan',
    mensaje: 'Otra más para Juan',
    likes: 6,
  },
];

// Generar HTML para los likes
function generarLikes() {
  const likesContainer = document.getElementById('likesContainer');
  mensajes.forEach((mensaje, index) => {
    const likeHTML = `
      <div class="like-container">
        <p>${mensaje.mensaje}</p>
        <button onclick="agregarLike(${index})">
          <span id="like-count-${index}">${mensaje.likes}</span> ❤️
        </button>
      </div>
    `;
    likesContainer.innerHTML += likeHTML;
  });
}

// Incrementar contador de me gustas
function agregarLike(index) {
  mensajes[index].likes++;
  document.getElementById(`like-count-${index}`).textContent =
    mensajes[index].likes;
}

// Llamar a la función de generar likes
generarLikes();

// 1. Agrupar mensajes por fecha para el gráfico de evolución
const mensajesPorFecha = {};
mensajes.forEach((mensaje) => {
  const fecha = mensaje.fecha;
  mensajesPorFecha[fecha] = (mensajesPorFecha[fecha] || 0) + 1;
});

// Preparar datos para el gráfico de mensajes enviados por fecha
const fechas = Object.keys(mensajesPorFecha);
const cantidadMensajes = Object.values(mensajesPorFecha);

const mensajesPorUsuario = mensajes.reduce((acc, mensaje) => {
  acc[mensaje.destinatario] = (acc[mensaje.destinatario] || 0) + 1;
  return acc;
}, {});

const totalMensajesPorUsuario = Object.entries(mensajesPorUsuario)
  .map(([usuario, total]) => `${usuario}: ${total} mensajes`)
  .join('<br>');
document.getElementById('totalMensajesPorUsuario').innerHTML =
  totalMensajesPorUsuario;

const fechaPrimerMensaje = mensajes.sort(
  (a, b) => new Date(a.fecha) - new Date(b.fecha)
)[0].fecha;
document.getElementById('fechaPrimerMensaje').textContent =
  fechaPrimerMensaje;

const promedioLikes =
  mensajes.reduce((sum, mensaje) => sum + mensaje.likes, 0) /
  mensajes.length;
document.getElementById('promedioLikesPorMensaje').textContent =
  promedioLikes.toFixed(2);
const usuarioMasMensajes = Object.entries(mensajesPorUsuario).reduce(
  (max, [usuario, total]) => {
    return total > max.total ? { usuario, total } : max;
  },
  { usuario: '', total: 0 }
);
document.getElementById(
  'usuarioMasMensajes'
).textContent = `${usuarioMasMensajes.usuario} (${usuarioMasMensajes.total} mensajes)`;
const likesPorUsuario = mensajes.reduce((acc, mensaje) => {
  acc[mensaje.destinatario] =
    (acc[mensaje.destinatario] || 0) + mensaje.likes;
  return acc;
}, {});

const usuarioMasLikes = Object.entries(likesPorUsuario).reduce(
  (max, [usuario, total]) => {
    return total > max.total ? { usuario, total } : max;
  },
  { usuario: '', total: 0 }
);

document.getElementById(
  'usuarioMasLikes'
).textContent = `${usuarioMasLikes.usuario} (${usuarioMasLikes.total} likes)`;
const mensajesPorDia = mensajes.reduce((acc, mensaje) => {
  acc[mensaje.fecha] = (acc[mensaje.fecha] || 0) + 1;
  return acc;
}, {});

const diaMasMensajes = Object.entries(mensajesPorDia).reduce(
  (max, [fecha, total]) => {
    return total > max.total ? { fecha, total } : max;
  },
  { fecha: '', total: 0 }
);

document.getElementById(
  'diaMasMensajes'
).textContent = `${diaMasMensajes.fecha} (${diaMasMensajes.total} mensajes)`;

// 2. Crear gráfico de evolución de mensajes enviados
const ctx1 = document
  .getElementById('mensajesEnviados-chart')
  .getContext('2d');
new Chart(ctx1, {
  type: 'line',
  data: {
    labels: fechas,
    datasets: [
      {
        label: 'Mensajes enviados',
        data: cantidadMensajes,
        backgroundColor: 'rgba(76, 175, 145, 0.2)',
        borderColor: '#4caf91',
        borderWidth: 2,
        tension: 0.1,
      },
    ],
  },
});

// 3. Crear gráfico de destinatarios
const mensajesPorDestinatario = {};
mensajes.forEach((mensaje) => {
  const destinatario = mensaje.destinatario;
  mensajesPorDestinatario[destinatario] =
    (mensajesPorDestinatario[destinatario] || 0) + 1;
});

const destinatarios = Object.keys(mensajesPorDestinatario);
const cantidadPorDestinatario = Object.values(mensajesPorDestinatario);

const ctx2 = document
  .getElementById('destinatarios-chart')
  .getContext('2d');
new Chart(ctx2, {
  type: 'bar',
  data: {
    labels: destinatarios,
    datasets: [
      {
        label: 'Mensajes por destinatario',
        data: cantidadPorDestinatario,
        backgroundColor: '#4caf91',
        borderColor: '#4caf91',
        borderWidth: 2,
      },
    ],
  },
});

// 4. Crear gráfico de distribución de me gustas
const likesPorMensaje = mensajes.map((mensaje) => mensaje.likes);
const ctx3 = document.getElementById('meGustas-chart').getContext('2d');
new Chart(ctx3, {
  type: 'bar',
  data: {
    labels: mensajes.map((mensaje, index) => `Mensaje ${index + 1}`),
    datasets: [
      {
        label: 'Me gustas',
        data: likesPorMensaje,
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 2,
      },
    ],
  },
});
