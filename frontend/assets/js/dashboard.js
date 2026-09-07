import { buscarChamados, criarChamado, atualizarChamado } from './api.js';

let chamadosEmMemoria = [];

function atualizarPerfil() {
  const nome = localStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`);
}

function abrirModalChamado() { document.getElementById('modalChamado')?.classList.add('active'); }
function fecharModalChamado() { document.getElementById('modalChamado')?.classList.remove('active'); }

function posicionarMenuStatus(picker) {
  const trigger = picker.querySelector('.status-trigger');
  const menu = picker.querySelector('.status-menu');
  if (!trigger || !menu) return;

  const triggerRect = trigger.getBoundingClientRect();
  const menuHeight = menu.getBoundingClientRect().height;
  const margem = 8;
  const espacoAbaixo = window.innerHeight - triggerRect.bottom - margem;
  const abrirAcima = espacoAbaixo < menuHeight && triggerRect.top >= menuHeight + margem;

  menu.style.left = `${triggerRect.left}px`;
  menu.style.width = `${triggerRect.width}px`;
  menu.style.top = abrirAcima
    ? `${triggerRect.top - menuHeight - 5}px`
    : `${triggerRect.bottom + 5}px`;
}

function linhaChamado(chamado) {
  const status = chamado.status || 'ABERTO';
  const statuses = ['ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'RESOLVIDO'];
  return `<tr class="chamado-row" data-detalhes="${chamado.id_chamado}" tabindex="0"><td><strong>#${chamado.id_chamado}</strong></td><td>${chamado.cliente || '-'}</td><td>${chamado.assunto || '-'}</td><td>${chamado.tecnico || 'Não atribuído'}</td><td>${chamado.data_agendada || '-'}</td><td><div class="status-picker" data-status-picker><button class="status-trigger status-${status.toLowerCase()}" type="button" aria-haspopup="listbox" aria-expanded="false"><span class="status-dot"></span><span class="status-trigger-label">${status}</span><span class="status-chevron">⌄</span></button><div class="status-menu" role="listbox">${statuses.map((item) => `<button class="status-option ${item === status ? 'is-selected' : ''}" type="button" role="option" aria-selected="${item === status}" data-status-value="${item}"><span class="status-dot"></span>${item}</button>`).join('')}</div><select class="status-select" data-id="${chamado.id_chamado}" aria-hidden="true" tabindex="-1">${statuses.map((item) => `<option value="${item}" ${item === status ? 'selected' : ''}>${item}</option>`).join('')}</select></div></td></tr>`;
}

function aplicarFiltrosChamados() {
  const busca = document.querySelector('#buscaChamados')?.value.trim().toLowerCase() || '';
  const status = document.querySelector('#filtroStatusChamados')?.value || '';
  const chamadosFiltrados = chamadosEmMemoria.filter((chamado) => {
    const correspondeBusca = [chamado.id_chamado, chamado.cliente, chamado.assunto]
      .some((valor) => String(valor || '').toLowerCase().includes(busca));
    return correspondeBusca && (!status || chamado.status === status);
  });
  const tabela = document.querySelector('#tabelaChamados');
  if (tabela) tabela.innerHTML = chamadosFiltrados.map(linhaChamado).join('') || '<tr><td colspan="6">Nenhum chamado encontrado.</td></tr>';
}

