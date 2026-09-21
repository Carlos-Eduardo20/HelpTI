document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os ícones do Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const formRegister = document.getElementById('formRegister');

    formRegister.addEventListener('submit', (e) => {
        e.preventDefault();

        const empresa = document.getElementById('empresa').value.trim();
        const email = document.getElementById('email').value.trim();
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmarSenha').value;

        // Validação de senhas iguais
        if (senha !== confirmarSenha) {
            alert('As senhas não coincidem!');
            return;
        }

        // Validação básica de e-mail corporativo (exemplo)
        const dominiosProibidos = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com'];
        const dominioEmail = email.split('@')[1]?.toLowerCase();

        if (dominiosProibidos.includes(dominioEmail)) {
            alert('Por favor, utilize um e-mail corporativo para realizar a solicitação.');
            return;
        }

        // Envio do formulário para o seu Backend Python/API
        console.log('Dados prontos para envio:', { empresa, email, senha });
        alert('Solicitação enviada com sucesso!');
    });
});