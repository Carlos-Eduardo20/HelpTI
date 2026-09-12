import { buscarChamados, criarChamado, atualizarChamado, buscarClientes, criarCliente, buscarConfiguracoes } from './api.js';

let chamadosEmMemoria = [];
let agendaPagina = 0;
let agendaModoAnterior = false;
let paginaChamados = 1;
const chamadosPorPagina = 5;

async function atualizarPerfil() {
  let nome = localStorage.getItem('workspaceName') || localStorage.getItem('perfilNome') || sessionStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`);
  try {
    const configuracoes = await buscarConfiguracoes();
    nome = configuracoes.workspaceName || nome;
    localStorage.setItem('workspaceName', nome);
    localStorage.setItem('supportEmail', configuracoes.supportEmail || '');
    document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
    document.querySelectorAll('.user-avatar img').forEach((image) => image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`);
  } catch (error) {
  }
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
  return `<tr class="chamado-row" data-detalhes="${chamado.id_chamado}" tabindex="0"><td><strong>#${chamado.id_chamado}</strong></td><td>${chamado.cliente || '-'}</td><td>${chamado.assunto || '-'}</td><td>${chamado.tecnico || 'Não atribuído'}</td><td>${chamado.data_agendada || '-'}</td><td><div class="status-picker" data-status-picker><button class="status-trigger status-${status.toLowerCase()}" type="button" aria-haspopup="listbox" aria-expanded="false"><span class="status-dot"></span><span class="status-trigger-label">${status}</span><span class="status-chevron"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></span></button><div class="status-menu" role="listbox">${statuses.map((item) => `<button class="status-option ${item === status ? 'is-selected' : ''}" type="button" role="option" aria-selected="${item === status}" data-status-value="${item}"><span class="status-dot"></span>${item}</button>`).join('')}</div><select class="status-select" data-id="${chamado.id_chamado}" aria-hidden="true" tabindex="-1">${statuses.map((item) => `<option value="${item}" ${item === status ? 'selected' : ''}>${item}</option>`).join('')}</select></div></td></tr>`;
}

function aplicarFiltrosChamados() {
  const busca = document.querySelector('#buscaChamados')?.value.trim().toLowerCase() || '';
  const status = document.querySelector('#filtroStatusChamados')?.value || '';
  const chamadosFiltrados = chamadosEmMemoria.filter((chamado) => {
    const correspondeBusca = [chamado.id_chamado, chamado.cliente, chamado.assunto]
      .some((valor) => String(valor || '').toLowerCase().includes(busca));
    return correspondeBusca && (!status || chamado.status === status);
  });
  const totalPaginas = Math.max(1, Math.ceil(chamadosFiltrados.length / chamadosPorPagina));
  paginaChamados = Math.min(paginaChamados, totalPaginas);
  const inicio = (paginaChamados - 1) * chamadosPorPagina;
  const chamadosDaPagina = chamadosFiltrados.slice(inicio, inicio + chamadosPorPagina);
  const tabela = document.querySelector('#tabelaChamados');
  if (tabela) tabela.innerHTML = chamadosDaPagina.map(linhaChamado).join('') || '<tr><td colspan="6">Nenhum chamado encontrado.</td></tr>';
  renderizarPaginacao(chamadosFiltrados.length, totalPaginas);
}

function renderizarPaginacao(totalResultados, totalPaginas) {
  const paginacao = document.querySelector('#paginacaoChamados');
  if (!paginacao) return;
  if (!totalResultados) {
    paginacao.innerHTML = '';
    return;
  }

  const inicio = (paginaChamados - 1) * chamadosPorPagina + 1;
  const fim = Math.min(paginaChamados * chamadosPorPagina, totalResultados);
  const paginas = criarListaPaginas(totalPaginas, paginaChamados);
  paginacao.innerHTML = `
    <span class="pagination-summary">Exibindo ${inicio}-${fim} de ${totalResultados} chamados</span>
    <div class="pagination-controls">
      <button class="pagination-button" type="button" data-pagina="${paginaChamados - 1}" aria-label="Página anterior" ${paginaChamados === 1 ? 'disabled' : ''}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
      </button>
      ${paginas.map((pagina) => pagina === '...' ? '<span class="pagination-ellipsis">...</span>' : `<button class="pagination-button ${pagina === paginaChamados ? 'active' : ''}" type="button" data-pagina="${pagina}" aria-label="Página ${pagina}" ${pagina === paginaChamados ? 'aria-current="page"' : ''}>${pagina}</button>`).join('')}
      <button class="pagination-button" type="button" data-pagina="${paginaChamados + 1}" aria-label="Próxima página" ${paginaChamados === totalPaginas ? 'disabled' : ''}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
      </button>
    </div>`;
}

