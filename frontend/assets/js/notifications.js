const PENDING_NOTIFICATION_KEY = 'helpti-pending-notification';

const ESTILOS = `
.error-toast { background: #fef2f2; border-color: #b91c1c; color: #b91c1c; }
.btn-spinner { display: inline-block; width: 1em; height: 1em; margin-right: 8px; vertical-align: -0.15em; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: helpti-spin 0.7s linear infinite; }
@keyframes helpti-spin { to { transform: rotate(360deg); } }
button.is-loading { opacity: 0.8; cursor: wait; }
`;

function garantirEstilos() {
  if (document.getElementById('helpti-feedback-styles')) return;
  const estilo = document.createElement('style');
  estilo.id = 'helpti-feedback-styles';
  estilo.textContent = ESTILOS;
  document.head.append(estilo);
}

export function mostrarErro(mensagem) {
  mostrarNotificacao(mensagem, 'error');
}

// Desabilita o botão, mostra um spinner e restaura o estado ao final da tarefa.
export async function comCarregamento(botao, tarefa, textoCarregando = 'Aguarde...') {
  if (!botao) return tarefa();
  garantirEstilos();
  const htmlOriginal = botao.innerHTML;
  const largura = botao.offsetWidth;
  botao.disabled = true;
  botao.classList.add('is-loading');
  botao.setAttribute('aria-busy', 'true');
  if (largura) botao.style.minWidth = `${largura}px`;
  botao.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>';
  botao.append(textoCarregando);
  try {
    return await tarefa();
  } finally {
    botao.disabled = false;
    botao.classList.remove('is-loading');
    botao.removeAttribute('aria-busy');
    botao.style.minWidth = '';
    botao.innerHTML = htmlOriginal;
  }
}

export function mostrarNotificacao(mensagem, tipo = 'success') {
  if (!mensagem) return;
  garantirEstilos();

  let container = document.querySelector('#toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-relevant', 'additions');
    document.body.append(container);
  }

  const notificacao = document.createElement('div');
  notificacao.className = tipo === 'error' ? 'success-toast error-toast' : 'success-toast';
  notificacao.setAttribute('role', tipo === 'error' ? 'alert' : 'status');
  notificacao.textContent = mensagem;
  container.append(notificacao);

  window.setTimeout(() => {
    notificacao.classList.add('is-hiding');
    notificacao.addEventListener('transitionend', () => notificacao.remove(), { once: true });
    window.setTimeout(() => notificacao.remove(), 350);
  }, 4000);
}

export function mostrarNotificacaoNaProximaPagina(mensagem) {
  if (mensagem) sessionStorage.setItem(PENDING_NOTIFICATION_KEY, mensagem);
}

const notificacaoPendente = sessionStorage.getItem(PENDING_NOTIFICATION_KEY);
if (notificacaoPendente) {
  sessionStorage.removeItem(PENDING_NOTIFICATION_KEY);
  mostrarNotificacao(notificacaoPendente);
}
