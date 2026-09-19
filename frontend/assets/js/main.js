import { buscarChamados, buscarClientes, atualizarCliente, excluirCliente, atualizarMembro, excluirMembro } from './api.js';

const loginExpiraEm = Number(localStorage.getItem('loginExpiraEm') || 0);
if (localStorage.getItem('grupoId') && (!loginExpiraEm || loginExpiraEm <= Date.now())) {
  localStorage.removeItem('grupoId');
  localStorage.removeItem('perfilNome');
  localStorage.removeItem('loginExpiraEm');
  localStorage.removeItem('emailLembrado');
}

if (!localStorage.getItem('grupoId') && !sessionStorage.getItem('grupoId')) {
  window.location.replace('login.html');
}

function openModal(id) {
  document.getElementById(id)?.classList.add('active');
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove('active');
}

function toggleProfileMenu(event) {
  event.stopPropagation();
  document.getElementById('profileDropdown')?.classList.toggle('active');
}

function mostrarPerfil() {
  const nome = localStorage.getItem('workspaceName') || localStorage.getItem('perfilNome') || sessionStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => {
    image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`;
  });
}

let clientesEmMemoria = [];

function renderizarClientes(clientes) {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  tabela.innerHTML = clientes.map((cliente) => `<tr onclick="window.location.href='cliente-detalhe.html?id=${cliente.id_usuario}'" style="cursor: pointer;"><td><strong>${cliente.nome || '-'}</strong></td><td>${cliente.cnpj || '-'}<br>${cliente.contato || ''}</td><td><span class="status-badge status-success">${cliente.status || 'Ativo'}</span></td></tr>`).join('') || '<tr><td colspan="5">Nenhum cliente encontrado.</td></tr>';
}

function filtrarClientes() {
  const termo = document.querySelector('#buscaClientes')?.value.trim().toLowerCase() || '';
  const camposMarcados = [...document.querySelectorAll('#menuFiltroClientes input[type="checkbox"]:checked')]
    .map((checkbox) => checkbox.value);
  const camposBusca = camposMarcados.length ? camposMarcados : ['nome', 'cnpj', 'contato', 'email', 'telefone', 'plano', 'status'];
  const clientesFiltrados = clientesEmMemoria.filter((cliente) => camposBusca
    .some((campoCliente) => normalizarTexto(campoCliente === 'status' ? (cliente.status || 'Ativo') : cliente[campoCliente] || '').includes(normalizarTexto(termo))));
  renderizarClientes(clientesFiltrados);
}

function normalizarTexto(valor) {
  return String(valor || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function configurarFiltroClientes() {
  const controle = document.querySelector('.client-filter-control');
  const botao = document.querySelector('#botaoFiltroClientes');
  const menu = document.querySelector('#menuFiltroClientes');
  if (!controle || !botao || !menu) return;

  botao.addEventListener('click', (event) => {
    event.stopPropagation();
    const aberto = controle.classList.toggle('is-open');
    botao.setAttribute('aria-expanded', String(aberto));
  });

  menu.addEventListener('change', (event) => {
    if (!event.target.matches('input[type="checkbox"]')) return;
    filtrarClientes();
  });

  document.querySelector('#filtroClientes')?.addEventListener('change', (event) => {
    const campo = event.target.value;
    if (!campo) return;
    const checkbox = menu.querySelector(`input[value="${campo}"]`);
    if (checkbox) checkbox.checked = true;
    filtrarClientes();
  });
}

async function carregarClientes() {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  try {
    const { buscarClientes } = await import('./api.js');
    clientesEmMemoria = await buscarClientes();
    renderizarClientes(clientesEmMemoria);
  } catch (error) { tabela.innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`; }
}

async function salvarCliente(event) {
  event.preventDefault();
  const form = event.target;
  const dados = Object.fromEntries([...form.elements]
    .filter((element) => element.name)
    .map((element) => [element.name, element.value.trim()]));
  try {
    const { criarCliente } = await import('./api.js');
    await criarCliente(dados);
    closeModal('modal-cliente'); form.reset(); await carregarClientes(); alert('Cliente cadastrado com sucesso.');
  } catch (error) { alert(`Não foi possível cadastrar: ${error.message}`); }
}

