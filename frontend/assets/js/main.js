import { API_URL, buscarChamados, buscarClientes, atualizarCliente, atualizarMembro } from './api.js';
import { gerarUrlAvatar } from './avatar.js';
import { mostrarNotificacao, mostrarNotificacaoNaProximaPagina, mostrarErro, comCarregamento } from './notifications.js';
import { formatBrazilianCnpj, formatBrazilianPhone, initializeCnpjInputs, initializePhoneInputs } from './phone.js';

initializePhoneInputs();
initializeCnpjInputs();

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
  if (id === 'modal-cliente') resetarContatosCliente();
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
  const empresa = localStorage.getItem('empresaNome') || sessionStorage.getItem('empresaNome') || 'HelpTI';
  document.querySelectorAll('.brand-name').forEach((element) => element.textContent = empresa);
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => { image.src = gerarUrlAvatar(nome); });
}

function configurarTema() {
  const root = document.documentElement;
  const temaInicial = localStorage.getItem('helpti-theme') === 'dark' ? 'dark' : 'light';
  root.dataset.theme = temaInicial;

  const perfil = document.querySelector('.user-profile-wrapper');
  if (!perfil?.parentNode) return;

  const controles = document.createElement('div');
  controles.className = 'user-controls';
  perfil.parentNode.insertBefore(controles, perfil);
  controles.append(perfil);

  const botao = document.createElement('button');
  botao.type = 'button';
  botao.className = 'theme-toggle';
  botao.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('helpti-theme', root.dataset.theme);
    atualizarBotaoTema();
  });

  function atualizarBotaoTema() {
    const temaEscuro = root.dataset.theme === 'dark';
    botao.setAttribute('aria-label', temaEscuro ? 'Ativar modo claro' : 'Ativar modo escuro');
    botao.setAttribute('aria-pressed', String(temaEscuro));
    botao.title = temaEscuro ? 'Ativar modo claro' : 'Ativar modo escuro';
    botao.innerHTML = temaEscuro
      ? '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.42 1.42"/><path d="m17.65 17.65 1.42 1.42"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.35 17.65-1.42 1.42"/><path d="m19.07 4.93-1.42 1.42"/></svg>'
      : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6.5 6.5 0 0 0 8.268 8.268c.344-.215.825-.003.803.401"/></svg>';
  }

  atualizarBotaoTema();
  controles.append(botao);
}

configurarTema();

let clientesEmMemoria = [];
let chamadosEmMemoria = [];
let filtroClientesSelecionado = 'todos';

const PERMISSOES_POR_CARGO = {
  'RH': ['dashboard', 'clientes', 'equipe'],
  'Suporte': ['dashboard', 'chamados', 'clientes', 'educacao'],
  'NOC': ['dashboard', 'chamados'],
  'Técnico': ['dashboard', 'chamados', 'educacao'],
  'Personalizado': ['dashboard']
};

const PAGINA_POR_PERMISSAO = {
  'dashboard.html': 'dashboard',
  'chamados.html': 'chamados',
  'chamados-detalhe.html': 'chamados',
  'clientes.html': 'clientes',
  'cliente-detalhe.html': 'clientes',
  'equipe.html': 'equipe',
  'equipe-detalhe.html': 'equipe',
  'relatorios.html': 'relatorios',
  'educacao.html': 'educacao',
  'settings.html': 'configuracoes'
};

function aplicarPresetPermissoes(cargo) {
  const permissoes = new Set(PERMISSOES_POR_CARGO[cargo] || PERMISSOES_POR_CARGO.Personalizado);
  document.querySelectorAll('#form-nova-equipe [name="permissoes"]').forEach((checkbox) => {
    checkbox.checked = permissoes.has(checkbox.value);
  });
}

async function aplicarPermissoesNavegacao() {
  try {
    const response = await fetch(`${API_URL}/sessao`);
    if (!response.ok) return;
    const usuario = await response.json();
    const permissoes = new Set(usuario.permissoes || []);
    document.body.dataset.gerenciarEquipe = String(permissoes.has('gerenciar_equipe'));
    document.querySelectorAll('a[href$=".html"]').forEach((link) => {
      const pagina = new URL(link.href, window.location.href).pathname.split('/').pop();
      const permissao = PAGINA_POR_PERMISSAO[pagina];
      if (permissao && !permissoes.has(permissao)) {
        link.hidden = true;
        link.style.display = 'none';
        link.setAttribute('aria-hidden', 'true');
      }
    });
    if (usuario.nome) document.querySelectorAll('.user-role').forEach((element) => { element.textContent = usuario.nome; });
  } catch (error) {
  }
}

function renderizarClientes(clientes) {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  tabela.innerHTML = clientes.map((cliente) => {
    const ativo = (cliente.status || 'ATIVO').toUpperCase() === 'ATIVO';
    return `<tr onclick="window.location.href='cliente-detalhe.html?id=${detailEscape(cliente.id_usuario)}'" style="cursor: pointer;"><td><strong>${detailEscape(cliente.nome)}</strong></td><td>${detailEscape(formatBrazilianCnpj(cliente.cnpj) || '-')}</td><td>${detailEscape(cliente.contato)}</td><td>${detailEscape(cliente.telefone_empresa || cliente.telefone)}</td><td><div class="client-row-actions"><span class="client-status-badge ${ativo ? 'is-active' : 'is-inactive'}">${ativo ? 'Ativo' : 'Desativado'}</span><button type="button" class="client-delete-button" data-excluir-cliente="${detailEscape(cliente.id_usuario)}" aria-label="Excluir cliente ${detailEscape(cliente.nome || '')}" title="Excluir cliente"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14H5V6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg></button></div></td></tr>`;
  }).join('') || '<tr><td colspan="5">Nenhum cliente encontrado.</td></tr>';
}

function filtrarClientes() {
  const termo = document.querySelector('#buscaClientes')?.value.trim().toLowerCase() || '';
  const clientesFiltrados = clientesEmMemoria.filter((cliente) => {
    const statusCliente = (cliente.status || 'ATIVO').toUpperCase();
    if (filtroClientesSelecionado === 'cliente:ATIVO' && statusCliente !== 'ATIVO') return false;
    if (filtroClientesSelecionado === 'cliente:INATIVO' && !['INATIVO', 'DESATIVADO'].includes(statusCliente)) return false;
    if (filtroClientesSelecionado.startsWith('chamado:')) {
      const statusChamado = filtroClientesSelecionado.split(':')[1];
      const possuiChamado = chamadosEmMemoria.some((chamado) => chamado.cliente === cliente.nome && chamado.status === statusChamado);
      if (!possuiChamado) return false;
    }
    const dadosBusca = [cliente.nome, cliente.cnpj, cliente.contato, cliente.email, cliente.telefone_empresa, cliente.telefone, cliente.endereco, cliente.plano, ...(cliente.contatos || []).flatMap((contato) => [contato.nome, contato.email, contato.telefone])];
    return !termo || dadosBusca.some((valor) => normalizarTexto(valor).includes(normalizarTexto(termo)));
  });
  renderizarClientes(clientesFiltrados);
}