async function carregarChamados() {
  const chamados = await buscarChamados();
  chamadosEmMemoria = chamados;
  aplicarFiltrosChamados();
  const contagens = ['ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'RESOLVIDO'].map((status) => chamados.filter((item) => item.status === status).length);
  document.querySelectorAll('.stat-value').forEach((element, index) => { if (contagens[index] !== undefined) element.textContent = contagens[index]; });
  renderizarAgenda(chamados);
}

function renderizarAgenda(chamados) {
  const agenda = document.querySelector('#agendaDinamica');
  const cabecalho = document.querySelector('#agendaCabecalho');
  if (!agenda || !cabecalho) return;
  const todasDatas = document.querySelector('#agendaTodasDatas')?.checked;
  const dataSelecionada = todasDatas ? '' : document.querySelector('#agendaData')?.value;
  const chamadosComData = chamados.filter((item) => item.data_agendada);
  const datas = [...new Set(chamadosComData.map((item) => item.data_agendada))]
    .filter((data) => !dataSelecionada || data === dataSelecionada)
    .sort();

  cabecalho.style.gridTemplateColumns = `repeat(${Math.max(datas.length, 1)}, minmax(220px, 1fr))`;
  agenda.style.gridTemplateColumns = `repeat(${Math.max(datas.length, 1)}, minmax(220px, 1fr))`;

  if (!datas.length) {
    cabecalho.innerHTML = '';
    agenda.innerHTML = '<p class="agenda-empty">Nenhum chamado para esta data.</p>';
    return;
  }

  cabecalho.innerHTML = datas.map((data) => `<div class="day-col-header${data === dataSelecionada ? ' active' : ''}">${formatarDataAgenda(data)}</div>`).join('');
  agenda.innerHTML = datas.map((data) => `<div class="agenda-column">${chamadosComData
    .filter((item) => item.data_agendada === data)
    .map((item) => `<a class="ticket-card-agenda priority-medium" href="chamados-detalhe.html?id=${item.id_chamado}"><strong>#${item.id_chamado} - ${item.cliente || '-'}</strong><p>${item.assunto || '-'}</p><span class="badge badge-blue">${item.status}</span></a>`)
    .join('')}</div>`).join('');
}

function formatarDataAgenda(data) {
  return new Date(`${data}T12:00:00`).toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
  });
}

function filtrarAgenda() { renderizarAgenda(chamadosEmMemoria); }
function mudarDia(dias) {
  const campo = document.querySelector('#agendaData');
  if (!campo) return;
  const data = new Date(`${campo.value || new Date().toISOString().slice(0, 10)}T12:00:00`);
  data.setDate(data.getDate() + dias);
  campo.value = data.toISOString().slice(0, 10);
  filtrarAgenda();
}

async function salvarChamado(event) {
  event.preventDefault();
  const form = event.target;
  const campos = form.elements;
  try {
    await criarChamado({
      cliente: campos.cliente.value.trim(),
      email_cliente: campos.email_cliente.value.trim(),
      assunto: campos.assunto.value.trim(),
      descricao: campos.descricao.value.trim(),
      data_agendada: campos.data_agendada.value || null
    });
    fecharModalChamado(); form.reset(); await carregarChamados(); alert('Chamado criado com sucesso.');
  } catch (error) { alert(`Não foi possível criar o chamado: ${error.message}`); }
}

window.abrirModalChamado = abrirModalChamado;
window.fecharModalChamado = fecharModalChamado;
window.salvarChamado = salvarChamado;
window.filtrarAgenda = filtrarAgenda;
window.mudarDia = mudarDia;

document.addEventListener('click', async (event) => {
  const statusTrigger = event.target.closest('[data-status-picker] .status-trigger');
  if (statusTrigger) {
    const picker = statusTrigger.closest('[data-status-picker]');
    const isOpen = picker.classList.toggle('is-open');
    statusTrigger.setAttribute('aria-expanded', String(isOpen));
    if (isOpen) posicionarMenuStatus(picker);
    return;
  }

  const statusOption = event.target.closest('[data-status-picker] .status-option');
  if (statusOption) {
    const picker = statusOption.closest('[data-status-picker]');
    const select = picker.querySelector('.status-select');
    const value = statusOption.dataset.statusValue;
    const trigger = picker.querySelector('.status-trigger');
    const id = select.dataset.id;
    const statusAnterior = select.value;
    select.value = value;
    trigger.className = `status-trigger status-${value.toLowerCase()}`;
    trigger.querySelector('.status-trigger-label').textContent = value;
    picker.querySelectorAll('.status-option').forEach((option) => {
      const selected = option === statusOption;
      option.classList.toggle('is-selected', selected);
      option.setAttribute('aria-selected', String(selected));
    });
    picker.classList.remove('is-open');
    trigger.setAttribute('aria-expanded', 'false');
    try {
      await atualizarChamado(id, { status: value });
      await carregarChamados();
    } catch (error) {
      select.value = statusAnterior;
      await carregarChamados();
      alert(`Não foi possível atualizar o status: ${error.message}`);
    }
    return;
  }

  document.querySelectorAll('[data-status-picker].is-open').forEach((picker) => {
    picker.classList.remove('is-open');
    const menu = picker.querySelector('.status-menu');
    if (menu) menu.removeAttribute('style');
    picker.querySelector('.status-trigger')?.setAttribute('aria-expanded', 'false');
  });

  const row = event.target.closest('.chamado-row');
  if (row) window.location.href = `chamados-detalhe.html?id=${row.dataset.detalhes}`;
});

window.addEventListener('resize', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
});

window.addEventListener('scroll', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
}, true);

document.addEventListener('DOMContentLoaded', () => {
  atualizarPerfil();
  document.querySelector('#buscaChamados')?.addEventListener('input', aplicarFiltrosChamados);
  document.querySelector('#filtroStatusChamados')?.addEventListener('change', aplicarFiltrosChamados);
  carregarChamados().catch((error) => {
    const tabela = document.querySelector('#tabelaChamados');
    const agenda = document.querySelector('#agendaDinamica');
    if (tabela) tabela.innerHTML = `<tr><td colspan="6">Não foi possível carregar: ${error.message}</td></tr>`;
    if (agenda) agenda.innerHTML = `<p>Não foi possível carregar a agenda: ${error.message}</p>`;
  });
});