async function carregarEquipe() {
  const tabela = document.querySelector('#tabelaEquipe');
  if (!tabela) return;
  try {
    const { buscarEquipe } = await import('./api.js');
    const equipe = await buscarEquipe();
    tabela.innerHTML = equipe.map((membro) => `<tr onclick="window.location.href='equipe-detalhe.html?id=${membro.id_grupo_solucionadores}'" style="cursor: pointer;"><td><strong>${membro.nome || membro.descricao || '-'}</strong></td><td>${membro.cargo || '-'}</td><td>${membro.setor_nome || 'Sem setor'}</td><td><span class="status-badge status-info">${membro.status || 'ATIVO'}</span></td></tr>`).join('') || '<tr><td colspan="4">Nenhum membro cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="4">${error.message}</td></tr>`; }
}

let setoresEmMemoria = [];
let equipeEmMemoria = [];

async function carregarSetores() {
  const tabela = document.querySelector('#tabelaSetores');
  if (!tabela) return;
  try {
    const { buscarSetores, buscarEquipe } = await import('./api.js');
    [setoresEmMemoria, equipeEmMemoria] = await Promise.all([buscarSetores(), buscarEquipe()]);
    const lista = document.querySelector('#setores-disponiveis');
    if (lista) lista.innerHTML = setoresEmMemoria.map((setor) => `<option value="${setor.nome}"></option>`).join('');
    tabela.innerHTML = setoresEmMemoria.map((setor) => renderizarSetor(setor)).join('') || '<tr><td colspan="3">Nenhum setor cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="3">${error.message}</td></tr>`; }
}

function iconeNivel(icone) {
  const caminhos = icone === 'plus'
    ? '<path d="M5 12h14"/><path d="M12 5v14" />'
    : '<path d="m9 18 6-6-6-6" />';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${caminhos}</svg>`;
}

function renderizarSetor(setor) {
  const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == setor.id_setor);
  const lista = participantes.map((membro) => `<li><a href="equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}"><strong>${membro.nome || '-'}</strong><span>${membro.cargo || 'Sem função'}</span></a></li>`).join('') || '<li class="empty-row">Nenhum participante neste setor.</li>';
  const niveis = (setor.niveis || []).map((nivel, indice) => {
    const membros = participantes.filter((membro) => Number(membro.nivel) === indice + 1).length;
    return `<div class="sector-level-row"><div><strong>${nivel}</strong><small>${membros} funcionário(s) alocado(s)</small></div><div class="level-actions"><button type="button" class="level-action" title="Ver detalhes de ${nivel}" aria-label="Ver detalhes de ${nivel}" data-level-action="details" data-setor-id="${setor.id_setor}" data-level-index="${indice + 1}">${iconeNivel('chevron')}</button><button type="button" class="level-action" title="Adicionar funcionário em ${nivel}" aria-label="Adicionar funcionário em ${nivel}" data-level-action="add" data-setor-id="${setor.id_setor}" data-level-index="${indice + 1}">${iconeNivel('plus')}</button></div></div>`;
  }).join('');
  return `<tr><td colspan="3"><details class="sector-details"><summary><span><strong>${setor.nome}</strong><small>${setor.niveis?.length ? `${setor.niveis.length} nível(is)` : 'Sem níveis cadastrados'}</small></span><span class="status-badge status-info">${participantes.length} participante(s)</span></summary>${niveis ? `<div class="sector-levels">${niveis}</div>` : ''}<ul class="sector-members">${lista}</ul></details></td></tr>`;
}

function obterNivelAtual() {
  return window.nivelSelecionado || { setorId: null, nivel: null };
}

function membrosDoNivel(setorId, nivel) {
  return equipeEmMemoria.filter((membro) => membro.id_setor == setorId && Number(membro.nivel) === Number(nivel));
}

function opcoesDeNiveis(setor) {
  return (setor.niveis || []).map((nivel, indice) => `<option value="${indice + 1}">${nivel}</option>`).join('');
}

function abrirDetalhesNivel(setorId, nivel) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == setorId);
  if (!setor) return;
  window.nivelSelecionado = { setorId, nivel };
  document.querySelector('#nivel-titulo').textContent = setor.niveis[nivel - 1] || `Nível ${nivel}`;
  document.querySelector('#nivel-setor').textContent = setor.nome;
  const membros = membrosDoNivel(setorId, nivel);
  document.querySelector('#nivel-membros').innerHTML = membros.length ? membros.map((membro) => `<div class="level-member-row"><div><strong>${membro.nome || '-'}</strong><small>${membro.email || 'Sem e-mail'}</small></div><div class="level-member-actions"><select data-member-level="${membro.id_grupo_solucionadores}" aria-label="Nível de ${membro.nome}">${opcoesDeNiveis(setor)}</select><button type="button" class="level-remove-button" data-remove-member="${membro.id_grupo_solucionadores}">Remover</button></div></div>`).join('') : '<p class="empty-row">Nenhum funcionário neste nível.</p>';
  document.querySelectorAll('[data-member-level]').forEach((select) => {
    select.value = String(nivel);
    select.addEventListener('change', () => alterarNivelFuncionario(select.dataset.memberLevel, setorId, select.value));
  });
  document.querySelectorAll('[data-remove-member]').forEach((button) => button.addEventListener('click', () => removerFuncionarioNivel(button.dataset.removeMember)));
  openModal('modal-nivel');
}

function abrirAdicionarFuncionarioNivel(setorId, nivel) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == setorId);
  if (!setor) return;
  window.nivelSelecionado = { setorId, nivel };
  const alocados = new Set(membrosDoNivel(setorId, nivel).map((membro) => String(membro.id_grupo_solucionadores)));
  const disponiveis = equipeEmMemoria.filter((membro) => !alocados.has(String(membro.id_grupo_solucionadores)));
  document.querySelector('#adicionar-nivel-titulo').textContent = `${setor.niveis[nivel - 1] || `Nível ${nivel}`} · ${setor.nome}`;
  document.querySelector('#funcionarios-disponiveis').innerHTML = disponiveis.length ? disponiveis.map((membro) => `<label class="available-member-row"><input type="checkbox" value="${membro.id_grupo_solucionadores}"><span><strong>${membro.nome || '-'}</strong><small>${membro.setor_nome || 'Sem setor'} · ${membro.nivel ? `Nível ${membro.nivel}` : 'Sem nível alocado'}</small></span></label>`).join('') : '<p class="empty-row">Todos os funcionários já estão neste nível.</p>';
  openModal('modal-adicionar-nivel');
}

async function alterarNivelFuncionario(id, setorId, nivel) {
  try {
    const { atualizarMembro } = await import('./api.js');
    await atualizarMembro(id, { nivel: Number(nivel), id_setor: setorId });
    await carregarSetores();
    abrirDetalhesNivel(setorId, Number(nivel));
  } catch (error) { alert(`Não foi possível alterar o nível: ${error.message}`); }
}

async function removerFuncionarioNivel(id) {
  const { setorId, nivel } = obterNivelAtual();
  try {
    const { atualizarMembro } = await import('./api.js');
    await atualizarMembro(id, { nivel: null });
    await carregarSetores();
    abrirDetalhesNivel(setorId, nivel);
  } catch (error) { alert(`Não foi possível remover o funcionário do nível: ${error.message}`); }
}

async function adicionarFuncionariosSelecionados() {
  const { setorId, nivel } = obterNivelAtual();
  const selecionados = [...document.querySelectorAll('#funcionarios-disponiveis input:checked')].map((input) => input.value);
  if (!selecionados.length) return;
  try {
    const { atualizarMembro } = await import('./api.js');
    await Promise.all(selecionados.map((id) => atualizarMembro(id, { nivel, id_setor: setorId })));
    closeModal('modal-adicionar-nivel');
    await carregarSetores();
  } catch (error) { alert(`Não foi possível adicionar os funcionários: ${error.message}`); }
}

function mostrarParticipantes(idSetor) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == idSetor);
  const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == idSetor);
  document.querySelector('#participantes-titulo').textContent = setor ? `Participantes: ${setor.nome}` : 'Participantes';
  document.querySelector('#lista-participantes').innerHTML = participantes.map((membro) => `<div class="participant-item"><strong>${membro.nome || '-'}</strong><span>${membro.cargo || 'Sem função'}</span></div>`).join('') || '<p class="empty-row">Nenhum participante neste setor.</p>';
  openModal('modal-participantes');
}

async function salvarSetor(event) {
  event.preventDefault();
  const form = event.target;
  const possuiNivel = form.querySelector('#possui-nivel').checked;
  const niveis = possuiNivel ? [...form.querySelectorAll('#levels-list input')].map((input) => input.value.trim()).filter(Boolean) : [];
  if (possuiNivel && !niveis.length) {
    alert('Adicione pelo menos um nível para este setor.');
    return;
  }
  try {
    const { criarSetor } = await import('./api.js');
    await criarSetor({ nome: form.elements.nome.value.trim(), niveis });
    closeModal('modal-setor');
    form.reset();
    document.querySelector('#levels-list').innerHTML = '';
    document.querySelector('#levels-editor').hidden = true;
    await carregarSetores();
    alert('Setor criado com sucesso.');
  } catch (error) { alert(`Não foi possível criar o setor: ${error.message}`); }
}

function adicionarNivel() {
  const lista = document.querySelector('#levels-list');
  if (!lista) return;
  const numero = lista.children.length + 1;
  const item = document.createElement('div');
  item.className = 'level-row';
  item.innerHTML = `<input name="nivel" type="text" value="Nível ${numero}" aria-label="Nível ${numero}" readonly><button type="button" class="level-remove" aria-label="Remover Nível ${numero}">&times;</button>`;
  item.querySelector('.level-remove').addEventListener('click', () => {
    item.remove();
    [...lista.querySelectorAll('input')].forEach((input, index) => { input.value = `Nível ${index + 1}`; input.setAttribute('aria-label', `Nível ${index + 1}`); });
  });
  lista.appendChild(item);
}

function configurarModalSetor() {
  const checkbox = document.querySelector('#possui-nivel');
  const editor = document.querySelector('#levels-editor');
  if (!checkbox || !editor) return;
  checkbox.addEventListener('change', () => {
    editor.hidden = !checkbox.checked;
    if (checkbox.checked && !document.querySelector('#levels-list').children.length) adicionarNivel();
  });
  document.querySelector('#adicionar-nivel')?.addEventListener('click', adicionarNivel);
}

async function salvarMembro(event) {
  event.preventDefault();
  const form = event.target;
  const setorNome = form.elements.setor.value.trim();
  try {
    const { criarMembro, criarSetor } = await import('./api.js');
    let setor = setoresEmMemoria.find((item) => item.nome.trim().toLowerCase() === setorNome.toLowerCase());
    if (!setor) setor = await criarSetor({ nome: setorNome, descricao: '' });
    await criarMembro({
      nome: form.elements.nome.value.trim(),
      email: form.elements.email.value.trim(),
      cargo: form.elements.cargo.value,
      valor_hora: form.elements.valor_hora.value,
      id_setor: setor.id_setor,
      senha: form.elements.senha.value
    });
    closeModal('modal-equipe'); form.reset(); await carregarSetores(); await carregarEquipe(); alert('Membro cadastrado com sucesso.');
  } catch (error) { alert(`Não foi possível cadastrar: ${error.message}`); }
}

async function salvarConfiguracoes(event) {
  event.preventDefault();
  const formulario = event.target;
  const botao = formulario.querySelector('button[type="submit"]');
  const dados = {
    workspaceName: document.getElementById('workspaceName')?.value.trim(),
    supportEmail: document.getElementById('supportEmail')?.value.trim()
  };
  if (!dados.workspaceName || !dados.supportEmail) {
    alert('Preencha o nome do workspace e o e-mail de suporte.');
    return;
  }
  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    const { salvarConfiguracoes: salvar } = await import('./api.js');
    const configuracoesSalvas = await salvar(dados);
    document.getElementById('workspaceName').value = configuracoesSalvas.workspaceName;
    document.getElementById('supportEmail').value = configuracoesSalvas.supportEmail;
    localStorage.setItem('workspaceName', configuracoesSalvas.workspaceName);
    localStorage.setItem('supportEmail', configuracoesSalvas.supportEmail);
    alert('Configurações salvas com sucesso.');
    window.location.href = 'dashboard.html';
  } catch (error) {
    alert(`Não foi possível salvar: ${error.message}`);
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar alterações';
  }
}

function cancelarConfigurações() {
  window.location.href = 'dashboard.html';
}

function encerrarSessao(event) {
  event.preventDefault();
  localStorage.removeItem('usuarioId');
  localStorage.removeItem('grupoId');
  localStorage.removeItem('perfilNome');
  localStorage.removeItem('loginExpiraEm');
  localStorage.removeItem('emailLembrado');
  sessionStorage.removeItem('grupoId');
  sessionStorage.removeItem('perfilNome');
  window.location.href = 'login.html';
}

window.openModal = openModal;
window.closeModal = closeModal;
window.toggleProfileMenu = toggleProfileMenu;
window.salvarCliente = salvarCliente;
window.salvarMembro = salvarMembro;
window.salvarSetor = salvarSetor;
window.salvarConfiguracoes = salvarConfiguracoes;
window.cancelarConfigurações = cancelarConfigurações;
window.abrirDetalhesNivel = abrirDetalhesNivel;
window.abrirAdicionarFuncionarioNivel = abrirAdicionarFuncionarioNivel;

document.addEventListener('click', () => document.getElementById('profileDropdown')?.classList.remove('active'));
document.addEventListener('click', (event) => {
  const action = event.target.closest('[data-level-action]');
  if (!action) return;
  event.preventDefault();
  event.stopPropagation();
  const setorId = action.dataset.setorId;
  const nivel = Number(action.dataset.levelIndex);
  if (action.dataset.levelAction === 'details') abrirDetalhesNivel(setorId, nivel);
  if (action.dataset.levelAction === 'add') abrirAdicionarFuncionarioNivel(setorId, nivel);
});
document.querySelector('#confirmar-adicao-nivel')?.addEventListener('click', adicionarFuncionariosSelecionados);
document.addEventListener('click', (event) => {
  const controle = document.querySelector('.client-filter-control');
  if (controle && !controle.contains(event.target)) {
    controle.classList.remove('is-open');
    document.querySelector('#botaoFiltroClientes')?.setAttribute('aria-expanded', 'false');
  }
});
document.querySelector('a[href="login.html"]')?.addEventListener('click', encerrarSessao);
document.addEventListener('DOMContentLoaded', () => { mostrarPerfil(); carregarClientes(); carregarEquipe(); carregarSetores(); configurarModalSetor(); });
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('#buscaClientes')?.addEventListener('input', filtrarClientes);
  configurarFiltroClientes();
});

document.addEventListener('DOMContentLoaded', async () => {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const idSelecionado = params.get('id');

  if (false && path.includes('chamados-detalhe.html') && idSelecionado) {
    const { buscarChamadoPorId } = await import('./api.js');
    const chamado = await buscarChamadoPorId(idSelecionado);
    if (chamado) {
      document.getElementById('chamado-id').textContent = `Chamado #${chamado.id_chamado} - ${chamado.assunto}`;
      document.getElementById('chamado-assunto').textContent = 'Detalhes da solicitação de atendimento';
      document.getElementById('chamado-cliente').textContent = chamado.cliente;
      document.getElementById('chamado-prioridade').textContent = chamado.prioridade;
      document.getElementById('chamado-status').textContent = chamado.status;
      document.getElementById('chamado-descricao').textContent = chamado.descricao || 'Sem descrição cadastrada.';
    }
  }

  if (false && path.includes('cliente-detalhe.html') && idSelecionado) {
    const { buscarClientes, buscarChamados } = await import('./api.js');
    const [clientes, chamados] = await Promise.all([buscarClientes(), buscarChamados()]);
    const cliente = clientes.find((item) => item.id_usuario == idSelecionado);
    if (cliente) {
      document.getElementById('cli-nome').textContent = cliente.nome;
      document.getElementById('cli-email').textContent = cliente.email;
      document.getElementById('cli-telefone').textContent = cliente.telefone || '-';
      document.getElementById('cli-plano').textContent = cliente.plano || '-';
      document.getElementById('cli-acoes').textContent = cliente.acoes || '-';
      document.getElementById('cli-data').textContent = cliente.criado_em ? new Date(cliente.criado_em).toLocaleDateString('pt-BR') : '-';
      const tabelaChamados = document.querySelector('#tabela-chamados-cliente tbody');
      const chamadosCliente = chamados.filter((chamado) => chamado.cliente === cliente.nome);
      tabelaChamados.innerHTML = chamadosCliente.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${chamado.id_chamado}'" style="cursor: pointer;"><td>#${chamado.id_chamado}</td><td>${chamado.status || '-'}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado encontrado para este cliente.</td></tr>';
    }
  }

  if (false && path.includes('equipe-detalhe.html') && idSelecionado) {
    const { buscarEquipe } = await import('./api.js');
    const equipe = await buscarEquipe();
    const membro = equipe.find((item) => item.id_grupo_solucionadores == idSelecionado);
    if (membro) {
      document.getElementById('membro-nome').textContent = membro.nome;
      document.getElementById('membro-email').textContent = membro.email;
      document.getElementById('membro-funcao').textContent = membro.cargo;
    }
  }
});

