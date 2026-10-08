import { comCarregamento } from './notifications.js';
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        lucide.createIcons();
    }

    const requestForm = document.getElementById('formForgotPassword');
    const resetForm = document.getElementById('formResetPassword');
    let email = '';

    requestForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const feedback = document.getElementById('forgotFeedback');
        const button = requestForm.querySelector('button[type="submit"]');
        email = document.getElementById('email').value.trim().toLowerCase();
        feedback.textContent = '';
        await comCarregamento(button, async () => {
        try {
            const response = await fetch(`${window.location.origin}/api/solicitar-codigo-recuperacao`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.erro || 'Não foi possível solicitar o código.');

            requestForm.hidden = true;
            resetForm.hidden = false;
            document.getElementById('resetFeedback').textContent = data.mensagem;
        } catch (error) {
            feedback.textContent = error.message;
        }
        }, 'Enviando...');
    });

    resetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const feedback = document.getElementById('resetFeedback');
        const button = resetForm.querySelector('button[type="submit"]');
        const code = document.getElementById('recoveryCode').value.trim();
        const password = document.getElementById('newPassword').value;
        const confirmation = document.getElementById('confirmPassword').value;
        feedback.textContent = '';

        if (password !== confirmation) {
            feedback.textContent = 'As senhas não coincidem.';
            return;
        }

        await comCarregamento(button, async () => {
        try {
            const response = await fetch(`${window.location.origin}/api/redefinir-senha`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, codigo: code, senha: password })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.erro || 'Não foi possível redefinir a senha.');

            feedback.classList.add('success');
            feedback.textContent = `${data.mensagem} Redirecionando para o login...`;
            window.setTimeout(() => {
                window.location.href = 'login.html';
            }, 1800);
        } catch (error) {
            feedback.textContent = error.message;
        }
        }, 'Salvando...');
    });
});
