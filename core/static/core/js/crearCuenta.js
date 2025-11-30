        // Inicializa los iconos de Lucide
        lucide.createIcons();

        const form = document.getElementById('signup-form');
        const feedbackEl = document.getElementById('feedback-message');

        // Función de alerta simulada (sustituye a alert())
        const alertSim = (message) => {
            const tempFeedback = document.createElement('div');
            tempFeedback.className = 'fixed bottom-4 right-4 p-3 rounded-lg shadow-lg bg-saga-red text-white transition-opacity duration-300';
            tempFeedback.textContent = message;
            document.body.appendChild(tempFeedback);
            setTimeout(() => tempFeedback.remove(), 3000);
        };
        window.alertSim = alertSim; // Exponer para el onclick

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // Obtener valores (simulación de registro)
            const firstName = document.getElementById('first-name').value;
            const lastName = document.getElementById('last-name').value;
            const country = document.getElementById('country').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            // Simple validación de datos
            if (password.length < 8) {
                feedbackEl.textContent = "La contraseña debe tener al menos 8 caracteres.";
                feedbackEl.classList.remove('hidden');
                feedbackEl.classList.add('bg-red-100', 'text-red-700');
                return;
            }

            // Simulación de envío exitoso
            feedbackEl.textContent = `¡Registro exitoso! Bienvenido(a) ${firstName} ${lastName} de ${country}.`;
            feedbackEl.classList.remove('hidden', 'bg-red-100', 'text-red-700');
            feedbackEl.classList.add('bg-green-100', 'text-green-700');
            
            form.reset();
            
            setTimeout(() => {
                feedbackEl.classList.add('hidden');
            }, 5000);
        });