function setDetailText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value || '-';
}

function detailInitials(name) {
  return String(name || '--').trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '--';
}

function detailDate(value) {
  if (!value) return 'Não informada';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('pt-BR');
}

function detailEscape(value) {
  return String(value ?? '-').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

function iniciarEdicaoDetalhe(scope, registro) {
  const campos = [...document.querySelectorAll(`[data-edit-scope="${scope}"]`)].length
    ? document.querySelectorAll('.info-value[data-edit-field]') : [];
  campos.forEach((campo) => {
    if (campo.querySelector('input')) return;
    const valor = campo.dataset.editField === 'id_setor' ? (registro.setor_nome || '') : (registro[campo.dataset.editField] || campo.textContent.trim());
    const input = document.createElement('input');
    input.className = 'info-value detail-editing';
    input.id = campo.id;
    input.value = valor;
    input.dataset.editField = campo.dataset.editField;
    campo.replaceWith(input);
    input.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      const dados = { [input.dataset.editField]: input.value.trim() };
      if (input.dataset.editField === 'valor_hora') dados.valor_hora = input.value.replace(/[^\d,.]/g, '').replace(',', '.') || null;
      if (input.dataset.editField === 'data_inicio') dados.data_inicio = input.value;
      if (scope === 'equipe' && input.dataset.editField === 'id_setor') {
        const setor = [...document.querySelectorAll('#setores-disponiveis option')].find((option) => option.value === input.value);
        dados.id_setor = setor?.dataset.id || (input.value.trim() === (registro.setor_nome || '').trim() ? registro.id_setor : input.value.trim());
      }
      try {
        const atualizado = scope === 'cliente' ? await atualizarCliente(registro.id_usuario, dados) : await atualizarMembro(registro.id_grupo_solucionadores, dados);
        registro = atualizado;
        const span = document.createElement('span');
        span.className = 'info-value';
        span.id = input.id;
        span.dataset.editField = input.dataset.editField;
        span.textContent = input.dataset.editField === 'id_setor' ? (atualizado.setor_nome || input.value) : (atualizado[input.dataset.editField] || input.value);
        input.replaceWith(span);
      } catch (error) { alert(`Não foi possível salvar: ${error.message}`); input.focus(); }
    });
    input.focus();
  });
}

