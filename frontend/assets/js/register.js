import { mostrarNotificacaoNaProximaPagina, comCarregamento } from './notifications.js';

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os ícones do Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const formRegister = document.getElementById('formRegister');
    const grupoCodigo = document.getElementById('grupoCodigoVerificacao');
    const campoCodigo = document.getElementById('codigoVerificacao');
    const botao = formRegister.querySelector('button[type="submit"]');
    const feedback = document.getElementById('registerFeedback');

    function dadosDoCadastro() {
        const nome = document.getElementById('nome').value.trim();
        const empresa = document.getElementById('empresa').value.trim();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmarSenha').value;
        return { nome, empresa, email, senha, confirmarSenha };
    }

    function mostrarCodigo() {
        grupoCodigo.hidden = false;
        campoCodigo.required = true;
        document.getElementById('nome').disabled = true;
        document.getElementById('empresa').disabled = true;
        document.getElementById('email').disabled = true;
        document.getElementById('senha').disabled = true;
        document.getElementById('confirmarSenha').disabled = true;
        botao.textContent = 'Confirmar e-mail';
        campoCodigo.focus();
    }

    async function enviarCodigo(cadastro) {
        const response = await fetch(`${window.location.origin}/api/contas`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cadastro)
        });
        const dados = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(dados.erro || 'Não foi possível enviar o código.');
        mostrarCodigo();
        feedback.textContent = dados.mensagem;
        feedback.classList.add('success');
    }

    formRegister.addEventListener('submit', async (event) => {
        event.preventDefault();
        feedback.textContent = '';
        feedback.classList.remove('success');
        await comCarregamento(botao, async () => {
        try {
            if (grupoCodigo.hidden) {
                const cadastro = dadosDoCadastro();
                if (cadastro.senha !== cadastro.confirmarSenha) {
                    throw new Error('As senhas não coincidem.');
                }
                await enviarCodigo(cadastro);
            } else {
                const email = document.getElementById('email').value.trim().toLowerCase();
                const response = await fetch(`${window.location.origin}/api/confirmar-conta`, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, codigo: campoCodigo.value.trim() })
                });
                const dados = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(dados.erro || 'Não foi possível confirmar o e-mail.');

                sessionStorage.setItem('grupoId', String(dados.id));
                sessionStorage.setItem('perfilNome', dados.nome);
                sessionStorage.setItem('empresaNome', dados.empresaNome);
                mostrarNotificacaoNaProximaPagina('E-mail confirmado e conta criada com sucesso.');
                window.location.href = 'dashboard.html';
            }
        } catch (error) {
            feedback.textContent = error.message;
        }
        }, grupoCodigo.hidden ? 'Enviando código...' : 'Confirmando...');
        botao.textContent = grupoCodigo.hidden ? 'Criar conta' : 'Confirmar e-mail';
    });

    document.getElementById('reenviarCodigo').addEventListener('click', async (event) => {
        const reenviar = event.currentTarget;
        feedback.textContent = '';
        feedback.classList.remove('success');
        reenviar.disabled = true;
        try {
            await enviarCodigo(dadosDoCadastro());
        } catch (error) {
            feedback.textContent = error.message;
        } finally {
            reenviar.disabled = false;
        }
    });

    document.getElementById('editarCadastro').addEventListener('click', () => {
        grupoCodigo.hidden = true;
        campoCodigo.required = false;
        campoCodigo.value = '';
        for (const id of ['nome', 'empresa', 'email', 'senha', 'confirmarSenha']) {
            document.getElementById(id).disabled = false;
        }
        feedback.textContent = '';
        feedback.classList.remove('success');
        botao.textContent = 'Criar conta';
        botao.disabled = false;
    });
});