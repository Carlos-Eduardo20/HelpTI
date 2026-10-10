import { buscarChamados, criarChamado, atualizarChamado, buscarClientes, buscarEquipe, buscarSetores, criarCliente, buscarConfiguracoes } from './api.js';
import { gerarUrlAvatar } from './avatar.js';
import { mostrarNotificacao, mostrarErro, comCarregamento } from './notifications.js';
import { formatBrazilianPhone } from './phone.js';

let chamadosEmMemoria = [];
let agendaPagina = 0;
let agendaModoAnterior = false;
let ultimaDataAgenda = '';
let paginaChamados = 1;
const chamadosPorPagina = 5;
const SLA_LIMITE_SEGUNDOS = 25 * 60;

function dataLocalISO(data = new Date()) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

function datasAgendaApartirDe(dataInicial, datasComChamados) {
  const indiceInicial = datasComChamados.findIndex((data) => data >= dataInicial);
  const datas = indiceInicial < 0 ? [] : datasComChamados.slice(indiceInicial);
  if (!datas.length || datas[0] !== dataInicial) datas.unshift(dataInicial);
  return datas;
}

function segundosSlaRestantes(chamado, agora = Date.now()) {
  let consumidos = Number(chamado.tempo_decorrido_segundos || 0);
  if (chamado.status === 'ANDAMENTO' && chamado.tempo_inicio) {
    const inicioTexto = String(chamado.tempo_inicio).replace(' ', 'T');
    const inicio = new Date(inicioTexto).getTime();
    if (!Number.isNaN(inicio)) consumidos += Math.max(0, Math.floor((agora - inicio) / 1000));
  }
  return SLA_LIMITE_SEGUNDOS - consumidos;
}

function formatarSlaRestante(segundos) {
  const absoluto = Math.abs(segundos);
  const tempo = `${String(Math.floor(absoluto / 60)).padStart(2, '0')}:${String(absoluto % 60).padStart(2, '0')}`;
  return segundos < 0 ? `+${tempo} (estourado)` : tempo;
}

function atualizarSlasVisiveis() {
  document.querySelectorAll('[data-sla-id]').forEach((elemento) => {
    const chamado = chamadosEmMemoria.find((item) => String(item.id_chamado) === elemento.dataset.slaId);
    if (!chamado) return;
    const restante = segundosSlaRestantes(chamado);
    elemento.textContent = formatarSlaRestante(restante);
    elemento.classList.toggle('is-expired', restante < 0);
  });
}

async function atualizarPerfil() {
  let nome = localStorage.getItem('workspaceName') || localStorage.getItem('perfilNome') || sessionStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => { image.src = gerarUrlAvatar(nome); });
  try {
    const configuracoes = await buscarConfiguracoes();
    nome = configuracoes.workspaceName || nome;
    localStorage.setItem('workspaceName', nome);
    localStorage.setItem('supportEmail', configuracoes.supportEmail || '');
    document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
    document.querySelectorAll('.user-avatar img').forEach((image) => { image.src = gerarUrlAvatar(nome); });
  } catch (error) {
  }
}

function abrirModalChamado() {
  document.getElementById('modalChamado')?.classList.add('active');
  const campoSetor = document.querySelector('#setorChamado');
  if (campoSetor) {
    const buscaSetor = document.querySelector('#setorSearchInput');
    const buscaTecnico = document.querySelector('#tecnicoSearchInput');
    const campoTecnico = document.querySelector('#tecnicoChamado');
    campoSetor.value = '';
    if (buscaSetor) buscaSetor.value = '';
    if (campoTecnico) campoTecnico.value = '';
    if (buscaTecnico) { buscaTecnico.value = ''; buscaTecnico.disabled = true; }
    renderizarOpcoesTecnicos();
  }
}
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
  const statuses = ['ABERTO', 'ANDAMENTO', 'AGUARDANDO', 'PAUSADO', 'RESOLVIDO'];
  const statusInformado = String(chamado.status || 'ABERTO').toUpperCase();
  const status = statuses.includes(statusInformado) ? statusInformado : 'ABERTO';
  const slaRestante = segundosSlaRestantes(chamado);
  const id = escaparHtml(chamado.id_chamado);
  return `<tr class="chamado-row" data-detalhes="${id}" tabindex="0"><td><strong>#${id}</strong></td><td>${escaparHtml(chamado.cliente)}</td><td>${escaparHtml(chamado.tecnico || 'Não atribuído')}</td><td><span class="sla-countdown${slaRestante < 0 ? ' is-expired' : ''}" data-sla-id="${id}">${formatarSlaRestante(slaRestante)}</span></td><td><div class="status-picker" data-status-picker><button class="status-trigger status-${status.toLowerCase()}" type="button" aria-haspopup="listbox" aria-expanded="false"><span class="status-dot"></span><span class="status-trigger-label">${status}</span><span class="status-chevron"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg></span></button><div class="status-menu" role="listbox">${statuses.map((item) => `<button class="status-option ${item === status ? 'is-selected' : ''}" type="button" role="option" aria-selected="${item === status}" data-status-value="${item}"><span class="status-dot"></span>${item}</button>`).join('')}</div><select class="status-select" data-id="${id}" aria-hidden="true" tabindex="-1">${statuses.map((item) => `<option value="${item}" ${item === status ? 'selected' : ''}>${item}</option>`).join('')}</select></div></td></tr>`;
}