function normalizarTexto(valor) {
  return String(valor || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function configurarFiltroClientes() {
  const controle = document.querySelector('.client-status-filter-control');
  const botao = document.querySelector('#botaoFiltroClientes');
  const menu = document.querySelector('#menuFiltroClientes');
  if (!controle || !botao || !menu) return;

  botao.addEventListener('click', (event) => {
    event.stopPropagation();
    const aberto = controle.classList.toggle('is-open');
    botao.setAttribute('aria-expanded', String(aberto));
  });

  menu.addEventListener('click', (event) => {
    const opcao = event.target.closest('[data-client-filter]');
    if (!opcao) return;
    filtroClientesSelecionado = opcao.dataset.clientFilter;
    document.querySelector('#filtroClientesLabel').textContent = opcao.textContent.trim();
    menu.querySelectorAll('[data-client-filter]').forEach((item) => item.setAttribute('aria-selected', String(item === opcao)));
    controle.classList.remove('is-open');
    botao.setAttribute('aria-expanded', 'false');
    filtrarClientes();
  });
}

async function carregarClientes() {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  try {
    const { buscarClientes, buscarChamados } = await import('./api.js');
    [clientesEmMemoria, chamadosEmMemoria] = await Promise.all([buscarClientes(), buscarChamados()]);
    filtrarClientes();
  } catch (error) { tabela.innerHTML = `<tr><td colspan="5">${detailEscape(error.message)}</td></tr>`; }
}

async function salvarCliente(event) {
  event.preventDefault();
  const form = event.target;
  const contatos = [...form.querySelectorAll('[data-contato-row]')].map((linha) => ({
    email: linha.querySelector('[data-contato-email]').value.trim(),
    nome: linha.querySelector('[data-contato-nome]').value.trim(),
    telefone: formatBrazilianPhone(linha.querySelector('[data-contato-telefone]').value)
  }));
  const primeiroContato = contatos[0];
  const dados = {
    nome: form.elements.nome.value.trim(),
    cnpj: formatBrazilianCnpj(form.elements.cnpj.value),
    telefone_empresa: formatBrazilianPhone(form.elements.telefone_empresa.value),
    endereco: form.elements.endereco.value.trim(),
    email: primeiroContato.email,
    contato: primeiroContato.nome,
    telefone: primeiroContato.telefone,
    contatos
  };
  await comCarregamento(form.querySelector('[type="submit"]'), async () => {
    try {
      const { criarCliente } = await import('./api.js');
      await criarCliente(dados);
      closeModal('modal-cliente'); form.reset(); resetarContatosCliente(); await carregarClientes(); mostrarNotificacao('Cliente cadastrado com sucesso.');
    } catch (error) { mostrarErro(`Não foi possível cadastrar: ${error.message}`); }
  }, 'Salvando...');
}

function atualizarBotoesRemoverContato() {
  const linhas = [...document.querySelectorAll('#contatosCliente [data-contato-row]')];
  linhas.forEach((linha) => {
    linha.querySelector('[data-remover-contato]').disabled = linhas.length === 1;
  });
}

function adicionarContatoCliente() {
  const lista = document.querySelector('#contatosCliente');
  const modelo = document.querySelector('#modeloContatoCliente');
  if (!lista || !modelo) return;
  lista.append(modelo.content.cloneNode(true));
  const linhas = [...lista.querySelectorAll('[data-contato-row]')];
  linhas.at(-1).querySelector('.form-group:nth-child(2) label').textContent = 'Nome do funcionário';
  atualizarBotoesRemoverContato();
  linhas.at(-1).querySelector('[data-contato-email]').focus();
}

function resetarContatosCliente() {
  const lista = document.querySelector('#contatosCliente');
  const modelo = document.querySelector('#modeloContatoCliente');
  if (!lista || !modelo) return;
  lista.replaceChildren(modelo.content.cloneNode(true));
  atualizarBotoesRemoverContato();
}

function formatarTelefoneEmpresa(valor) {
  return formatBrazilianPhone(valor);
}

async function carregarEquipe() {
  const tabela = document.querySelector('#tabelaEquipe');
  if (!tabela) return;
  try {
    const { buscarEquipe } = await import('./api.js');
    const equipe = await buscarEquipe();
    tabela.innerHTML = equipe.map((membro) => `<tr onclick="window.location.href='equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}'" style="cursor: pointer;"><td><strong>${detailEscape(membro.nome || membro.descricao)}</strong></td><td>${detailEscape(membro.cargo)}</td><td>${detailEscape(membro.setor_nome || 'Sem setor')}</td><td><span class="status-badge status-info">${detailEscape(membro.status || 'ATIVO')}</span></td></tr>`).join('') || '<tr><td colspan="4">Nenhum membro cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="4">${detailEscape(error.message)}</td></tr>`; }
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
    if (lista) lista.innerHTML = setoresEmMemoria.map((setor) => `<option value="${detailEscape(setor.nome)}"></option>`).join('');
    tabela.innerHTML = setoresEmMemoria.map((setor) => renderizarSetor(setor)).join('') || '<tr><td colspan="3">Nenhum setor cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="3">${detailEscape(error.message)}</td></tr>`; }
}

function iconeNivel(icone) {
  const caminhos = icone === 'plus'
    ? '<path d="M5 12h14"/><path d="M12 5v14" />'
    : icone === 'chevron-down'
      ? '<path d="m6 9 6 6 6-6" />'
      : '<path d="m9 18 6-6-6-6" />';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${caminhos}</svg>`;
}

function renderizarSetor(setor) {
  const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == setor.id_setor);
  const niveis = (setor.niveis || []).map((nivel, indice) => {
    const membrosDoNivelAtual = participantes.filter((membro) => Number(membro.nivel) === indice + 1);
    const membrosHtml = membrosDoNivelAtual.map((membro) => `<a href="equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}"><strong>${detailEscape(membro.nome)}</strong><span>${detailEscape(membro.email || 'Sem e-mail')}</span></a>`).join('') || '<span class="empty-row">Nenhum funcionário neste nível.</span>';
    return `<div class="sector-level-row"><div class="level-summary"><strong>${detailEscape(nivel)}</strong><small>${membrosDoNivelAtual.length} funcionário(s) alocado(s)</small></div><div class="level-actions"><button type="button" class="level-action" title="Mostrar funcionários de ${detailEscape(nivel)}" aria-label="Mostrar funcionários de ${detailEscape(nivel)}" aria-expanded="false" data-level-action="details" data-setor-id="${detailEscape(setor.id_setor)}" data-level-index="${indice + 1}">${iconeNivel('chevron')}</button><button type="button" class="level-action" title="Adicionar técnico em ${detailEscape(nivel)}" aria-label="Adicionar técnico em ${detailEscape(nivel)}" data-level-action="add" data-setor-id="${detailEscape(setor.id_setor)}" data-level-index="${indice + 1}">${iconeNivel('plus')}</button></div><div class="level-members-inline" hidden>${membrosHtml}</div></div>`;
  }).join('');
  const possuiNiveis = Boolean(setor.niveis?.length);
  const membrosSemNivel = participantes.filter((membro) => !membro.nivel);
  const semNivelHtml = membrosSemNivel.map((membro) => `<a href="equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}"><strong>${detailEscape(membro.nome || membro.descricao)}</strong><span>${detailEscape(membro.email || 'Sem e-mail')}</span></a>`).join('') || '<span class="empty-row">Nenhum funcionário neste setor.</span>';
  const conteudoNiveis = possuiNiveis
    ? `<div class="sector-levels">${niveis}</div>`
    : `<div class="sector-levels sector-no-levels"><div class="sector-no-levels-header"><span>${membrosSemNivel.length} funcionário(s)</span><button type="button" class="level-action" title="Adicionar funcionário sem nível" aria-label="Adicionar funcionário ao setor ${detailEscape(setor.nome)}" data-level-action="add" data-setor-id="${detailEscape(setor.id_setor)}">${iconeNivel('plus')}</button></div><div class="level-members-inline">${semNivelHtml}</div></div>`;
  return `<tr><td colspan="3"><details class="sector-details"><summary><span><strong>${detailEscape(setor.nome)}</strong><small>${possuiNiveis ? `${setor.niveis.length} nível(is)` : 'Sem níveis cadastrados'}</small></span><span class="sector-summary-actions"><span class="status-badge status-info">${participantes.length} participante(s)</span><button type="button" class="sector-delete-button" title="Excluir setor" aria-label="Excluir setor" data-delete-sector="${detailEscape(setor.id_setor)}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14H5V6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg></button></span></summary>${conteudoNiveis}</details></td></tr>`;
}

function obterNivelAtual() {
  return window.nivelSelecionado || { setorId: null, nivel: null };
}

function membrosDoNivel(setorId, nivel) {
  return equipeEmMemoria.filter((membro) => membro.id_setor == setorId && Number(membro.nivel) === Number(nivel));
}

function opcoesDeNiveis(setor) {
  return (setor.niveis || []).map((nivel, indice) => `<option value="${indice + 1}">${detailEscape(nivel)}</option>`).join('');
}

function abrirDetalhesNivel(setorId, nivel) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == setorId);
  if (!setor) return;
  window.nivelSelecionado = { setorId, nivel };
  document.querySelector('#nivel-titulo').textContent = setor.niveis[nivel - 1] || `Nível ${nivel}`;
  document.querySelector('#nivel-setor').textContent = setor.nome;
  const membros = membrosDoNivel(setorId, nivel);
  document.querySelector('#nivel-membros').innerHTML = membros.length ? membros.map((membro) => `<div class="level-member-row"><div><strong>${detailEscape(membro.nome)}</strong><small>${detailEscape(membro.email || 'Sem e-mail')}</small></div><div class="level-member-actions"><select data-member-level="${detailEscape(membro.id_grupo_solucionadores)}" aria-label="Nível de ${detailEscape(membro.nome)}">${opcoesDeNiveis(setor)}</select><button type="button" class="level-remove-button" data-remove-member="${detailEscape(membro.id_grupo_solucionadores)}">Remover</button></div></div>`).join('') : '<p class="empty-row">Nenhum funcionário neste nível.</p>';
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
  document.querySelector('#funcionarios-disponiveis').innerHTML = disponiveis.length ? disponiveis.map((membro) => `<label class="available-member-row"><input type="checkbox" value="${detailEscape(membro.id_grupo_solucionadores)}"><span><strong>${detailEscape(membro.nome)}</strong><small>${detailEscape(membro.setor_nome || 'Sem setor')} · ${membro.nivel ? `Nível ${detailEscape(membro.nivel)}` : 'Sem nível alocado'}</small></span></label>`).join('') : '<p class="empty-row">Todos os funcionários já estão neste nível.</p>';
  openModal('modal-adicionar-nivel');
}

function abrirNovoFuncionario(setorId, nivel) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == setorId);
  const form = document.querySelector('#form-nova-equipe');
  const campoSetor = form?.elements.setor;
  const campoNivel = form?.elements.nivel;
  if (!setor || !form || !campoSetor || !campoNivel) return;
  form.reset();
  aplicarPresetPermissoes(form.elements.cargo.value);
  campoSetor.value = setor.nome;
  const niveis = setor.niveis || [];
  campoNivel.required = niveis.length > 0;
  campoNivel.innerHTML = niveis.length
    ? `<option value="">Selecione um nível</option>${opcoesDeNiveis(setor)}`
    : '<option value="">Sem nível</option>';
  campoNivel.value = nivel ? String(nivel) : '';
  openModal('modal-equipe');
}

