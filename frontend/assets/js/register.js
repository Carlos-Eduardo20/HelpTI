import { mostrarNotificacaoNaProximaPagina, comCarregamento } from './notifications.js';

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  const form = document.getElementById('formRegister');
  const button = form.querySelector('button[type="submit"]');
  const feedback = document.getElementById('registerFeedback');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    feedback.textContent = '';
    feedback.classList.remove('success');

    await comCarregamento(button, async () => {
      try {
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmarSenha').value;
        if (senha !== confirmarSenha) throw new Error('As senhas não coincidem.');

        const cadastro = {
          nome: document.getElementById('nome').value.trim(),
          empresa: document.getElementById('empresa').value.trim(),
          email: document.getElementById('email').value.trim().toLowerCase(),
          senha
        };
        const response = await fetch(`${window.location.origin}/api/contas`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cadastro)
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
      }
    }, 'Criando conta...');
  });
});
