import { buscarChamados, buscarChamadoPorId, criarChamado, atualizarChamado } from './api.js';

let chamadosEmMemoria = [];

function atualizarPerfil() {
  const nome = localStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`);
}

function definirDataAtual() {
  const campo = document.querySelector('#agendaData');
  if (campo && !campo.value) campo.value = new Date().toISOString().slice(0, 10);
}

function abrirModalChamado() { document.getElementById('modalChamado')?.classList.add('active'); }
function fecharModalChamado() { document.getElementById('modalChamado')?.classList.remove('active'); }

function linhaChamado(chamado) {
  const status = chamado.status || 'ABERTO';
  return `<tr><td><strong>#${chamado.id_chamado}</strong></td><td>${chamado.cliente || '-'}</td><td>${chamado.assunto || '-'}</td><td>${chamado.tecnico || 'Não atribuído'}</td><td>${chamado.data_agendada || '-'}</td><td><select class="status-select" data-id="${chamado.id_chamado}">${['ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'RESOLVIDO'].map((item) => `<option value="${item}" ${item === status ? 'selected' : ''}>${item}</option>`).join('')}</select></td><td><button class="btn-cancel" data-detalhes="${chamado.id_chamado}">Ver chamado</button> <button class="btn-cancel" data-atender="${chamado.id_chamado}">Atualizar</button></td></tr>`;
}

async function carregarChamados() {
  const chamados = await buscarChamados();
  chamadosEmMemoria = chamados;
  const tabela = document.querySelector('#tabelaChamados');
  if (tabela) tabela.innerHTML = chamados.map(linhaChamado).join('') || '<tr><td colspan="7">Nenhum chamado cadastrado.</td></tr>';
  const contagens = ['ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'RESOLVIDO'].map((status) => chamados.filter((item) => item.status === status).length);
  document.querySelectorAll('.stat-value').forEach((element, index) => { if (contagens[index] !== undefined) element.textContent = contagens[index]; });
  renderizarAgenda(chamados);
}

function renderizarAgenda(chamados) {
  const agenda = document.querySelector('#agendaDinamica');
  if (!agenda) return;
  const dataSelecionada = document.querySelector('#agendaData')?.value;
  const filtrados = chamados.filter((item) => !dataSelecionada || !item.data_agendada || item.data_agendada === dataSelecionada);
  agenda.innerHTML = filtrados.map((item) => `<div class="ticket-card-agenda priority-medium"><span class="ticket-time">${item.hora_agendada || 'Sem horário'}</span><strong>#${item.id_chamado} - ${item.cliente || '-'}</strong><p>${item.assunto || '-'}</p><span class="badge badge-blue">${item.status}</span></div>`).join('') || '<p>Nenhum chamado para esta data.</p>';
}

function filtrarAgenda() { renderizarAgenda(chamadosEmMemoria); }
function mudarDia(dias) {
  const campo = document.querySelector('#agendaData');
  if (!campo) return;
  const data = new Date(`${campo.value}T12:00:00`);
  data.setDate(data.getDate() + dias);
  campo.value = data.toISOString().slice(0, 10);
  filtrarAgenda();
}

async function salvarChamado(event) {
  event.preventDefault();
  const form = event.target;
  const inputs = [...form.querySelectorAll('input, textarea, select')];
  try {
    await criarChamado({ cliente: inputs[0].value.trim(), assunto: inputs[1].value.trim(), descricao: inputs[2].value.trim(), data_agendada: inputs[3]?.value || null, hora_agendada: inputs[4]?.value || null });
    fecharModalChamado(); form.reset(); await carregarChamados(); alert('Chamado criado com sucesso.');
  } catch (error) { alert(`Não foi possível criar o chamado: ${error.message}`); }
}

window.abrirModalChamado = abrirModalChamado;
window.fecharModalChamado = fecharModalChamado;
window.salvarChamado = salvarChamado;
window.filtrarAgenda = filtrarAgenda;
window.mudarDia = mudarDia;

document.addEventListener('click', async (event) => {
  const detailsButton = event.target.closest('[data-detalhes]');
  if (detailsButton) {
    try {
      const chamado = await buscarChamadoPorId(detailsButton.dataset.detalhes);
      alert(`Chamado #${chamado.id_chamado}\nCliente: ${chamado.cliente}\nAssunto: ${chamado.assunto}\nDescrição: ${chamado.descricao || '-'}\nStatus: ${chamado.status}`);
    } catch (error) { alert(error.message); }
    return;
  }
  const button = event.target.closest('[data-atender]');
  if (!button) return;
  const select = document.querySelector(`.status-select[data-id="${button.dataset.atender}"]`);
  try { await atualizarChamado(button.dataset.atender, { status: select.value }); await carregarChamados(); } catch (error) { alert(error.message); }
});

document.addEventListener('DOMContentLoaded', () => {
  atualizarPerfil();
  definirDataAtual();
  carregarChamados().catch((error) => {
    const tabela = document.querySelector('#tabelaChamados');
    const agenda = document.querySelector('#agendaDinamica');
    if (tabela) tabela.innerHTML = `<tr><td colspan="7">Não foi possível carregar: ${error.message}</td></tr>`;
    if (agenda) agenda.innerHTML = `<p>Não foi possível carregar a agenda: ${error.message}</p>`;
  });
});