function alternarMembrosNivel(botao) {
  const lista = botao.closest('.sector-level-row')?.querySelector('.level-members-inline');
  if (!lista) return;
  const aberto = lista.hidden;
  lista.hidden = !aberto;
  botao.setAttribute('aria-expanded', String(aberto));
  botao.innerHTML = iconeNivel(aberto ? 'chevron-down' : 'chevron');
  botao.title = `${aberto ? 'Ocultar' : 'Mostrar'} funcionários`;
  botao.setAttribute('aria-label', `${aberto ? 'Ocultar' : 'Mostrar'} funcionários do nível`);
}

function equipamentosDoCliente(id) {
  const chave = `helpti-equipamentos-${id}`;
  const salvos = JSON.parse(localStorage.getItem(chave) || 'null');
  if (Array.isArray(salvos)) return salvos;
  localStorage.setItem(chave, JSON.stringify([]));
  return [];
}

function limparEquipamentosLegados() {
  const chaveMigracao = 'helpti-migracao-equipamentos-mapa-vazio-v1';
  if (localStorage.getItem(chaveMigracao) === 'concluida') return;

  const chavesDeEquipamentos = [];
  for (let indice = 0; indice < localStorage.length; indice += 1) {
    const chave = localStorage.key(indice);
    if (chave?.startsWith('helpti-equipamentos-')) chavesDeEquipamentos.push(chave);
  }
  chavesDeEquipamentos.forEach((chave) => localStorage.removeItem(chave));
  localStorage.setItem(chaveMigracao, 'concluida');
}

function renderizarEquipamentos(id) {
  const lista = document.querySelector('#mapa-equipamentos');
  if (!lista) return;
  const equipamentos = equipamentosDoCliente(id);
  lista.innerHTML = equipamentos.length
    ? equipamentos.map((equipamento, indice) => `<div class="asset-item"><span class="asset-name">${detailEscape(equipamento.nome)}</span><strong class="asset-count">${Number(equipamento.quantidade) || 0} un</strong><div class="asset-actions"><button type="button" data-editar-equipamento="${indice}" aria-label="Editar ${detailEscape(equipamento.nome)}">Editar</button><button type="button" data-apagar-equipamento="${indice}" aria-label="Apagar ${detailEscape(equipamento.nome)}">Apagar</button></div></div>`).join('')
    : '<p class="assets-empty">Nenhum equipamento cadastrado. Use o botão + para adicionar.</p>';
  const total = equipamentos.reduce((soma, equipamento) => soma + (Number(equipamento.quantidade) || 0), 0);
  document.querySelector('#equipamentos-total').textContent = `Total: ${total} equipamento(s) cadastrado(s)`;
}

function salvarEquipamento(id, indice = null) {
  const equipamentos = equipamentosDoCliente(id);
  const atual = indice === null ? { nome: '', quantidade: 1 } : equipamentos[indice];
  const nome = window.prompt('Nome do equipamento:', atual.nome);
  if (nome === null || !nome.trim()) return;
  const quantidade = window.prompt('Número de equipamentos:', atual.quantidade);
  if (quantidade === null || !/^\d+$/.test(quantidade) || Number(quantidade) < 0) return mostrarErro('Informe uma quantidade inteira válida.');
  const equipamento = { nome: nome.trim(), quantidade: Number(quantidade) };
  if (indice === null) equipamentos.push(equipamento); else equipamentos[indice] = equipamento;
  localStorage.setItem(`helpti-equipamentos-${id}`, JSON.stringify(equipamentos));
  renderizarEquipamentos(id);
  mostrarNotificacao(indice === null ? 'Equipamento cadastrado com sucesso.' : 'Equipamento atualizado com sucesso.');
}

function configurarEquipamentos(id) {
  limparEquipamentosLegados();
  renderizarEquipamentos(id);
  document.querySelector('#adicionar-equipamento')?.addEventListener('click', () => salvarEquipamento(id));
  document.querySelector('#editar-equipamentos')?.addEventListener('click', () => {
    document.querySelector('#mapa-equipamentos')?.classList.toggle('is-editing');
  });
  document.querySelector('#mapa-equipamentos')?.addEventListener('click', (event) => {
    const editar = event.target.closest('[data-editar-equipamento]');
    const apagar = event.target.closest('[data-apagar-equipamento]');
    if (editar) salvarEquipamento(id, Number(editar.dataset.editarEquipamento));
    if (apagar && window.confirm('Apagar este equipamento?')) {
      const equipamentos = equipamentosDoCliente(id);
      equipamentos.splice(Number(apagar.dataset.apagarEquipamento), 1);
      localStorage.setItem(`helpti-equipamentos-${id}`, JSON.stringify(equipamentos));
      renderizarEquipamentos(id);
    }
  });
}

