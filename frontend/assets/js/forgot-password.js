document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os ícones do Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const formForgotPassword = document.getElementById('formForgotPassword');

    formForgotPassword.addEventListener('submit', (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();

        if (email) {
            console.log('Enviando link de redefinição para:', email);
            alert(`Link de recuperação enviado para ${email}!`);
        }
    });
});