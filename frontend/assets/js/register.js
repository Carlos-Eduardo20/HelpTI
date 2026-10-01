document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os ícones do Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const formRegister = document.getElementById('formRegister');

    formRegister.addEventListener('submit', async (event) => {
        event.preventDefault();

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

        const dominio = email.split('@').pop().toLowerCase();
        const dominiosPessoais = new Set([
            'aol.com', 'bol.com.br', 'email.com', 'fastmail.com', 'gmail.com',
            'gmx.com', 'googlemail.com', 'hotmail.com', 'hotmail.com.br', 'icloud.com',
            'ig.com.br', 'live.com', 'mail.com', 'me.com', 'msn.com', 'outlook.com',
            'outlook.com.br', 'pm.me', 'proton.me', 'protonmail.com', 'terra.com.br',
            'uol.com.br', 'yahoo.com', 'yahoo.com.br', 'yandex.com', 'zoho.com'
        ]);
        if ([...dominiosPessoais].some((pessoal) => dominio === pessoal || dominio.endsWith(`.${pessoal}`))) {
            feedback.textContent = 'Use um e-mail corporativo. Provedores de e-mail pessoal não são aceitos.';
            return;
        }

        botao.disabled = true;
        botao.textContent = 'Criando conta...';
        try {
            const response = await fetch(`${window.location.origin}/api/contas`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ empresa, email, senha })
            });
            const dados = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(dados.erro || 'Não foi possível criar a conta.');

            sessionStorage.setItem('grupoId', String(dados.id));
            sessionStorage.setItem('perfilNome', dados.nome);
            sessionStorage.setItem('empresaNome', dados.empresaNome);
            window.location.href = 'dashboard.html';
        } catch (error) {
            feedback.textContent = error.message;
            botao.disabled = false;
            botao.textContent = 'Criar conta empresarial';
        }
    });
});