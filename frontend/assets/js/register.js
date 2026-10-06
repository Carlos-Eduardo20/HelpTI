import { mostrarNotificacaoNaProximaPagina } from './notifications.js';

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os ícones do Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const formRegister = document.getElementById('formRegister');

    formRegister.addEventListener('submit', async (event) => {
        event.preventDefault();

        const nome = document.getElementById('nome').value.trim();
        const empresa = document.getElementById('empresa').value.trim();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmarSenha').value;
        const feedback = document.getElementById('registerFeedback');
        const botao = formRegister.querySelector('button[type="submit"]');

        feedback.textContent = '';
        feedback.classList.remove('success');
        if (senha !== confirmarSenha) {
            feedback.textContent = 'As senhas não coincidem.';
            return;
        }

        botao.disabled = true;
        botao.textContent = 'Criando conta...';
        try {
            const response = await fetch(`${window.location.origin}/api/contas`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome, empresa, email, senha })
            });
            const dados = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(dados.erro || 'Não foi possível criar a conta.');

            sessionStorage.setItem('grupoId', String(dados.id));
            sessionStorage.setItem('perfilNome', dados.nome);
            sessionStorage.setItem('empresaNome', dados.empresaNome);
            mostrarNotificacaoNaProximaPagina('Conta criada com sucesso.');
            window.location.href = 'dashboard.html';
        } catch (error) {
            feedback.textContent = error.message;
            botao.disabled = false;
            botao.textContent = 'Criar conta';
        }
    });
});