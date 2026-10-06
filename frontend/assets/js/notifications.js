const PENDING_NOTIFICATION_KEY = 'helpti-pending-notification';

export function mostrarNotificacao(mensagem) {
  if (!mensagem) return;

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
  notificacao.className = 'success-toast';
  notificacao.setAttribute('role', 'status');
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