function criarListaPaginas(totalPaginas, paginaAtual) {
  const paginasPorBloco = 3;
  const primeiroNumero = Math.floor((paginaAtual - 1) / paginasPorBloco) * paginasPorBloco + 1;
  const ultimaPaginaDoBloco = Math.min(primeiroNumero + paginasPorBloco - 1, totalPaginas);
  return Array.from(
    { length: ultimaPaginaDoBloco - primeiroNumero + 1 },
    (_, indice) => primeiroNumero + indice
  );
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
  const chamadosComData = chamados.filter((item) => {
    if (!item.data_agendada) return false;
    const diaDaSemana = new Date(`${item.data_agendada}T12:00:00`).getDay();
    return diaDaSemana >= 1 && diaDaSemana <= 5;
  });
  const todasDatas = document.querySelector('#agendaTodasDatas')?.checked || false;
  if (todasDatas !== agendaModoAnterior) agendaPagina = 0;
  agendaModoAnterior = todasDatas;
  let datas;
  if (todasDatas) {
    const datasComChamados = [...new Set(chamadosComData.map((item) => item.data_agendada))].sort();
    datas = datasComChamados.slice(agendaPagina * 5, agendaPagina * 5 + 5);
  } else {
    const campoData = document.querySelector('#agendaData');
    const dataSelecionada = new Date(`${campoData?.value || new Date().toISOString().slice(0, 10)}T12:00:00`);
    const diaDaSemana = dataSelecionada.getDay();
    const segunda = new Date(dataSelecionada);
    segunda.setDate(dataSelecionada.getDate() + (diaDaSemana === 0 ? -6 : 1 - diaDaSemana));
    datas = Array.from({ length: 5 }, (_, indice) => {
      const data = new Date(segunda);
      data.setDate(segunda.getDate() + indice);
      return data.toISOString().slice(0, 10);
    });
  }
  const hoje = new Date().toISOString().slice(0, 10);

  cabecalho.style.gridTemplateColumns = 'repeat(5, minmax(220px, 1fr))';
  agenda.style.gridTemplateColumns = 'repeat(5, minmax(220px, 1fr))';

  cabecalho.innerHTML = datas.map((data) => `<div class="day-col-header ${data === hoje ? 'active' : ''}">${formatarDataAgenda(data)}</div>`).join('');
  const classesBadge = { ABERTO: 'badge-blue', ANDAMENTO: 'badge-yellow', AGUARDANDO: 'badge-yellow', RESOLVIDO: 'badge-green' };
  agenda.innerHTML = datas.map((data) => {
    const chamadosDoDia = chamadosComData.filter((item) => item.data_agendada === data);
    const cards = chamadosDoDia.map((item) => { const status = item.status || 'ABERTO'; return `<a class="ticket-card-agenda status-${status.toLowerCase()}" href="chamados-detalhe.html?id=${item.id_chamado}"><strong>#${item.id_chamado} - ${item.cliente || '-'}</strong><p>${item.assunto || '-'}</p><span class="badge ${classesBadge[status] || 'badge-blue'}">${status}</span></a>`; }).join('');
    return `<div class="agenda-column">${cards}</div>`;
  }).join('');
}

function formatarDataAgenda(data) {
  return new Date(`${data}T12:00:00`).toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
  });
}

function filtrarAgenda() { renderizarAgenda(chamadosEmMemoria); }

const nomesMesesAgenda = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

