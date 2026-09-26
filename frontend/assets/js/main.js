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
  document.querySelectorAll('.user-avatar img').forEach((image) => {
    image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`;
  });
}

let clientesEmMemoria = [];

function renderizarClientes(clientes) {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  tabela.innerHTML = clientes.map((cliente) => `<tr onclick="window.location.href='cliente-detalhe.html?id=${cliente.id_usuario}'" style="cursor: pointer;"><td><strong>${cliente.nome || '-'}</strong></td><td>${cliente.cnpj || '-'}</td><td>${cliente.contato || '-'}</td><td>${cliente.telefone || '-'}</td><td><span class="status-badge status-success">${cliente.status || 'Ativo'}</span></td></tr>`).join('') || '<tr><td colspan="5">Nenhum cliente encontrado.</td></tr>';
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
  const contatos = [...form.querySelectorAll('[data-contato-row]')].map((linha) => ({
    email: linha.querySelector('[data-contato-email]').value.trim(),
    nome: linha.querySelector('[data-contato-nome]').value.trim(),
    telefone: linha.querySelector('[data-contato-telefone]').value.trim()
  }));
  const primeiroContato = contatos[0];
  const dados = {
    nome: form.elements.nome.value.trim(),
    cnpj: form.elements.cnpj.value.trim(),
    email: primeiroContato.email,
    contato: primeiroContato.nome,
    telefone: primeiroContato.telefone,
    contatos
  };
  try {
    const { criarCliente } = await import('./api.js');
    await criarCliente(dados);
    closeModal('modal-cliente'); form.reset(); resetarContatosCliente(); await carregarClientes(); alert('Cliente cadastrado com sucesso.');
  } catch (error) { alert(`Não foi possível cadastrar: ${error.message}`); }
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
    : icone === 'chevron-down'
      ? '<path d="m6 9 6 6 6-6" />'
      : '<path d="m9 18 6-6-6-6" />';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${caminhos}</svg>`;
}

function renderizarSetor(setor) {
  const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == setor.id_setor);
  const niveis = (setor.niveis || []).map((nivel, indice) => {
    const membrosDoNivelAtual = participantes.filter((membro) => Number(membro.nivel) === indice + 1);
    const membrosHtml = membrosDoNivelAtual.map((membro) => `<a href="equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}" target="_blank" rel="noopener noreferrer"><strong>${membro.nome || '-'}</strong><span>${membro.email || 'Sem e-mail'}</span></a>`).join('') || '<span class="empty-row">Nenhum funcionário neste nível.</span>';
    return `<div class="sector-level-row"><div class="level-summary"><strong>${nivel}</strong><small>${membrosDoNivelAtual.length} funcionário(s) alocado(s)</small></div><div class="level-actions"><button type="button" class="level-action" title="Mostrar funcionários de ${nivel}" aria-label="Mostrar funcionários de ${nivel}" aria-expanded="false" data-level-action="details" data-setor-id="${setor.id_setor}" data-level-index="${indice + 1}">${iconeNivel('chevron')}</button><button type="button" class="level-action" title="Adicionar técnico em ${nivel}" aria-label="Adicionar técnico em ${nivel}" data-level-action="add" data-setor-id="${setor.id_setor}" data-level-index="${indice + 1}">${iconeNivel('plus')}</button></div><div class="level-members-inline" hidden>${membrosHtml}</div></div>`;
  }).join('');
  return `<tr><td colspan="3"><details class="sector-details"><summary><span><strong>${setor.nome}</strong><small>${setor.niveis?.length ? `${setor.niveis.length} nível(is)` : 'Sem níveis cadastrados'}</small></span><span class="sector-summary-actions"><span class="status-badge status-info">${participantes.length} participante(s)</span><button type="button" class="sector-delete-button" title="Excluir setor" aria-label="Excluir setor" data-delete-sector="${setor.id_setor}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14H5V6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg></button></span></summary>${niveis ? `<div class="sector-levels">${niveis}</div>` : '<div class="sector-levels"><span class="empty-row">Nenhum nível cadastrado.</span></div>'}</details></td></tr>`;
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

function abrirNovoFuncionario(setorId, nivel) {
  const setor = setoresEmMemoria.find((item) => item.id_setor == setorId);
  const form = document.querySelector('#form-nova-equipe');
  const campoSetor = form?.elements.setor;
  const campoNivel = form?.elements.nivel;
  if (!setor || !form || !campoSetor || !campoNivel) return;
  form.reset();
  campoSetor.value = setor.nome;
  campoNivel.innerHTML = (setor.niveis || []).map((nome, indice) => `<option value="${indice + 1}">${nome}</option>`).join('') || '<option value="">Sem níveis cadastrados</option>';
  campoNivel.value = String(nivel);
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

const equipamentosPadrao = [
  { nome: 'Servidores AD/Files', quantidade: 2 },
  { nome: 'Firewall Fortinet', quantidade: 1 },
  { nome: 'Switches Core', quantidade: 2 },
  { nome: 'Access Points', quantidade: 6 },
  { nome: 'Workstations', quantidade: 20 },
  { nome: 'Printers IP', quantidade: 3 }
];

function equipamentosDoCliente(id) {
  const chave = `helpti-equipamentos-${id}`;
  const salvos = JSON.parse(localStorage.getItem(chave) || 'null');
  if (Array.isArray(salvos)) return salvos;
  localStorage.setItem(chave, JSON.stringify(equipamentosPadrao));
  return [...equipamentosPadrao];
}

function renderizarEquipamentos(id) {
  const lista = document.querySelector('#mapa-equipamentos');
  if (!lista) return;
  const equipamentos = equipamentosDoCliente(id);
  lista.innerHTML = equipamentos.map((equipamento, indice) => `<div class="asset-item"><span class="asset-name">${detailEscape(equipamento.nome)}</span><strong class="asset-count">${Number(equipamento.quantidade) || 0} un</strong><div class="asset-actions"><button type="button" data-editar-equipamento="${indice}" aria-label="Editar ${detailEscape(equipamento.nome)}">Editar</button><button type="button" data-apagar-equipamento="${indice}" aria-label="Apagar ${detailEscape(equipamento.nome)}">Apagar</button></div></div>`).join('');
  const total = equipamentos.reduce((soma, equipamento) => soma + (Number(equipamento.quantidade) || 0), 0);
  document.querySelector('#equipamentos-total').textContent = `Total: ${total} equipamento(s) cadastrado(s)`;
}

function salvarEquipamento(id, indice = null) {
  const equipamentos = equipamentosDoCliente(id);
  const atual = indice === null ? { nome: '', quantidade: 1 } : equipamentos[indice];
  const nome = window.prompt('Nome do equipamento:', atual.nome);
  if (nome === null || !nome.trim()) return;
  const quantidade = window.prompt('Número de equipamentos:', atual.quantidade);
  if (quantidade === null || !/^\d+$/.test(quantidade) || Number(quantidade) < 0) return alert('Informe uma quantidade inteira válida.');
  const equipamento = { nome: nome.trim(), quantidade: Number(quantidade) };
  if (indice === null) equipamentos.push(equipamento); else equipamentos[indice] = equipamento;
  localStorage.setItem(`helpti-equipamentos-${id}`, JSON.stringify(equipamentos));
  renderizarEquipamentos(id);
}

function configurarEquipamentos(id) {
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
    alert('Setor apagado com sucesso.');
  } catch (error) { alert(`Não foi possível apagar o setor: ${error.message}`); }
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
  if (!/^[A-Za-zÀ-ÿ ]+$/.test(form.elements.nome.value.trim()) || !/^[A-Za-zÀ-ÿ ]+$/.test(setorNome)) {
    form.reportValidity();
    return;
  }
  try {
    const { criarMembro, criarSetor } = await import('./api.js');
    let setor = setoresEmMemoria.find((item) => item.nome.trim().toLowerCase() === setorNome.toLowerCase());
    if (!setor) setor = await criarSetor({ nome: setorNome, descricao: '' });
    await criarMembro({
      nome: form.elements.nome.value.trim(),
      email: form.elements.email.value.trim(),
      telefone: form.elements.telefone.value.trim(),
      valor_hora: form.elements.valor_hora.value,
      id_setor: setor.id_setor,
      nivel: form.elements.nivel.value,
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
  if (action.dataset.levelAction === 'add') abrirNovoFuncionario(setorId, nivel);
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
  resetarContatosCliente();
  document.querySelector('#adicionarContatoCliente')?.addEventListener('click', adicionarContatoCliente);
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
        setDetailText('chamado-data', detailDate(chamado.data_abertura));
        setDetailText('chamado-descricao', chamado.descricao || 'Sem descrição cadastrada.');
        setDetailText('statusChamado', status);
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
        if (campoAgendamento && chamado.data_agendada) {
          campoAgendamento.value = `${chamado.data_agendada.slice(0, 10)}T${(chamado.hora_agendada || '09:00:00').slice(0, 5)}`;
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
          if (sucesso) alert(sucesso);
          return true;
        } catch (error) {
          alert(`Não foi possível atualizar o chamado: ${error.message}`);
          return false;
        }
      }

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
        if (await executarAcao({ acao: 'escalonar', ...dados }, 'Chamado escalonado.')) modalEscalonar?.classList.remove('active');
      });
      document.querySelector('#formEncerrar')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const botaoSubmit = event.currentTarget.querySelector('[type="submit"]');
        botaoSubmit.disabled = true;
        try {
          chamado = await atualizarChamado(id, { acao: 'encerrar', descricao_final: new FormData(event.currentTarget).get('descricao_final') });
          atualizarTelaChamado();
          modalEncerrar?.classList.remove('active');
          event.currentTarget.reset();
          alert('Chamado resolvido e e-mail enviado ao cliente.');
        } catch (error) {
          alert(`Não foi possível encerrar o chamado: ${error.message}`);
        } finally {
          botaoSubmit.disabled = false;
        }
      });
      document.querySelector('#salvarAgendamento')?.addEventListener('click', async () => {
        if (!campoAgendamento?.value) { campoAgendamento?.reportValidity(); return; }
        await executarAcao({ acao: 'agendar', data_agendada: campoAgendamento.value }, 'Agendamento salvo.');
      });
      timerChamado = window.setInterval(() => {
        if (chamado.status === 'ANDAMENTO') atualizarTelaChamado();
      }, 1000);
      atualizarTelaChamado();
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
      configurarEquipamentos(id);
      document.querySelector('#desativarCliente')?.addEventListener('click', async () => {
        if (!window.confirm('Tem certeza de que deseja apagar este cliente?')) return;
        try { await excluirCliente(cliente.id_usuario); window.location.href = 'clientes.html'; } catch (error) { alert(`Não foi possível apagar: ${error.message}`); }
      });
      const table = document.querySelector('#tabela-chamados-cliente tbody');
      const tickets = chamados.filter((chamado) => chamado.cliente === cliente.nome);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td><td>${detailEscape(chamado.classificacao)}</td></tr>`).join('') || '<tr><td colspan="4">Nenhum chamado encontrado para este cliente.</td></tr>';
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
      setDetailText('membro-telefone', membro.telefone || 'Não informado');
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
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado atribuído a este membro.</td></tr>';
    }
  } catch (error) {
    console.error('Não foi possível carregar os detalhes:', error);
    const title = document.querySelector('.page-title-bar h1');
    if (title) title.textContent = error.message || 'Não foi possível carregar os detalhes.';
  }
});