function dataAberturaDoChamado(chamado) {
  const valor = chamado.data_abertura;
  if (!valor) return null;
  const data = new Date(valor.includes('T') ? valor : `${valor}T12:00:00`);
  return Number.isNaN(data.getTime()) ? null : data;
}

function correspondeAoPeriodoDeAbertura(chamado, periodo) {
  if (!periodo) return true;
  const dataAbertura = dataAberturaDoChamado(chamado);
  if (!dataAbertura) return false;
  const hoje = new Date();
  const inicioHoje = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const inicioAbertura = new Date(dataAbertura.getFullYear(), dataAbertura.getMonth(), dataAbertura.getDate());
  const diferencaDias = Math.floor((inicioHoje - inicioAbertura) / 86400000);
  return periodo === 'hoje' ? diferencaDias === 0
    : periodo === 'ontem' ? diferencaDias === 1
      : periodo === 'mes' ? diferencaDias >= 0 && diferencaDias < 30
        : diferencaDias >= 0 && diferencaDias < 365;
}

function aplicarFiltrosChamados() {
  const busca = document.querySelector('#buscaChamados')?.value.trim().toLowerCase() || '';
  const status = document.querySelector('#filtroStatusChamados')?.value || 'NAO_RESOLVIDOS';
  const periodo = document.querySelector('input[name="filtroAbertura"]:checked')?.value || '';
  const chamadosFiltrados = chamadosEmMemoria.filter((chamado) => {
    const correspondeBusca = [chamado.id_chamado, chamado.cliente]
      .some((valor) => String(valor || '').toLowerCase().includes(busca));
    const correspondeStatus = status === 'NAO_RESOLVIDOS'
      ? chamado.status !== 'RESOLVIDO'
      : chamado.status === status;
    return correspondeBusca && correspondeStatus && correspondeAoPeriodoDeAbertura(chamado, periodo);
  });
  const totalPaginas = Math.max(1, Math.ceil(chamadosFiltrados.length / chamadosPorPagina));
  paginaChamados = Math.min(paginaChamados, totalPaginas);
  const inicio = (paginaChamados - 1) * chamadosPorPagina;
  const chamadosDaPagina = chamadosFiltrados.slice(inicio, inicio + chamadosPorPagina);
  const tabela = document.querySelector('#tabelaChamados');
  if (tabela) tabela.innerHTML = chamadosDaPagina.map(linhaChamado).join('') || '<tr><td colspan="6">Nenhum chamado encontrado.</td></tr>';
  atualizarSlasVisiveis();
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
  const dataEscolhida = document.querySelector('#agendaData')?.value || dataLocalISO();
  if (todasDatas !== agendaModoAnterior || dataEscolhida !== ultimaDataAgenda) agendaPagina = 0;
  agendaModoAnterior = todasDatas;
  ultimaDataAgenda = dataEscolhida;
  let datas;
  const datasComChamados = [...new Set(chamadosComData.map((item) => item.data_agendada))].sort();
  if (todasDatas) {
    const datasDisponiveis = datasAgendaApartirDe(dataEscolhida, datasComChamados);
    datas = datasDisponiveis.slice(agendaPagina, agendaPagina + 5);
    if (!datas.length) datas = [dataEscolhida];
  } else {
    const dataInicio = new Date(`${dataEscolhida}T12:00:00`);
    datas = Array.from({ length: 5 }, (_, indice) => {
      const data = new Date(dataInicio);
      data.setDate(dataInicio.getDate() + indice);
      return dataLocalISO(data);
    });
  }
  const hoje = dataLocalISO();
  const anterior = document.querySelector('#agendaDiaAnterior');
  const proximo = document.querySelector('#agendaProximoDia');
  if (anterior) anterior.disabled = todasDatas && agendaPagina <= 0;
  const totalDatasDisponiveis = datasAgendaApartirDe(dataEscolhida, datasComChamados).length;
  if (anterior) anterior.disabled = todasDatas && agendaPagina <= 0;
  if (proximo) proximo.disabled = todasDatas && agendaPagina + 5 >= totalDatasDisponiveis;

  const colunas = `repeat(${Math.max(datas.length, 1)}, minmax(0, 1fr))`;
  cabecalho.style.gridTemplateColumns = colunas;
  agenda.style.gridTemplateColumns = colunas;

  cabecalho.innerHTML = datas.map((data) => `<div class="day-col-header ${data === hoje ? 'active' : ''}">${escaparHtml(formatarDataAgenda(data))}</div>`).join('');
  const classesBadge = { ABERTO: 'badge-blue', ANDAMENTO: 'badge-yellow', AGUARDANDO: 'badge-yellow', PAUSADO: 'badge-yellow', RESOLVIDO: 'badge-green' };
  agenda.innerHTML = datas.map((data) => {
    const chamadosDoDia = chamadosComData.filter((item) => item.data_agendada === data);
    const cards = chamadosDoDia.map((item) => {
      const statusInformado = String(item.status || 'ABERTO').toUpperCase();
      const status = Object.hasOwn(classesBadge, statusInformado) ? statusInformado : 'ABERTO';
      const id = escaparHtml(item.id_chamado);
      return `<a class="ticket-card-agenda status-${status.toLowerCase()}" href="chamados-detalhe.html?id=${encodeURIComponent(item.id_chamado)}"><strong>#${id} - ${escaparHtml(item.cliente)}</strong><span class="badge ${classesBadge[status]}">${status}</span></a>`;
    }).join('') || '<span class="agenda-empty-day">Nenhum chamado nesta data.</span>';
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

function mudarDia(dias) {
  if (document.querySelector('#agendaTodasDatas')?.checked) {
    const dataEscolhida = document.querySelector('#agendaData')?.value || dataLocalISO();
    const datasComChamados = [...new Set(chamadosEmMemoria.filter((item) => {
      if (!item.data_agendada) return false;
      const diaDaSemana = new Date(`${item.data_agendada}T12:00:00`).getDay();
      return diaDaSemana >= 1 && diaDaSemana <= 5;
    }).map((item) => item.data_agendada))];
    const totalDatas = datasAgendaApartirDe(dataEscolhida, datasComChamados).length;
    const ultimaPagina = Math.max(0, Math.ceil(totalDatas / 5) * 5 - 5);
    agendaPagina = Math.min(ultimaPagina, Math.max(0, agendaPagina + (dias * 5)));
    renderizarAgenda(chamadosEmMemoria);
    return;
  }
  const campo = document.querySelector('#agendaData');
  if (!campo) return;
  const data = new Date(`${campo.value || dataLocalISO()}T12:00:00`);
  data.setDate(data.getDate() + (dias * 5));
  campo.value = dataLocalISO(data);
  const label = document.querySelector('#agendaDataLabel');
  if (label) label.textContent = formatarDataCurtaAgenda(campo.value);
  filtrarAgenda();
}

let clientesDoChamado = [];
let setoresDoChamado = [];
let equipeDoChamado = [];

function normalizarBusca(valor) {
  return String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function escaparHtml(valor) {
  return String(valor || '').replace(/[&<>'"]/g, (caractere) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[caractere]);
}

function renderizarOpcoesClientes(termo = '') {
  const lista = document.querySelector('#clienteDropdownList');
  if (!lista) return;
  const busca = normalizarBusca(termo);
  const clientes = clientesDoChamado.filter((cliente) => normalizarBusca(`${cliente.nome} ${cliente.telefone} ${cliente.email}`).includes(busca));
  lista.innerHTML = clientes.length
    ? clientes.map((cliente) => `<li data-cliente-id="${escaparHtml(cliente.id_usuario)}"><strong>${escaparHtml(cliente.nome)}</strong><span>${escaparHtml(cliente.telefone || 'Telefone não informado')} · ${escaparHtml(cliente.email || 'E-mail não informado')}</span></li>`).join('')
    : '<li class="select-empty">Nenhum cliente encontrado.</li>';
}

function selecionarClienteChamado(cliente) {
  const campoBusca = document.querySelector('#clienteSearchInput');
  const campoCliente = document.querySelector('#clienteChamado');
  const campoEmail = document.querySelector('#emailClienteChamado');
  const campoTelefone = document.querySelector('#telefoneClienteChamado');
  if (!campoBusca || !campoCliente) return;
  campoBusca.value = cliente.nome || '';
  campoCliente.value = cliente.nome || '';
  if (campoEmail) campoEmail.value = cliente.email || '';
  if (campoTelefone) campoTelefone.value = formatBrazilianPhone(cliente.telefone || '');
  const campoContato = document.querySelector('#funcionarioSearchInput');
  if (campoContato) campoContato.value = cliente.contato || '';
  document.querySelector('#clienteDropdownList')?.classList.add('hidden');
}

async function carregarClientesNoChamado() {
  const campoBusca = document.querySelector('#clienteSearchInput');
  if (!campoBusca) return;
  try {
    clientesDoChamado = await buscarClientes();
    renderizarOpcoesClientes();
  } catch (error) {
    const lista = document.querySelector('#clienteDropdownList');
    if (lista) lista.innerHTML = '<li class="select-empty">Não foi possível carregar clientes.</li>';
  }
}

function renderizarOpcoesTecnicos(idSetor = '') {
  const campo = document.querySelector('#tecnicoChamado');
  if (!campo) return;
  const tecnicos = equipeDoChamado.filter((membro) => String(membro.id_setor) === String(idSetor) && (membro.status || 'ATIVO') === 'ATIVO');
  const busca = document.querySelector('#tecnicoSearchInput');
  const lista = document.querySelector('#tecnicoDropdownList');
  if (!busca || !lista) return;
  campo.value = '';
  busca.value = '';
  busca.disabled = !idSetor || !tecnicos.length;
  lista.innerHTML = idSetor && tecnicos.length
    ? tecnicos.map((membro) => `<li data-tecnico-id="${escaparHtml(membro.id_grupo_solucionadores)}"><strong>${escaparHtml(membro.nome || membro.descricao || 'Técnico')}</strong><span>${escaparHtml(membro.cargo || membro.email || 'Técnico disponível')}</span></li>`).join('')
    : `<li class="select-empty">${idSetor ? 'Nenhum técnico disponível' : 'Selecione primeiro o setor'}</li>`;
}

function renderizarOpcoesSetores(termo = '') {
  const lista = document.querySelector('#setorDropdownList');
  if (!lista) return;
  const busca = normalizarBusca(termo);
  const setores = setoresDoChamado.filter((setor) => normalizarBusca(setor.nome).includes(busca));
  lista.innerHTML = setores.length
    ? setores.map((setor) => `<li data-setor-id="${escaparHtml(setor.id_setor)}"><strong>${escaparHtml(setor.nome)}</strong><span>${escaparHtml(setor.descricao || 'Setor de atendimento')}</span></li>`).join('')
    : '<li class="select-empty">Nenhum setor encontrado.</li>';
}

function filtrarOpcoesTecnicos(termo = '') {
  const lista = document.querySelector('#tecnicoDropdownList');
  const idSetor = document.querySelector('#setorChamado')?.value || '';
  if (!lista) return;
  const busca = normalizarBusca(termo);
  const tecnicos = equipeDoChamado.filter((membro) => String(membro.id_setor) === String(idSetor) && (membro.status || 'ATIVO') === 'ATIVO' && normalizarBusca(`${membro.nome || ''} ${membro.descricao || ''} ${membro.cargo || ''} ${membro.email || ''}`).includes(busca));
  lista.innerHTML = tecnicos.length
    ? tecnicos.map((membro) => `<li data-tecnico-id="${escaparHtml(membro.id_grupo_solucionadores)}"><strong>${escaparHtml(membro.nome || membro.descricao || 'Técnico')}</strong><span>${escaparHtml(membro.cargo || membro.email || 'Técnico disponível')}</span></li>`).join('')
    : '<li class="select-empty">Nenhum técnico encontrado.</li>';
}

function configurarBuscaResponsaveis() {
  const buscaSetor = document.querySelector('#setorSearchInput');
  const campoSetor = document.querySelector('#setorChamado');
  const listaSetor = document.querySelector('#setorDropdownList');
  const buscaTecnico = document.querySelector('#tecnicoSearchInput');
  const campoTecnico = document.querySelector('#tecnicoChamado');
  const listaTecnico = document.querySelector('#tecnicoDropdownList');
  if (!buscaSetor || !campoSetor || !listaSetor || !buscaTecnico || !campoTecnico || !listaTecnico) return;

  buscaSetor.addEventListener('focus', () => { renderizarOpcoesSetores(buscaSetor.value); listaSetor.classList.remove('hidden'); });
  buscaSetor.addEventListener('input', () => {
    campoSetor.value = '';
    renderizarOpcoesTecnicos();
    renderizarOpcoesSetores(buscaSetor.value);
    listaSetor.classList.remove('hidden');
  });
  listaSetor.addEventListener('click', (event) => {
    const opcao = event.target.closest('[data-setor-id]');
    if (!opcao) return;
    const setor = setoresDoChamado.find((item) => String(item.id_setor) === opcao.dataset.setorId);
    if (!setor) return;
    buscaSetor.value = setor.nome || '';
    campoSetor.value = setor.id_setor;
    listaSetor.classList.add('hidden');
    renderizarOpcoesTecnicos(campoSetor.value);
  });
  buscaTecnico.addEventListener('focus', () => { filtrarOpcoesTecnicos(buscaTecnico.value); listaTecnico.classList.remove('hidden'); });
  buscaTecnico.addEventListener('input', () => { campoTecnico.value = ''; filtrarOpcoesTecnicos(buscaTecnico.value); listaTecnico.classList.remove('hidden'); });
  listaTecnico.addEventListener('click', (event) => {
    const opcao = event.target.closest('[data-tecnico-id]');
    if (!opcao) return;
    const tecnico = equipeDoChamado.find((item) => String(item.id_grupo_solucionadores) === opcao.dataset.tecnicoId);
    if (!tecnico) return;
    buscaTecnico.value = tecnico.nome || tecnico.descricao || 'Técnico';
    campoTecnico.value = tecnico.id_grupo_solucionadores;
    listaTecnico.classList.add('hidden');
  });
  document.addEventListener('click', (event) => {
    if (!document.querySelector('#selectSetorWrapper')?.contains(event.target)) listaSetor.classList.add('hidden');
    if (!document.querySelector('#selectTecnicoWrapper')?.contains(event.target)) listaTecnico.classList.add('hidden');
  });
}

async function carregarResponsaveisDoChamado() {
  const campoSetor = document.querySelector('#setorChamado');
  if (!campoSetor) return;
  try {
    [setoresDoChamado, equipeDoChamado] = await Promise.all([buscarSetores(), buscarEquipe()]);
    renderizarOpcoesSetores();
    renderizarOpcoesTecnicos();
  } catch (error) {
    const listaSetor = document.querySelector('#setorDropdownList');
    if (listaSetor) listaSetor.innerHTML = '<li class="select-empty">Não foi possível carregar os setores.</li>';
    renderizarOpcoesTecnicos();
  }
}

function configurarBuscaClienteChamado() {
  const campoBusca = document.querySelector('#clienteSearchInput');
  const campoCliente = document.querySelector('#clienteChamado');
  const lista = document.querySelector('#clienteDropdownList');
  if (!campoBusca || !campoCliente || !lista) return;

  const abrirLista = () => {
    renderizarOpcoesClientes(campoBusca.value);
    lista.classList.remove('hidden');
  };
  campoBusca.addEventListener('focus', abrirLista);
  campoBusca.addEventListener('click', abrirLista);
  campoBusca.addEventListener('input', () => {
    if (campoBusca.value !== campoCliente.value) {
      campoCliente.value = '';
      document.querySelector('#emailClienteChamado').value = '';
      document.querySelector('#telefoneClienteChamado').value = '';
      document.querySelector('#funcionarioSearchInput').value = '';
      document.querySelector('#telefoneFuncionarioChamado').value = '';
    }
    abrirLista();
  });
  campoBusca.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') lista.classList.add('hidden');
  });
  lista.addEventListener('click', (event) => {
    const opcao = event.target.closest('[data-cliente-id]');
    if (!opcao) return;
    const cliente = clientesDoChamado.find((item) => String(item.id_usuario) === opcao.dataset.clienteId);
    if (cliente) selecionarClienteChamado(cliente);
  });
  document.addEventListener('click', (event) => {
    if (!document.querySelector('#selectClienteWrapper')?.contains(event.target)) lista.classList.add('hidden');
  });
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
  const botao = form.querySelector('[type="submit"]');
  await comCarregamento(botao, async () => { try {
    const cliente = await criarCliente({ nome: campos.nome.value.trim(), telefone: campos.telefone.value.trim(), contato: campos.contato.value.trim(), email: campos.email.value.trim() });
    await carregarClientesNoChamado();
    document.querySelector('#clienteChamado').value = cliente.nome;
    document.querySelector('#clienteSearchInput').value = cliente.nome;
    document.querySelector('#emailClienteChamado').value = cliente.email || '';
    form.reset();
    cancelarNovoClienteDoChamado();
    mostrarNotificacao('Cliente cadastrado com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível cadastrar o cliente: ${error.message}`); } }, 'Salvando...');
}

async function salvarChamado(event) {
  event.preventDefault();
  const form = event.target;
  const campos = form.elements;
  if (!campos.cliente.value || !campos.email_cliente.value || !campos.telefone_cliente.value || !campos.contato_cliente.value.trim() || !campos.telefone_contato.value.trim() || !campos.id_setor.value || !campos.id_grupo_solucionadores.value || !campos.descricao.value.trim()) {
    form.reportValidity();
    return;
  }
  const botao = form.querySelector('[type="submit"]');
  await comCarregamento(botao, async () => { try {
    await criarChamado({
      cliente: campos.cliente.value.trim(),
      email_cliente: campos.email_cliente.value.trim(),
      telefone_cliente: formatBrazilianPhone(campos.telefone_cliente.value),
      contato_cliente: campos.contato_cliente.value.trim(),
      telefone_contato: formatBrazilianPhone(campos.telefone_contato.value),
      id_setor: campos.id_setor.value,
      id_grupo_solucionadores: campos.id_grupo_solucionadores.value,
      descricao: campos.descricao.value.trim()
    });
    fecharModalChamado(); form.reset(); await carregarChamados(); mostrarNotificacao('Chamado criado com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível criar o chamado: ${error.message}`); } }, 'Abrindo chamado...');
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
  const statusFilterButton = event.target.closest('#botaoStatusChamados');
  if (statusFilterButton) {
    const controle = statusFilterButton.closest('.status-filter-control');
    const aberto = !controle.classList.contains('is-open');
    document.querySelector('.chamados-filter-control.is-open')?.classList.remove('is-open');
    document.querySelector('#botaoFiltroChamados')?.setAttribute('aria-expanded', 'false');
    controle.classList.toggle('is-open', aberto);
    statusFilterButton.setAttribute('aria-expanded', String(aberto));
    return;
  }

  const chamadosFilterButton = event.target.closest('#botaoFiltroChamados');
  if (chamadosFilterButton) {
    const controle = chamadosFilterButton.closest('.chamados-filter-control');
    const aberto = !controle.classList.contains('is-open');
    document.querySelector('.status-filter-control.is-open')?.classList.remove('is-open');
    document.querySelector('#botaoStatusChamados')?.setAttribute('aria-expanded', 'false');
    controle.classList.toggle('is-open', aberto);
    chamadosFilterButton.setAttribute('aria-expanded', String(aberto));
    return;
  }

  const limparFiltroAbertura = event.target.closest('#limparFiltroAbertura');
  if (limparFiltroAbertura) {
    document.querySelectorAll('input[name="filtroAbertura"]').forEach((opcao) => { opcao.checked = false; });
    paginaChamados = 1;
    aplicarFiltrosChamados();
    return;
  }

  const filtroAbertura = event.target.closest('input[name="filtroAbertura"]');
  if (filtroAbertura) {
    const selecionado = filtroAbertura.checked;
    document.querySelectorAll('input[name="filtroAbertura"]').forEach((opcao) => {
      opcao.checked = opcao === filtroAbertura && selecionado;
    });
    paginaChamados = 1;
    aplicarFiltrosChamados();
    return;
  }

  const statusFilterOption = event.target.closest('[data-status-filter]');
  if (statusFilterOption) {
    const valor = statusFilterOption.dataset.statusFilter;
    const select = document.querySelector('#filtroStatusChamados');
    const controle = statusFilterOption.closest('.status-filter-control');
    if (select) select.value = valor;
    document.querySelector('#statusChamadosLabel').textContent = statusFilterOption.textContent;
    controle.classList.remove('is-open');
    document.querySelector('#botaoStatusChamados')?.setAttribute('aria-expanded', 'false');
    controle.querySelectorAll('[data-status-filter]').forEach((option) => option.setAttribute('aria-selected', String(option === statusFilterOption)));
    paginaChamados = 1;
    aplicarFiltrosChamados();
    return;
  }

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
      mostrarNotificacao('Status do chamado atualizado com sucesso.');
    } catch (error) {
      select.value = statusAnterior;
      await carregarChamados();
      mostrarErro(`Não foi possível atualizar o status: ${error.message}`);
    }
    return;
  }

  document.querySelectorAll('[data-status-picker].is-open').forEach((picker) => {
    picker.classList.remove('is-open');
    const menu = picker.querySelector('.status-menu');
    if (menu) menu.removeAttribute('style');
    picker.querySelector('.status-trigger')?.setAttribute('aria-expanded', 'false');
  });
  document.querySelector('.status-filter-control.is-open')?.classList.remove('is-open');
  document.querySelector('#botaoStatusChamados')?.setAttribute('aria-expanded', 'false');
  document.querySelector('.chamados-filter-control.is-open')?.classList.remove('is-open');
  document.querySelector('#botaoFiltroChamados')?.setAttribute('aria-expanded', 'false');

  const row = event.target.closest('.chamado-row');
  if (row && !event.target.closest('[data-status-picker]')) {
    window.location.href = `chamados-detalhe.html?id=${encodeURIComponent(row.dataset.detalhes)}`;
  }
});

window.addEventListener('resize', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
});

window.addEventListener('scroll', () => {
  document.querySelectorAll('[data-status-picker].is-open').forEach(posicionarMenuStatus);
}, true);

document.addEventListener('DOMContentLoaded', () => {
  atualizarPerfil();
  const statusInicial = new URLSearchParams(window.location.search).get('status');
  const filtroStatus = document.querySelector('#filtroStatusChamados');
  if (statusInicial === 'RESOLVIDO' && filtroStatus) {
    filtroStatus.value = statusInicial;
    const opcaoResolvidos = document.querySelector('[data-status-filter="RESOLVIDO"]');
    if (opcaoResolvidos) {
      document.querySelector('#statusChamadosLabel').textContent = opcaoResolvidos.textContent;
      document.querySelectorAll('[data-status-filter]').forEach((opcao) => {
        opcao.setAttribute('aria-selected', String(opcao === opcaoResolvidos));
      });
    }
  }
  const agendaData = document.querySelector('#agendaData');
  if (agendaData && !agendaData.value) agendaData.value = dataLocalISO();
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
  document.querySelector('#hojeCalendarioAgenda')?.addEventListener('click', () => selecionarDataAgenda(dataLocalISO()));
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
  configurarBuscaClienteChamado();
  configurarBuscaResponsaveis();
  carregarClientesNoChamado();
  carregarResponsaveisDoChamado();
  carregarChamados().catch((error) => {
    const tabela = document.querySelector('#tabelaChamados');
    const agenda = document.querySelector('#agendaDinamica');
    if (tabela) tabela.innerHTML = `<tr><td colspan="6">Não foi possível carregar: ${escaparHtml(error.message)}</td></tr>`;
    if (agenda) agenda.innerHTML = `<p>Não foi possível carregar a agenda: ${escaparHtml(error.message)}</p>`;
  });
  window.setInterval(atualizarSlasVisiveis, 1000);
});