function formatarDataCurtaAgenda(data) {
  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

function abrirCalendarioAgenda() {
  const modal = document.querySelector('#modalCalendarioAgenda');
  if (!modal) return;
  const selecionada = document.querySelector('#agendaData')?.value || new Date().toISOString().slice(0, 10);
  const data = new Date(`${selecionada}T12:00:00`);
  modal.dataset.mes = String(data.getMonth());
  modal.dataset.ano = String(data.getFullYear());
  modal.hidden = false;
  renderizarCalendarioAgenda();
  document.querySelector('#fecharCalendarioAgenda')?.focus();
}

function fecharCalendarioAgenda() { const modal = document.querySelector('#modalCalendarioAgenda'); if (modal) modal.hidden = true; }

function renderizarCalendarioAgenda() {
  const modal = document.querySelector('#modalCalendarioAgenda');
  const grade = document.querySelector('#calendarioAgendaDias');
  const titulo = document.querySelector('#mesAnoAgenda');
  if (!modal || !grade || !titulo) return;
  const mes = Number(modal.dataset.mes);
  const ano = Number(modal.dataset.ano);
  titulo.textContent = `${nomesMesesAgenda[mes]} de ${ano}`;
  const primeiroDia = new Date(ano, mes, 1);
  const inicio = (primeiroDia.getDay() + 6) % 7;
  const ultimoDia = new Date(ano, mes + 1, 0).getDate();
  const diasMesAnterior = new Date(ano, mes, 0).getDate();
  const selecionada = document.querySelector('#agendaData')?.value;
  const hoje = new Date().toISOString().slice(0, 10);
  const dias = [];
  for (let indice = 0; indice < 42; indice += 1) {
    const numero = indice - inicio + 1;
    let dia = numero;
    let mesDoDia = mes;
    let anoDoDia = ano;
    let classe = '';
    if (numero < 1) { dia = diasMesAnterior + numero; mesDoDia -= 1; classe = ' is-other-month'; }
    if (numero > ultimoDia) { dia = numero - ultimoDia; mesDoDia += 1; classe = ' is-other-month'; }
    if (mesDoDia < 0) { mesDoDia = 11; anoDoDia -= 1; }
    if (mesDoDia > 11) { mesDoDia = 0; anoDoDia += 1; }
    const valor = `${anoDoDia}-${String(mesDoDia + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
    if (valor === hoje) classe += ' is-today';
    if (valor === selecionada) classe += ' is-selected';
    dias.push(`<button type="button" class="agenda-calendar-day${classe}" data-data="${valor}">${dia}</button>`);
  }
  grade.innerHTML = dias.join('');
}

function selecionarDataAgenda(valor) {
  const campo = document.querySelector('#agendaData');
  const label = document.querySelector('#agendaDataLabel');
  if (!campo || !label) return;
  campo.value = valor;
  label.textContent = formatarDataCurtaAgenda(valor);
  fecharCalendarioAgenda();
  filtrarAgenda();
}

function mudarDia(semanas) {
  if (document.querySelector('#agendaTodasDatas')?.checked) {
    const datasComChamados = [...new Set(chamadosEmMemoria.filter((item) => {
      if (!item.data_agendada) return false;
      const diaDaSemana = new Date(`${item.data_agendada}T12:00:00`).getDay();
      return diaDaSemana >= 1 && diaDaSemana <= 5;
    }).map((item) => item.data_agendada))];
    const ultimaPagina = Math.max(0, Math.ceil(datasComChamados.length / 5) - 1);
    agendaPagina = Math.min(ultimaPagina, Math.max(0, agendaPagina + semanas));
    renderizarAgenda(chamadosEmMemoria);
    return;
  }
  const campo = document.querySelector('#agendaData');
  if (!campo) return;
  const data = new Date(`${campo.value || new Date().toISOString().slice(0, 10)}T12:00:00`);
  data.setDate(data.getDate() + (semanas * 7));
  campo.value = data.toISOString().slice(0, 10);
  const label = document.querySelector('#agendaDataLabel');
  if (label) label.textContent = formatarDataCurtaAgenda(campo.value);
  filtrarAgenda();
}

async function carregarClientesNoChamado() {
  const seletor = document.querySelector('#clienteChamado');
  if (!seletor) return;
  try {
    const clientes = await buscarClientes();
    seletor.innerHTML = '<option value="">Selecione um cliente</option>' + clientes.map((cliente) => `<option value="${cliente.nome}" data-email="${cliente.email || ''}">${cliente.nome}</option>`).join('');
  } catch (error) { seletor.innerHTML = `<option value="">Não foi possível carregar clientes</option>`; }
}

function abrirNovoClienteDoChamado() {
  document.querySelector('#modalChamado')?.classList.remove('active');
  document.querySelector('#modalNovoClienteChamado')?.classList.add('active');
}

function cancelarNovoClienteDoChamado() {
  document.querySelector('#modalNovoClienteChamado')?.classList.remove('active');
  document.querySelector('#modalChamado')?.classList.add('active');
}

async function salvarNovoClienteDoChamado(event) {
  event.preventDefault();
  const form = event.target;
  const campos = form.elements;
  try {
    const cliente = await criarCliente({ nome: campos.nome.value.trim(), telefone: campos.telefone.value.trim(), contato: campos.contato.value.trim(), email: campos.email.value.trim() });
    await carregarClientesNoChamado();
    const seletor = document.querySelector('#clienteChamado');
    seletor.value = cliente.nome;
    document.querySelector('#emailClienteChamado').value = cliente.email || '';
    form.reset();
    cancelarNovoClienteDoChamado();
  } catch (error) { alert(`Não foi possível cadastrar o cliente: ${error.message}`); }
}

async function salvarChamado(event) {
  event.preventDefault();
  const form = event.target;
  const campos = form.elements;
  if (!campos.cliente.value || !campos.email_cliente.value || !campos.assunto.value || !campos.data_agendada.value) {
    form.reportValidity();
    return;
  }
  const diaDaSemana = new Date(`${campos.data_agendada.value}T12:00:00`).getDay();
  if (diaDaSemana === 0 || diaDaSemana === 6) {
    alert('Chamados só podem ser agendados de segunda a sexta-feira.');
    return;
  }
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
window.abrirNovoClienteDoChamado = abrirNovoClienteDoChamado;
window.cancelarNovoClienteDoChamado = cancelarNovoClienteDoChamado;
window.salvarNovoClienteDoChamado = salvarNovoClienteDoChamado;

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
  if (row && !event.target.closest('[data-status-picker]')) window.location.href = `chamados-detalhe.html?id=${row.dataset.detalhes}`;
});

window.addEventListener('resize', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
});

window.addEventListener('scroll', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
}, true);

document.addEventListener('DOMContentLoaded', () => {
  atualizarPerfil();
  const agendaData = document.querySelector('#agendaData');
  if (agendaData && !agendaData.value) agendaData.value = new Date().toISOString().slice(0, 10);
  if (agendaData) document.querySelector('#agendaDataLabel').textContent = formatarDataCurtaAgenda(agendaData.value);
  document.querySelector('#abrirCalendarioAgenda')?.addEventListener('click', abrirCalendarioAgenda);
  document.querySelector('#fecharCalendarioAgenda')?.addEventListener('click', fecharCalendarioAgenda);
  document.querySelector('#confirmarCalendarioAgenda')?.addEventListener('click', fecharCalendarioAgenda);
  document.querySelector('#mesAnteriorAgenda')?.addEventListener('click', () => {
    const modal = document.querySelector('#modalCalendarioAgenda');
    let mes = Number(modal.dataset.mes) - 1;
    let ano = Number(modal.dataset.ano);
    if (mes < 0) { mes = 11; ano -= 1; }
    modal.dataset.mes = String(mes); modal.dataset.ano = String(ano); renderizarCalendarioAgenda();
  });
  document.querySelector('#mesProximoAgenda')?.addEventListener('click', () => {
    const modal = document.querySelector('#modalCalendarioAgenda');
    let mes = Number(modal.dataset.mes) + 1;
    let ano = Number(modal.dataset.ano);
    if (mes > 11) { mes = 0; ano += 1; }
    modal.dataset.mes = String(mes); modal.dataset.ano = String(ano); renderizarCalendarioAgenda();
  });
  document.querySelector('#hojeCalendarioAgenda')?.addEventListener('click', () => selecionarDataAgenda(new Date().toISOString().slice(0, 10)));
  document.querySelector('#calendarioAgendaDias')?.addEventListener('click', (event) => {
    const botao = event.target.closest('[data-data]');
    if (botao) selecionarDataAgenda(botao.dataset.data);
  });
  document.querySelector('#modalCalendarioAgenda')?.addEventListener('click', (event) => {
    if (event.target.id === 'modalCalendarioAgenda') fecharCalendarioAgenda();
  });
  document.querySelector('#buscaChamados')?.addEventListener('input', () => {
    paginaChamados = 1;
    aplicarFiltrosChamados();
  });
  document.querySelector('#filtroStatusChamados')?.addEventListener('change', () => {
    paginaChamados = 1;
    aplicarFiltrosChamados();
  });
  document.querySelector('#paginacaoChamados')?.addEventListener('click', (event) => {
    const botao = event.target.closest('[data-pagina]');
    if (!botao || botao.disabled) return;
    paginaChamados = Number(botao.dataset.pagina);
    aplicarFiltrosChamados();
  });
  const clienteChamado = document.querySelector('#clienteChamado');
  clienteChamado?.addEventListener('change', () => {
    if (clienteChamado.value === '__novo__') {
      clienteChamado.value = '';
      abrirNovoClienteDoChamado();
      return;
    }
    const email = clienteChamado.selectedOptions[0]?.dataset.email || '';
    const campoEmail = document.querySelector('#emailClienteChamado');
    if (campoEmail && email) campoEmail.value = email;
  });
  carregarClientesNoChamado();
  carregarChamados().catch((error) => {
    const tabela = document.querySelector('#tabelaChamados');
    const agenda = document.querySelector('#agendaDinamica');
    if (tabela) tabela.innerHTML = `<tr><td colspan="6">Não foi possível carregar: ${error.message}</td></tr>`;
    if (agenda) agenda.innerHTML = `<p>Não foi possível carregar a agenda: ${error.message}</p>`;
  });
});
