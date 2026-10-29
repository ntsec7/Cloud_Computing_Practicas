document.getElementById('register-form').addEventListener('submit', async (e) => {
  
    // Si el pattern o el required no se cumplen, mostramos el mensaje nativo y paramos
  if (!form.checkValidity()) {
    e.preventDefault();
    form.reportValidity(); // Fuerza al navegador a mostrar el mensaje flotante del pattern
    return;
  }
  
  e.preventDefault();

  const username = document.getElementById('username').value.trim();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  const errorBadge = document.getElementById('error-message');
  const successBadge = document.getElementById('success-message');

  // Limpiar mensajes previos
  errorBadge.style.display = 'none';
  errorBadge.textContent = '';
  successBadge.style.display = 'none';
  successBadge.textContent = '';

  // Validación 1: Longitud mínima de contraseña
  if (password.length < 8) {
    errorBadge.textContent = "Password must have at least 8 characters.";
    errorBadge.style.display = 'block';
    return;
  }

  // Validación 2: Coincidencia de contraseñas
  if (password !== confirmPassword) {
    errorBadge.textContent = "The passwords doesn't match";
    errorBadge.style.display = 'block';
    return;
  }


  try {
    console.log("Enviando datos de registro:", { username, email, password });

    /* 
       Próximo paso: Aquí haremos la petición POST al Microservicio 2 (User & Stats):
       
       const response = await fetch('http://localhost:8002/api/users/register', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ username, email, password })
       });
    */

    //Mensaje de exito
    successBadge.textContent = "New account created successfully!";
    successBadge.style.display = 'block';

    //Redirige tras 1.5 segundos
    setTimeout(() => {
      window.location.href = 'login.html';
    }, 1500);

  } catch (error) {
    errorBadge.textContent = "Error connecting with the server.";
    errorBadge.style.display = 'block';
  }
});