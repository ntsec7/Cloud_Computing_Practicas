document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const errorBadge = document.getElementById('error-message');

  try {
    // Aquí se hace petición fetch al Microservicio de Login
    console.log("Intentando iniciar sesión con:", { username, password });

    // Simulación temporal hasta conectar con el backend:
    if (username && password) {
      localStorage.setItem('currentUser', username);
      window.location.href = 'game.html'; // Redirige a la pantalla de juego
    }
  } catch (error) {
    errorBadge.textContent = "Error connecting with the server.";
    errorBadge.style.display = 'block';
  }
});