async function excluirSetor(idSetor) {
  if (!window.confirm('Tem certeza de que deseja apagar este setor e seus níveis?')) return;
  try {
    const { excluirSetor: remover } = await import('./api.js');
    await remover(idSetor);
    await carregarSetores();
    mostrarNotificacao('Setor apagado com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível apagar o setor: ${error.message}`); }
}

async function alterarNivelFuncionario(id, setorId, nivel) {
  try {
    const { atualizarMembro } = await import('./api.js');
    await atualizarMembro(id, { nivel: Number(nivel), id_setor: setorId });
    await carregarSetores();
    abrirDetalhesNivel(setorId, Number(nivel));
    mostrarNotificacao('Nível do funcionário atualizado com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível alterar o nível: ${error.message}`); }
}

async function removerFuncionarioNivel(id) {
  const { setorId, nivel } = obterNivelAtual();
  try {
    const { atualizarMembro } = await import('./api.js');
    await atualizarMembro(id, { nivel: null });
    await carregarSetores();
    abrirDetalhesNivel(setorId, nivel);
    mostrarNotificacao('Funcionário removido do nível com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível remover o funcionário do nível: ${error.message}`); }
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
    mostrarNotificacao('Funcionário(s) adicionado(s) ao nível com sucesso.');
  } catch (error) { mostrarErro(`Não foi possível adicionar os funcionários: ${error.message}`); }
}

function mostrarParticipantes(idSetor) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == idSetor);
  const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == idSetor);
  document.querySelector('#participantes-titulo').textContent = setor ? `Participantes: ${setor.nome}` : 'Participantes';
  document.querySelector('#lista-participantes').innerHTML = participantes.map((membro) => `<div class="participant-item"><strong>${detailEscape(membro.nome)}</strong><span>${detailEscape(membro.cargo || 'Sem função')}</span></div>`).join('') || '<p class="empty-row">Nenhum participante neste setor.</p>';
  openModal('modal-participantes');
}

async function salvarSetor(event) {
  event.preventDefault();
  const form = event.target;
  const possuiNivel = form.querySelector('#possui-nivel').checked;
  const niveis = possuiNivel ? [...form.querySelectorAll('#levels-list input')].map((input) => input.value.trim()).filter(Boolean) : [];
  if (possuiNivel && !niveis.length) {
    mostrarErro('Adicione pelo menos um nível para este setor.');
    return;
  }
  await comCarregamento(form.querySelector('[type="submit"]'), async () => {
    try {
      const { criarSetor } = await import('./api.js');
      await criarSetor({ nome: form.elements.nome.value.trim(), niveis });
      closeModal('modal-setor');
      form.reset();
      document.querySelector('#levels-list').innerHTML = '';
      document.querySelector('#levels-editor').hidden = true;
      await carregarSetores();
      mostrarNotificacao('Setor criado com sucesso.');
    } catch (error) { mostrarErro(`Não foi possível criar o setor: ${error.message}`); }
  }, 'Salvando...');
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
  if (!/^[A-Za-zÀ-ÿ ]+$/.test(form.elements.nome.value.trim()) || !/^[A-Za-zÀ-ÿ ]+$/.test(setorNome)) {
    form.reportValidity();
    return;
  }
  await comCarregamento(form.querySelector('[type="submit"]'), async () => {
    try {
      const { criarMembro, criarSetor } = await import('./api.js');
      let setor = setoresEmMemoria.find((item) => item.nome.trim().toLowerCase() === setorNome.toLowerCase());
      if (!setor) setor = await criarSetor({ nome: setorNome, descricao: '' });
      await criarMembro({
        nome: form.elements.nome.value.trim(),
        email: form.elements.email.value.trim(),
        cargo: form.elements.cargo.value,
        permissoes: [...form.querySelectorAll('[name="permissoes"]:checked')].map((checkbox) => checkbox.value),
        telefone: formatBrazilianPhone(form.elements.telefone.value),
        valor_hora: form.elements.valor_hora.value,
        id_setor: setor.id_setor,
        nivel: form.elements.nivel.value,
        senha: form.elements.senha.value
      });
      closeModal('modal-equipe'); form.reset(); await carregarSetores(); await carregarEquipe(); mostrarNotificacao('Membro cadastrado com sucesso.');
    } catch (error) { mostrarErro(`Não foi possível cadastrar: ${error.message}`); }
  }, 'Salvando...');
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
    mostrarErro('Preencha o nome do workspace e o e-mail de suporte.');
    return;
  }
  await comCarregamento(botao, async () => {
    try {
      const { salvarConfiguracoes: salvar } = await import('./api.js');
      const configuracoesSalvas = await salvar(dados);
      document.getElementById('workspaceName').value = configuracoesSalvas.workspaceName;
      document.getElementById('supportEmail').value = configuracoesSalvas.supportEmail;
      localStorage.setItem('workspaceName', configuracoesSalvas.workspaceName);
      localStorage.setItem('supportEmail', configuracoesSalvas.supportEmail);
      mostrarNotificacao('Configurações salvas com sucesso.');
    } catch (error) {
      mostrarErro(`Não foi possível salvar: ${error.message}`);
    }
  }, 'Salvando...');
}

function cancelarConfigurações() {
  window.location.href = 'dashboard.html';
}

async function encerrarSessao(event) {
  event.preventDefault();
  try { await fetch(`${API_URL}/logout`, { method: 'POST' }); } catch (error) {}
  localStorage.removeItem('usuarioId');
  localStorage.removeItem('grupoId');
  localStorage.removeItem('perfilNome');
  localStorage.removeItem('empresaNome');
  localStorage.removeItem('loginExpiraEm');
  localStorage.removeItem('emailLembrado');
  sessionStorage.removeItem('grupoId');
  sessionStorage.removeItem('perfilNome');
  sessionStorage.removeItem('empresaNome');
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
window.abrirNovoFuncionario = abrirNovoFuncionario;

document.addEventListener('click', () => document.getElementById('profileDropdown')?.classList.remove('active'));
document.addEventListener('click', (event) => {
  const action = event.target.closest('[data-level-action]');
  if (!action) return;
  event.preventDefault();
  event.stopPropagation();
  const setorId = action.dataset.setorId;
  const nivel = Number(action.dataset.levelIndex);
  if (action.dataset.levelAction === 'details') alternarMembrosNivel(action);
  if (action.dataset.levelAction === 'add') abrirNovoFuncionario(setorId, Number.isInteger(nivel) && nivel > 0 ? nivel : null);
});
document.addEventListener('click', (event) => {
  const botao = event.target.closest('[data-delete-sector]');
  if (!botao) return;
  event.preventDefault();
  event.stopPropagation();
  excluirSetor(botao.dataset.deleteSector);
});
document.querySelector('#confirmar-adicao-nivel')?.addEventListener('click', adicionarFuncionariosSelecionados);
document.addEventListener('click', (event) => {
  const controle = document.querySelector('.client-status-filter-control');
  if (controle && !controle.contains(event.target)) {
    controle.classList.remove('is-open');
    document.querySelector('#botaoFiltroClientes')?.setAttribute('aria-expanded', 'false');
  }
});
document.querySelector('a[href="login.html"]')?.addEventListener('click', encerrarSessao);
document.addEventListener('DOMContentLoaded', () => {
  mostrarPerfil();
  aplicarPermissoesNavegacao();
  document.querySelector('#cargo-membro')?.addEventListener('change', (event) => aplicarPresetPermissoes(event.target.value));
  carregarClientes();
  carregarEquipe();
  carregarSetores();
  configurarModalSetor();
});
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('#buscaClientes')?.addEventListener('input', filtrarClientes);
  document.querySelector('#tabelaClientes')?.addEventListener('click', async (event) => {
    const botao = event.target.closest('[data-excluir-cliente]');
    if (!botao) return;
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm('Você tem certeza que quer apagar o cliente.')) return;
    try {
      const { excluirCliente } = await import('./api.js');
      await excluirCliente(botao.dataset.excluirCliente);
      await carregarClientes();
    } catch (error) {
      mostrarErro(`Não foi possível excluir o cliente: ${error.message}`);
    }
  });
  configurarFiltroClientes();
  resetarContatosCliente();
  document.querySelector('#adicionarContatoCliente')?.addEventListener('click', adicionarContatoCliente);
  document.querySelector('[name="telefone_empresa"]')?.addEventListener('input', (event) => {
    event.target.value = formatarTelefoneEmpresa(event.target.value);
  });
  document.querySelector('#contatosCliente')?.addEventListener('click', (event) => {
    const botao = event.target.closest('[data-remover-contato]');
    if (!botao || botao.disabled) return;
    botao.closest('[data-contato-row]')?.remove();
    atualizarBotoesRemoverContato();
  });
});

