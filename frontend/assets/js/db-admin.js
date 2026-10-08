import { mostrarNotificacao, mostrarErro, comCarregamento } from './notifications.js';

const API = `${window.location.origin}/api/admin/db`;

async function chamar(caminho, opcoes = {}) {
  const resposta = await fetch(`${API}${caminho}`, { credentials: 'same-origin', ...opcoes });
  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => ({}));
    const erro = new Error(dados.erro || `Erro HTTP ${resposta.status}`);
    erro.status = resposta.status;
    throw erro;
  }
  return resposta;
}

function formatarTamanho(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function definirTexto(id, valor) {
  const elemento = document.getElementById(id);
  if (elemento) elemento.textContent = valor;
}

async function carregarEstatisticas(secao) {
  const dados = await (await chamar('/stats')).json();
  const r = dados.registros;
  definirTexto('dbTotalChamados', r.chamados);
  definirTexto('dbTamanho', formatarTamanho(dados.tamanhoBytes));
  definirTexto('dbVersaoSchema', `v${dados.versaoSchema}`);
  definirTexto('dbCaminho', dados.caminho);
  definirTexto('dbRegistros', `Chamados: ${r.chamados} · Clientes: ${r.clientes} · Equipe: ${r.equipe} · Histórico: ${r.historico}`);
  const botaoReset = document.getElementById('btnResetDemo');
  if (botaoReset) botaoReset.hidden = !dados.contaTeste;
  secao.hidden = false;
}

async function exportarBackup(evento) {
  const botao = evento.currentTarget;
  await comCarregamento(botao, async () => {
    try {
      const resposta = await chamar('/backup');
      const blob = await resposta.blob();
      const disposicao = resposta.headers.get('Content-Disposition') || '';
      const nome = (disposicao.match(/filename="?([^";]+)"?/) || [])[1] || 'helpti-backup.sql';
      const url = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement('a'), { href: url, download: nome });
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      mostrarNotificacao('Backup SQL exportado com sucesso.');
    } catch (erro) {
      mostrarErro(erro.message);
    }
  }, 'Exportando...');
}

async function restaurarDemo(evento, secao) {
  if (!window.confirm('Isso apaga chamados e clientes da demonstração e restaura o estado inicial. Continuar?')) return;
  await comCarregamento(evento.currentTarget, async () => {
    try {
      const resposta = await chamar('/reset-demo', { method: 'POST' });
      const dados = await resposta.json();
      mostrarNotificacao(dados.mensagem);
      await carregarEstatisticas(secao);
    } catch (erro) {
      mostrarErro(erro.message);
    }
  }, 'Restaurando...');
}

document.addEventListener('DOMContentLoaded', async () => {
  const secao = document.getElementById('dbAdminSection');
  if (!secao) return;
  document.getElementById('btnExportBackup')?.addEventListener('click', exportarBackup);
  document.getElementById('btnResetDemo')?.addEventListener('click', (e) => restaurarDemo(e, secao));
  try {
    await carregarEstatisticas(secao);
  } catch (erro) {
    if (erro.status !== 403 && erro.status !== 404) mostrarErro(erro.message);
  }
});