function configurarDetalheEditavel(scope, registro) {
  document.querySelector(`[data-edit-scope="${scope}"]`)?.addEventListener('click', () => iniciarEdicaoDetalhe(scope, registro));
}

document.addEventListener('DOMContentLoaded', async () => {
  const path = window.location.pathname;
  const id = new URLSearchParams(window.location.search).get('id');
  if (!id || !/(-detalhe\.html)$/.test(path)) return;

  try {
    if (path.includes('chamados-detalhe.html')) {
      const { buscarChamadoPorId, buscarClientes, buscarEquipe } = await import('./api.js');
      const [chamado, clientes, equipe] = await Promise.all([buscarChamadoPorId(id), buscarClientes(), buscarEquipe()]);
      const cliente = clientes.find((item) => item.nome === chamado.cliente);
      const responsavel = equipe.find((item) => item.id_grupo_solucionadores == chamado.id_grupo_solucionadores);
      setDetailText('chamado-titulo', `#${chamado.id_chamado}`);
      setDetailText('chamado-breadcrumb-cliente', chamado.cliente);
      setDetailText('chamado-cliente', chamado.cliente);
      setDetailText('chamado-contato', cliente?.contato || 'Não informado');
      setDetailText('chamado-telefone', cliente?.telefone || 'Não informado');
      setDetailText('chamado-email', chamado.email_cliente || cliente?.email || 'Não informado');
      setDetailText('chamado-data', detailDate(chamado.data_agendada));
      setDetailText('chamado-nivel', `Tipo ${chamado.id_tipo_chamado || 'não informado'}`);
      setDetailText('chamado-descricao', chamado.descricao || 'Sem descrição cadastrada.');
      const sidebarValues = document.querySelectorAll('.ticket-sidebar .sidebar-info-list .info-value');
      if (sidebarValues.length >= 4) {
        sidebarValues[0].textContent = responsavel?.nome || 'Não atribuído';
        sidebarValues[1].textContent = responsavel?.setor_nome || 'Não informado';
        sidebarValues[2].textContent = 'Não informado';
        sidebarValues[3].textContent = chamado.status || 'ABERTO';
      }
      const history = document.querySelector('.timeline-list');
      if (history) history.innerHTML = `<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-header"><strong>Chamado ${detailEscape(chamado.status || 'ABERTO').toLowerCase()}</strong><span class="timeline-time">${detailEscape(detailDate(chamado.data_agendada))}</span></div><p>Registro criado no sistema.</p></div></div>`;
    }

    if (path.includes('cliente-detalhe.html')) {
      const { buscarClientes, buscarChamados } = await import('./api.js');
      const [clientes, chamados] = await Promise.all([buscarClientes(), buscarChamados()]);
      const cliente = clientes.find((item) => item.id_usuario == id);
      if (!cliente) throw new Error('Cliente não encontrado.');
      setDetailText('cli-nome', cliente.nome);
      setDetailText('cli-breadcrumb', cliente.nome);
      setDetailText('cli-avatar', detailInitials(cliente.nome));
      setDetailText('cli-cnpj', cliente.cnpj);
      setDetailText('cli-email', cliente.email);
      setDetailText('cli-telefone', cliente.telefone);
      setDetailText('cli-endereco', cliente.contato);
      setDetailText('cli-fatura', cliente.plano);
      setDetailText('cli-contrato', cliente.acoes);
      configurarDetalheEditavel('cliente', cliente);
      document.querySelector('#desativarCliente')?.addEventListener('click', async () => {
        if (!window.confirm('Tem certeza de que deseja apagar este cliente?')) return;
        try { await excluirCliente(cliente.id_usuario); window.location.href = 'clientes.html'; } catch (error) { alert(`Não foi possível apagar: ${error.message}`); }
      });
      const table = document.querySelector('#tabela-chamados-cliente tbody');
      const tickets = chamados.filter((chamado) => chamado.cliente === cliente.nome);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.assunto)}</td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td><td>${detailEscape(chamado.classificacao)}</td></tr>`).join('') || '<tr><td colspan="6">Nenhum chamado encontrado para este cliente.</td></tr>';
    }

    if (path.includes('equipe-detalhe.html')) {
      const { buscarEquipe, buscarChamados } = await import('./api.js');
      const [equipe, chamados] = await Promise.all([buscarEquipe(), buscarChamados()]);
      const membro = equipe.find((item) => item.id_grupo_solucionadores == id);
      if (!membro) throw new Error('Membro da equipe não encontrado.');
      setDetailText('membro-nome', membro.nome);
      setDetailText('membro-breadcrumb', membro.nome);
      setDetailText('membro-avatar', detailInitials(membro.nome));
      setDetailText('membro-setor', membro.setor_nome || 'Sem setor');
      setDetailText('membro-cargo', membro.cargo || 'Não informado');
      setDetailText('membro-email', membro.email);
      setDetailText('membro-telefone', 'Não informado');
      setDetailText('membro-admissao', detailDate(membro.data_inicio));
      setDetailText('membro-valor-hora', membro.valor_hora ? `R$ ${Number(membro.valor_hora).toFixed(2).replace('.', ',')}` : 'Não informado');
      configurarDetalheEditavel('equipe', membro);
      document.querySelector('#desativarMembro')?.addEventListener('click', async () => {
        if (!window.confirm('Tem certeza de que deseja apagar este técnico?')) return;
        try { await excluirMembro(membro.id_grupo_solucionadores); window.location.href = 'equipe.html'; } catch (error) { alert(`Não foi possível apagar: ${error.message}`); }
      });
      setDetailText('membro-certificacoes', 'Não informado');
      document.querySelectorAll('.team-stats-grid .stat-box-number').forEach((element) => { element.textContent = '—'; });
      const skills = document.querySelector('.skills-tags-container');
      if (skills) skills.textContent = 'Nenhuma especialidade cadastrada.';
      const table = document.querySelector('#tabela-chamados-tecnico tbody');
      const tickets = chamados.filter((chamado) => chamado.id_grupo_solucionadores == membro.id_grupo_solucionadores);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.assunto)}</td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td></tr>`).join('') || '<tr><td colspan="4">Nenhum chamado atribuído a este membro.</td></tr>';
    }
  } catch (error) {
    console.error('Não foi possível carregar os detalhes:', error);
    const title = document.querySelector('.page-title-bar h1');
    if (title) title.textContent = error.message || 'Não foi possível carregar os detalhes.';
  }
});