document.addEventListener('DOMContentLoaded', async () => {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const idSelecionado = params.get('id');

  if (false && path.includes('chamados-detalhe.html') && idSelecionado) {
    const { buscarChamadoPorId } = await import('./api.js');
    const chamado = await buscarChamadoPorId(idSelecionado);
    if (chamado) {
      document.getElementById('chamado-id').textContent = `Chamado #${chamado.id_chamado}`;
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
      tabelaChamados.innerHTML = chamadosCliente.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td>#${detailEscape(chamado.id_chamado)}</td><td>${detailEscape(chamado.status)}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado encontrado para este cliente.</td></tr>';
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
  if (!element) return;
  if (element instanceof HTMLInputElement) {
    const text = value || '';
    element.value = element.type === 'tel' && text !== 'Não informado'
      ? formatBrazilianPhone(text)
      : text;
  }
  else element.textContent = value || '-';
}

function detailInitials(name) {
  return String(name || '--').trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '--';
}

function detailDate(value) {
  if (!value) return 'Não informada';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('pt-BR');
}

function formatarDataAbertura(value) {
  const partes = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
  if (!partes) return detailDate(value);
  const [, ano, mes, dia, hora, minuto] = partes;
  return `${dia}-${mes}-${ano}${hora ? ` ${hora}:${minuto}` : ''}`;
}

function detailEscape(value) {
  return String(value ?? '-').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

function renderizarHistoricoChamado(eventos = []) {
  const timeline = document.querySelector('.timeline-list');
  if (!timeline) return;
  const titulos = {
    aberto: 'Chamado criado',
    iniciado: 'Atendimento iniciado',
    pausado: 'Atendimento pausado',
    escalonado: 'Chamado escalonado',
    encerrado: 'Chamado encerrado',
    agendado: 'Atendimento agendado',
    contato_atualizado: 'Contato atualizado',
    status_alterado: 'Status alterado'
  };
  if (!eventos.length) {
    timeline.innerHTML = '<p class="timeline-empty">Nenhuma atualização registrada.</p>';
    return;
  }
  timeline.innerHTML = eventos.map((evento) => {
    const data = new Date(String(evento.data_evento || '').replace(' ', 'T'));
    const horario = Number.isNaN(data.getTime())
      ? detailEscape(evento.data_evento)
      : detailEscape(data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }));
    const titulo = titulos[evento.evento] || 'Atualização';
    const autorTag = evento.autor ? `<span class="timeline-author" style="font-size: 11px; font-weight: 600; color: var(--primary-color, #2563eb); margin-left: 6px;">[${detailEscape(evento.autor)}]</span>` : '';
    return `<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-header"><strong>${titulo}</strong>${autorTag}<span class="timeline-time">${horario}</span></div><p>${detailEscape(evento.descricao)}</p></div></div>`;
  }).join('');
}

const mesesAgendamento = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

function dataLocalAgendamento(data = new Date()) {
  return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, '0')}-${String(data.getDate()).padStart(2, '0')}`;
}

function atualizarRotuloAgendamento() {
  const valor = document.querySelector('#data_agendada')?.value || '';
  const [data, hora] = valor.split('T');
  const rotulo = document.querySelector('#agendamentoDataLabel');
  if (!rotulo) return;
  if (!data) { rotulo.textContent = 'Selecionar data e horário'; return; }
  const [ano, mes, dia] = data.split('-');
  rotulo.textContent = `${dia}/${mes}/${ano} · ${hora || '09:00'}`;
}

function renderizarCalendarioAgendamento() {
  const modal = document.querySelector('#modalCalendarioAgendamento');
  const grade = document.querySelector('#calendarioAgendamentoDias');
  const titulo = document.querySelector('#mesAnoAgendamento');
  if (!modal || !grade || !titulo) return;
  const mes = Number(modal.dataset.mes);
  const ano = Number(modal.dataset.ano);
  titulo.textContent = `${mesesAgendamento[mes]} de ${ano}`;
  const inicioMes = new Date(ano, mes, 1);
  const inicioSemana = (inicioMes.getDay() + 6) % 7;
  const ultimoDia = new Date(ano, mes + 1, 0).getDate();
  const diasMesAnterior = new Date(ano, mes, 0).getDate();
  const selecionada = document.querySelector('#data_agendada')?.value.split('T')[0];
  const hoje = dataLocalAgendamento();
  const dias = [];
  for (let indice = 0; indice < 42; indice += 1) {
    const numeroDia = indice - inicioSemana + 1;
    let dia = numeroDia;
    let mesDia = mes;
    let anoDia = ano;
    let classe = '';
    if (numeroDia < 1) { dia = diasMesAnterior + numeroDia; mesDia -= 1; classe = ' is-other-month'; }
    if (numeroDia > ultimoDia) { dia = numeroDia - ultimoDia; mesDia += 1; classe = ' is-other-month'; }
    if (mesDia < 0) { mesDia = 11; anoDia -= 1; }
    if (mesDia > 11) { mesDia = 0; anoDia += 1; }
    const valor = `${anoDia}-${String(mesDia + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
    if (valor === hoje) classe += ' is-today';
    if (valor === selecionada) classe += ' is-selected';
    dias.push(`<button type="button" class="agenda-calendar-day${classe}" data-agendamento-data="${valor}">${dia}</button>`);
  }
  grade.innerHTML = dias.join('');
}

function abrirCalendarioAgendamento() {
  const modal = document.querySelector('#modalCalendarioAgendamento');
  const campo = document.querySelector('#data_agendada');
  const hora = document.querySelector('#horaAgendamento');
  if (!modal || !campo || !hora) return;
  if (!campo.value) campo.value = `${dataLocalAgendamento()}T09:00`;
  hora.value = campo.value.split('T')[1] || '09:00';
  const selecionada = new Date(`${campo.value.split('T')[0]}T12:00:00`);
  modal.dataset.mes = String(selecionada.getMonth());
  modal.dataset.ano = String(selecionada.getFullYear());
  modal.hidden = false;
  renderizarCalendarioAgendamento();
  atualizarRotuloAgendamento();
}

function selecionarDataAgendamento(data) {
  const campo = document.querySelector('#data_agendada');
  const hora = document.querySelector('#horaAgendamento');
  if (!campo || !hora) return;
  campo.value = `${data}T${hora.value || '09:00'}`;
  renderizarCalendarioAgendamento();
  atualizarRotuloAgendamento();
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
    input.value = campo.dataset.editField === 'cnpj' ? formatBrazilianCnpj(valor) : valor;
    input.dataset.editField = campo.dataset.editField;
    if (campo.dataset.editField === 'cnpj') {
      input.inputMode = 'numeric';
      input.maxLength = 18;
      input.pattern = '\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}';
    }
    campo.replaceWith(input);
    input.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      const dados = { [input.dataset.editField]: input.dataset.editField === 'cnpj' ? formatBrazilianCnpj(input.value) : input.value.trim() };
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
        span.textContent = input.dataset.editField === 'id_setor'
          ? (atualizado.setor_nome || input.value)
          : input.dataset.editField === 'cnpj'
            ? formatBrazilianCnpj(atualizado.cnpj || input.value)
            : (atualizado[input.dataset.editField] || input.value);
        input.replaceWith(span);
        mostrarNotificacao('Alterações salvas com sucesso.');
      } catch (error) { mostrarErro(`Não foi possível salvar: ${error.message}`); input.focus(); }
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
      const { buscarChamadoPorId, buscarClientes, buscarEquipe, buscarSetores, atualizarChamado } = await import('./api.js');
      let [chamado, clientes, equipe, setores] = await Promise.all([buscarChamadoPorId(id), buscarClientes(), buscarEquipe(), buscarSetores()]);
      const cliente = clientes.find((item) => item.nome === chamado.cliente);
      const setorSelect = document.querySelector('#setorDestino');
      const tecnicoSelect = document.querySelector('#tecnicoDestino');
      const modalEscalonar = document.querySelector('#modalEscalonar');
      const modalEncerrar = document.querySelector('#modalEncerrar');
      const botaoIniciar = document.querySelector('#iniciarChamado');
      const botaoPausar = document.querySelector('#pausarChamado');
      const botaoEscalonar = document.querySelector('#escalonarChamado');
      const botaoEncerrar = document.querySelector('#encerrarChamado');
      const campoAgendamento = document.querySelector('#data_agendada');
      let timerChamado;

      const segundosAtendimento = () => {
        const acumulado = Number(chamado.tempo_decorrido_segundos || 0);
        const inicio = chamado.tempo_inicio ? new Date(chamado.tempo_inicio).getTime() : 0;
        return acumulado + (inicio && chamado.status === 'ANDAMENTO' ? Math.max(0, Math.floor((Date.now() - inicio) / 1000)) : 0);
      };

      const formatarTempo = (segundos) => `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;

      function atualizarTelaChamado() {
        const responsavel = equipe.find((item) => item.id_grupo_solucionadores == chamado.id_grupo_solucionadores);
        const status = chamado.status || 'ABERTO';
        const restantes = Math.max(0, 25 * 60 - segundosAtendimento());
        const badgeTempo = document.querySelector('#tempoChamado');
        setDetailText('chamado-titulo', `#${chamado.id_chamado}`);
        setDetailText('chamado-breadcrumb-cliente', chamado.cliente);
        setDetailText('chamado-cliente', chamado.cliente);
        setDetailText('chamado-contato-nome', chamado.contato_cliente || cliente?.contato || 'Não informado');
        setDetailText('chamado-contato-tel', chamado.telefone_contato || 'Não informado');
        setDetailText('chamado-telefone', chamado.telefone_cliente || cliente?.telefone || 'Não informado');
        setDetailText('chamado-email', chamado.email_cliente || cliente?.email || 'Não informado');
        setDetailText('chamado-data', formatarDataAbertura(chamado.data_abertura));
        setDetailText('chamado-descricao', chamado.descricao || 'Sem descrição cadastrada.');
        setDetailText('statusChamado', status);
        setDetailText('prioridadeChamadoDetalhe', chamado.prioridade || 'MÉDIA');
        document.querySelector('#statusChamado')?.classList.toggle('is-resolved', status === 'RESOLVIDO');
        renderizarHistoricoChamado(chamado.historico || []);
        const valoresSidebar = document.querySelectorAll('.ticket-sidebar .sidebar-info-list .info-value');
        if (valoresSidebar.length >= 2) {
          valoresSidebar[0].textContent = responsavel?.nome || 'Não atribuído';
          valoresSidebar[1].textContent = chamado.setor_nome || responsavel?.setor_nome || 'Não informado';
        }
        if (badgeTempo) {
          badgeTempo.textContent = `Tempo: ${formatarTempo(restantes)}`;
          badgeTempo.classList.toggle('is-warning', restantes <= 10 * 60 && restantes > 5 * 60);
          badgeTempo.classList.toggle('is-critical', restantes <= 5 * 60);
        }
        if (campoAgendamento) {
          if (chamado.data_agendada) campoAgendamento.value = `${chamado.data_agendada.slice(0, 10)}T${(chamado.hora_agendada || '09:00:00').slice(0, 5)}`;
          else if (!campoAgendamento.value) campoAgendamento.value = `${dataLocalAgendamento()}T09:00`;
          const horaAgendamento = document.querySelector('#horaAgendamento');
          if (horaAgendamento) {
            horaAgendamento.value = campoAgendamento.value.split('T')[1] || '09:00';
          }
          atualizarRotuloAgendamento();
        }
        const encerrado = status === 'RESOLVIDO';
        if (botaoIniciar) { botaoIniciar.disabled = encerrado || status === 'ANDAMENTO'; botaoIniciar.textContent = status === 'PAUSADO' ? 'Retomar chamado' : 'Iniciar chamado'; }
        if (botaoPausar) botaoPausar.disabled = status !== 'ANDAMENTO';
        if (botaoEscalonar) botaoEscalonar.disabled = status !== 'PAUSADO';
        if (botaoEncerrar) botaoEncerrar.disabled = encerrado || !['ANDAMENTO', 'PAUSADO'].includes(status);
        setDetailText('tempoFinalChamado', formatarTempo(segundosAtendimento()));
      }

      async function recarregarChamado() {
        chamado = await buscarChamadoPorId(id);
        atualizarTelaChamado();
      }

      async function executarAcao(dados, sucesso) {
        try {
          chamado = await atualizarChamado(id, dados);
          atualizarTelaChamado();
          if (sucesso) mostrarNotificacao(sucesso);
          return true;
        } catch (error) {
          mostrarErro(`Não foi possível atualizar o chamado: ${error.message}`);
          return false;
        }
      }

      const camposContato = document.querySelectorAll('[data-buscar-contatos]');
      const menuContatos = document.querySelector('#menuContatosChamado');
      const contatosCliente = cliente?.contatos?.length
        ? cliente.contatos
        : cliente?.contato ? [{ nome: cliente.contato, telefone: cliente.telefone }] : [];
      const definirMenuContatos = (aberto) => {
        if (!menuContatos) return;
        menuContatos.hidden = !aberto;
        camposContato.forEach((campo) => campo.setAttribute('aria-expanded', String(aberto)));
      };
      const renderizarContatosChamado = (termo = '') => {
        if (!menuContatos) return;
        const busca = normalizarTexto(termo);
        const contatosFiltrados = contatosCliente
          .map((contato, indice) => ({ ...contato, indice }))
          .filter((contato) => !busca || normalizarTexto(`${contato.nome} ${contato.telefone}`).includes(busca));
        menuContatos.innerHTML = contatosFiltrados.length
          ? contatosFiltrados.map((contato) => {
            const selecionado = contato.nome === chamado.contato_cliente && contato.telefone === chamado.telefone_contato;
            return `<button type="button" role="option" class="employee-contact-option" data-contato-indice="${contato.indice}" aria-selected="${selecionado}"><strong>${detailEscape(contato.nome || 'Contato')}</strong><span>${detailEscape(contato.telefone || 'Telefone não informado')}</span></button>`;
          }).join('')
          : '<span class="employee-contact-option">Nenhum contato encontrado para este cliente.</span>';
      };
      camposContato.forEach((campo) => {
        campo.addEventListener('focus', () => {
          renderizarContatosChamado(campo.value);
          definirMenuContatos(true);
        });
        campo.addEventListener('input', () => {
          renderizarContatosChamado(campo.value);
          definirMenuContatos(true);
        });
        campo.addEventListener('keydown', (event) => {
          if (event.key === 'Escape') definirMenuContatos(false);
          if (event.key === 'ArrowDown' && !menuContatos.hidden) {
            event.preventDefault();
            menuContatos.querySelector('[data-contato-indice]')?.focus();
          }
        });
      });
      menuContatos?.addEventListener('click', async (event) => {
        const opcao = event.target.closest('[data-contato-indice]');
        if (!opcao) return;
        const contato = contatosCliente[Number(opcao.dataset.contatoIndice)];
        if (!contato) return;
        try {
          chamado = await atualizarChamado(id, {
            acao: 'atualizar_contato',
            contato_cliente: contato.nome,
            telefone_contato: contato.telefone
          });
          atualizarTelaChamado();
          definirMenuContatos(false);
          mostrarNotificacao('Contato do chamado alterado com sucesso.');
        } catch (error) { mostrarErro(`Não foi possível alterar o contato: ${error.message}`); }
      });
      menuContatos?.addEventListener('pointerdown', (event) => {
        if (event.target.closest('[data-contato-indice]')) event.preventDefault();
      });
      document.addEventListener('click', (event) => {
        if (!event.target.closest('.employee-info-column')) definirMenuContatos(false);
      });

      const modalCalendario = document.querySelector('#modalCalendarioAgendamento');
      const alterarMesCalendario = (delta) => {
        if (!modalCalendario) return;
        let mes = Number(modalCalendario.dataset.mes) + delta;
        let ano = Number(modalCalendario.dataset.ano);
        if (mes < 0) { mes = 11; ano -= 1; }
        if (mes > 11) { mes = 0; ano += 1; }
        modalCalendario.dataset.mes = String(mes);
        modalCalendario.dataset.ano = String(ano);
        renderizarCalendarioAgendamento();
      };
      document.querySelector('#abrirCalendarioAgendamento')?.addEventListener('click', abrirCalendarioAgendamento);
      document.querySelector('#fecharCalendarioAgendamento')?.addEventListener('click', () => { if (modalCalendario) modalCalendario.hidden = true; });
      document.querySelector('#mesAnteriorAgendamento')?.addEventListener('click', () => alterarMesCalendario(-1));
      document.querySelector('#mesProximoAgendamento')?.addEventListener('click', () => alterarMesCalendario(1));
      document.querySelector('#calendarioAgendamentoDias')?.addEventListener('click', (event) => {
        const dia = event.target.closest('[data-agendamento-data]');
        if (dia) selecionarDataAgendamento(dia.dataset.agendamentoData);
      });
      const horaAgendamento = document.querySelector('#horaAgendamento');
      horaAgendamento?.addEventListener('input', () => {
        if (!horaAgendamento) return;
        const posicaoOriginal = horaAgendamento.selectionStart ?? horaAgendamento.value.length;
        const digitosAntesDoCursor = horaAgendamento.value.slice(0, posicaoOriginal).replace(/\D/g, '').length;
        const digitos = horaAgendamento.value.replace(/\D/g, '').slice(0, 4);
        const horarioFormatado = digitos.length > 2
          ? `${digitos.slice(0, 2)}:${digitos.slice(2)}`
          : digitos.length === 2 ? `${digitos}:` : digitos;
        if (horaAgendamento.value !== horarioFormatado) {
          horaAgendamento.value = horarioFormatado;
          const novaPosicao = Math.min(
            digitosAntesDoCursor + (digitosAntesDoCursor >= 2 && digitos.length >= 2 ? 1 : 0),
            horarioFormatado.length
          );
          horaAgendamento.setSelectionRange(novaPosicao, novaPosicao);
        }
        if (!horaAgendamento.checkValidity()) return;
        const data = campoAgendamento?.value.split('T')[0] || dataLocalAgendamento();
        if (campoAgendamento) campoAgendamento.value = `${data}T${horaAgendamento.value}`;
        atualizarRotuloAgendamento();
      });
      document.querySelector('#hojeCalendarioAgendamento')?.addEventListener('click', () => selecionarDataAgendamento(dataLocalAgendamento()));
      modalCalendario?.addEventListener('click', (event) => {
        if (event.target === modalCalendario) modalCalendario.hidden = true;
      });

      if (setorSelect && tecnicoSelect) {
        setorSelect.innerHTML = setores.map((setor) => `<option value="${detailEscape(setor.id_setor)}">${detailEscape(setor.nome)}</option>`).join('');
        setorSelect.value = String(chamado.id_setor || '');
        const atualizarTecnicosDestino = () => {
          const tecnicos = equipe.filter((membro) => String(membro.id_setor) === setorSelect.value && (membro.status || 'ATIVO') === 'ATIVO');
          tecnicoSelect.innerHTML = tecnicos.map((membro) => `<option value="${detailEscape(membro.id_grupo_solucionadores)}">${detailEscape(membro.nome || membro.descricao || 'Técnico')}</option>`).join('');
          tecnicoSelect.disabled = tecnicos.length === 0;
        };
        setorSelect.addEventListener('change', atualizarTecnicosDestino);
        atualizarTecnicosDestino();
      }

      document.querySelectorAll('[data-fechar-modal]').forEach((botao) => botao.addEventListener('click', () => {
        modalEscalonar?.classList.remove('active');
        modalEncerrar?.classList.remove('active');
      }));
      [modalEscalonar, modalEncerrar].forEach((modal) => modal?.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('active');
      }));
      botaoIniciar?.addEventListener('click', () => executarAcao({ acao: 'iniciar' }, 'Atendimento iniciado.'));
      botaoPausar?.addEventListener('click', () => executarAcao({ acao: 'pausar' }, 'Atendimento pausado.'));
      botaoEscalonar?.addEventListener('click', () => {
        if (chamado.status === 'PAUSADO') modalEscalonar?.classList.add('active');
      });
      botaoEncerrar?.addEventListener('click', () => {
        setDetailText('tempoFinalChamado', formatarTempo(segundosAtendimento()));
        modalEncerrar?.classList.add('active');
      });
      document.querySelector('#formEscalonar')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const dados = Object.fromEntries(new FormData(event.currentTarget));
        await comCarregamento(event.currentTarget.querySelector('[type="submit"]'), async () => {
          if (await executarAcao({ acao: 'escalonar', ...dados }, 'Chamado escalonado.')) modalEscalonar?.classList.remove('active');
        }, 'Escalonando...');
      });
      document.querySelector('#formEncerrar')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        await comCarregamento(form.querySelector('[type="submit"]'), async () => {
          try {
            chamado = await atualizarChamado(id, { acao: 'encerrar', descricao_final: new FormData(form).get('descricao_final') });
            atualizarTelaChamado();
            modalEncerrar?.classList.remove('active');
            form.reset();
            mostrarNotificacao('Chamado resolvido com sucesso.');
            if (!chamado.email_enviado && chamado.aviso_email) mostrarErro(chamado.aviso_email);
          } catch (error) {
            mostrarErro(`Não foi possível encerrar o chamado: ${error.message}`);
          }
        }, 'Encerrando...');
      });
      document.querySelector('#salvarAgendamento')?.addEventListener('click', async () => {
        const data = campoAgendamento?.value.split('T')[0];
        const campoHora = document.querySelector('#horaAgendamento');
        const hora = campoHora?.value;
        if (!data || !hora || !campoHora?.checkValidity()) { campoHora?.reportValidity(); return; }
        if (await executarAcao({ acao: 'agendar', data_agendada: `${data}T${hora}` }, 'Agendamento salvo.')) modalCalendario.hidden = true;
      });
      timerChamado = window.setInterval(() => {
        if (chamado.status === 'ANDAMENTO') atualizarTelaChamado();
      }, 1000);
      atualizarTelaChamado();
    }

    if (path.includes('cliente-detalhe.html')) {
      const { buscarClientes, buscarChamados, criarContatoCliente } = await import('./api.js');
      const [clientes, chamados] = await Promise.all([buscarClientes(), buscarChamados()]);
      let cliente = clientes.find((item) => item.id_usuario == id);
      if (!cliente) throw new Error('Cliente não encontrado.');
      setDetailText('cli-nome', cliente.nome);
      setDetailText('cli-breadcrumb', cliente.nome);
      setDetailText('cli-avatar', detailInitials(cliente.nome));
      setDetailText('cli-cnpj', formatBrazilianCnpj(cliente.cnpj));
      setDetailText('cli-email', cliente.email);
      setDetailText('cli-telefone', cliente.telefone_empresa || cliente.telefone);
      setDetailText('cli-endereco', cliente.endereco);
      setDetailText('cli-fatura', cliente.plano);
      setDetailText('cli-contrato', cliente.acoes);
      const contatos = cliente.contatos?.length ? cliente.contatos : [{ nome: cliente.contato, email: cliente.email, telefone: cliente.telefone }];
      const listaContatos = document.querySelector('#cli-contatos');
      if (listaContatos) {
        listaContatos.innerHTML = contatos.map((contato) => `<div class="client-contact-detail"><strong>${detailEscape(contato.nome || 'Contato')}</strong><span>${detailEscape(contato.email || 'E-mail não informado')}</span><span>${detailEscape(contato.telefone || 'Telefone não informado')}</span></div>`).join('') || '<span class="info-value">Nenhum contato cadastrado.</span>';
      }
      configurarDetalheEditavel('cliente', cliente);
      const botaoEditarCliente = document.querySelector('[data-edit-scope="cliente"]');
      const botaoAdicionarContato = document.querySelector('#adicionar-contato-cliente');
      const modalContato = document.querySelector('#modalContatoCliente');
      const formularioContato = document.querySelector('#formContatoCliente');
      const mensagemContato = document.querySelector('#mensagemContatoCliente');
      const renderizarContatosCliente = () => {
        const listaAtualizada = cliente.contatos || [];
        if (listaContatos) {
          listaContatos.innerHTML = listaAtualizada.map((contato) => `<div class="client-contact-detail"><strong>${detailEscape(contato.nome || 'Contato')}</strong><span>${detailEscape(contato.email || 'E-mail não informado')}</span><span>${detailEscape(contato.telefone || 'Telefone não informado')}</span></div>`).join('') || '<span class="info-value">Nenhum contato cadastrado.</span>';
        }
      };
      botaoEditarCliente?.addEventListener('click', () => { botaoAdicionarContato.hidden = false; });
      botaoAdicionarContato?.addEventListener('click', () => {
        formularioContato?.reset();
        if (mensagemContato) mensagemContato.textContent = '';
        modalContato?.showModal();
        formularioContato?.elements.nome.focus();
      });
      document.querySelector('#fecharModalContatoCliente')?.addEventListener('click', () => modalContato?.close());
      document.querySelector('#cancelarContatoCliente')?.addEventListener('click', () => modalContato?.close());
      formularioContato?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const dados = Object.fromEntries(new FormData(formularioContato).entries());
        await comCarregamento(formularioContato.querySelector('[type="submit"]'), async () => {
          try {
            dados.telefone = formatBrazilianPhone(dados.telefone);
            const resultado = await criarContatoCliente(cliente.id_usuario, dados);
            cliente.contatos = resultado.contatos;
            renderizarContatosCliente();
            modalContato?.close();
            if (mensagemContato) mensagemContato.textContent = '';
            mostrarNotificacao('Contato cadastrado com sucesso.');
          } catch (error) {
            if (mensagemContato) mensagemContato.textContent = `Não foi possível adicionar o contato: ${error.message}`;
            mostrarErro(`Não foi possível adicionar o contato: ${error.message}`);
          }
        }, 'Salvando...');
      });
      configurarEquipamentos(id);
      const botaoStatusCliente = document.querySelector('#desativarCliente');
      const atualizarStatusCliente = () => {
        const ativo = (cliente.status || 'ATIVO').toUpperCase() === 'ATIVO';
        const badge = document.querySelector('#cli-status');
        if (badge) {
          badge.textContent = ativo ? 'Cliente Ativo' : 'Cliente Desativado';
          badge.classList.toggle('badge-green', ativo);
          badge.classList.toggle('badge-red', !ativo);
        }
        if (botaoStatusCliente) {
          botaoStatusCliente.textContent = ativo ? 'Desativar Cliente' : 'Ativar Cliente';
          botaoStatusCliente.classList.toggle('is-activate', !ativo);
        }
      };
      atualizarStatusCliente();
      botaoStatusCliente?.addEventListener('click', async () => {
        const ativo = (cliente.status || 'ATIVO').toUpperCase() === 'ATIVO';
        const novoStatus = ativo ? 'INATIVO' : 'ATIVO';
        if (!window.confirm(`Deseja ${ativo ? 'desativar' : 'ativar'} este cliente?`)) return;
        try {
          cliente = await atualizarCliente(cliente.id_usuario, { status: novoStatus });
          atualizarStatusCliente();
          mostrarNotificacao(`Cliente ${novoStatus === 'ATIVO' ? 'ativado' : 'desativado'} com sucesso.`);
        } catch (error) { mostrarErro(`Não foi possível atualizar o status: ${error.message}`); }
      });
      const table = document.querySelector('#tabela-chamados-cliente tbody');
      const tickets = chamados.filter((chamado) => chamado.cliente === cliente.nome);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td><td>${detailEscape(chamado.classificacao)}</td></tr>`).join('') || '<tr><td colspan="4">Nenhum chamado encontrado para este cliente.</td></tr>';
    }

    if (path.includes('equipe-detalhe.html')) {
      const { buscarEquipe, buscarChamados, buscarSetores } = await import('./api.js');
      const [equipe, chamados, setores] = await Promise.all([buscarEquipe(), buscarChamados(), buscarSetores()]);
      const membro = equipe.find((item) => item.id_grupo_solucionadores == id);
      if (!membro) throw new Error('Membro da equipe não encontrado.');
      const setorMembro = setores.find((item) => item.id_setor == membro.id_setor);
      const nomeNivel = membro.nivel && setorMembro?.niveis?.[Number(membro.nivel) - 1]
        ? setorMembro.niveis[Number(membro.nivel) - 1]
        : membro.nivel ? `Nível ${membro.nivel}` : 'Sem nível';
      setDetailText('membro-nome', membro.nome);
      setDetailText('membro-breadcrumb', membro.nome);
      setDetailText('membro-avatar', detailInitials(membro.nome));
      setDetailText('membro-setor', membro.setor_nome || 'Sem setor');
      setDetailText('membro-nivel', nomeNivel);
      setDetailText('membro-email', membro.email);
      setDetailText('membro-telefone', membro.telefone || 'Não informado');
      setDetailText('membro-admissao', detailDate(membro.data_inicio));
      setDetailText('membro-valor-hora', membro.valor_hora ? `R$ ${Number(membro.valor_hora).toFixed(2).replace('.', ',')}` : 'Não informado');
      configurarDetalheEditavel('equipe', membro);
      const botaoStatusMembro = document.querySelector('#desativarMembro');
      const atualizarStatusMembro = () => {
        const ativo = (membro.status || 'ATIVO').toUpperCase() === 'ATIVO';
        const badge = document.querySelector('#membro-status');
        if (badge) {
          badge.textContent = ativo ? 'Ativo' : 'Desativado';
          badge.classList.toggle('badge-green', ativo);
          badge.classList.toggle('badge-red', !ativo);
        }
        if (botaoStatusMembro) {
          botaoStatusMembro.textContent = ativo ? 'Desativar Técnico' : 'Ativar Técnico';
          botaoStatusMembro.classList.toggle('is-activate', !ativo);
        }
      };
      atualizarStatusMembro();
      botaoStatusMembro?.addEventListener('click', async () => {
        const ativo = (membro.status || 'ATIVO').toUpperCase() === 'ATIVO';
        const novoStatus = ativo ? 'INATIVO' : 'ATIVO';
        if (!window.confirm(`Deseja ${ativo ? 'desativar' : 'ativar'} este técnico?`)) return;
        try {
          const atualizado = await atualizarMembro(membro.id_grupo_solucionadores, { status: novoStatus });
          membro.status = atualizado.status;
          atualizarStatusMembro();
          mostrarNotificacao(`Técnico ${novoStatus === 'ATIVO' ? 'ativado' : 'desativado'} com sucesso.`);
        } catch (error) { mostrarErro(`Não foi possível atualizar o status: ${error.message}`); }
      });
      setDetailText('membro-certificacoes', 'Não informado');
      document.querySelectorAll('.team-stats-grid .stat-box-number').forEach((element) => { element.textContent = '—'; });
      const skills = document.querySelector('.skills-tags-container');
      if (skills) skills.textContent = 'Nenhuma especialidade cadastrada.';
      const table = document.querySelector('#tabela-chamados-tecnico tbody');
      const tickets = chamados.filter((chamado) => chamado.id_grupo_solucionadores == membro.id_grupo_solucionadores);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado atribuído a este membro.</td></tr>';
    }
  } catch (error) {
    console.error('Não foi possível carregar os detalhes:', error);
    const title = document.querySelector('.page-title-bar h1');
    if (title) title.textContent = error.message || 'Não foi possível carregar os detalhes.';
  }
});