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
  tabela.innerHTML = clientes.map((cliente) => `<tr onclick="window.location.href='cliente-detalhe.html?id=${cliente.id_usuario}'" style="cursor: pointer;"><td><strong>${cliente.nome || '-'}</strong></td><td>${cliente.cnpj || '-'}<br>${cliente.contato || ''}</td><td>${cliente.plano || '-'}</td><td><span class="status-badge status-success">${cliente.status || 'Ativo'}</span></td><td>${cliente.acoes || '-'}</td></tr>`).join('') || '<tr><td colspan="5">Nenhum cliente encontrado.</td></tr>';
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
    tabela.innerHTML = setoresEmMemoria.map((setor) => {
      const participantes = equipeEmMemoria.filter((membro) => membro.id_setor == setor.id_setor);
      const lista = participantes.map((membro) => `<li><a href="equipe-detalhe.html?id=${encodeURIComponent(membro.id_grupo_solucionadores)}"><strong>${membro.nome || '-'}</strong><span>${membro.cargo || 'Sem função'}</span></a></li>`).join('') || '<li class="empty-row">Nenhum participante neste setor.</li>';
      return `<tr><td colspan="3"><details class="sector-details"><summary><span><strong>${setor.nome}</strong><small>${setor.descricao || 'Sem descrição'}</small></span><span class="status-badge status-info">${participantes.length} participante(s)</span></summary><ul class="sector-members">${lista}</ul></details></td></tr>`;
    }).join('') || '<tr><td colspan="3">Nenhum setor cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="3">${error.message}</td></tr>`; }
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
  const inputs = form.querySelectorAll('input, textarea');
  try {
    const { criarSetor } = await import('./api.js');
    await criarSetor({ nome: inputs[0].value.trim(), descricao: inputs[1].value.trim() });
    closeModal('modal-setor'); form.reset(); await carregarSetores(); alert('Setor criado com sucesso.');
  } catch (error) { alert(`Não foi possível criar o setor: ${error.message}`); }
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

document.addEventListener('click', () => document.getElementById('profileDropdown')?.classList.remove('active'));
document.addEventListener('click', (event) => {
  const controle = document.querySelector('.client-filter-control');
  if (controle && !controle.contains(event.target)) {
    controle.classList.remove('is-open');
    document.querySelector('#botaoFiltroClientes')?.setAttribute('aria-expanded', 'false');
  }
});
document.querySelector('a[href="login.html"]')?.addEventListener('click', encerrarSessao);
document.addEventListener('DOMContentLoaded', () => { mostrarPerfil(); carregarClientes(); carregarEquipe(); carregarSetores(); });
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
      tabelaChamados.innerHTML = chamadosCliente.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${chamado.id_chamado}'" style="cursor: pointer;"><td>#${chamado.id_chamado}</td><td>${chamado.assunto || '-'}</td><td>${chamado.status || '-'}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado encontrado para este cliente.</td></tr>';
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
      setDetailText('chamado-titulo', `#${chamado.id_chamado} — ${chamado.assunto || 'Sem assunto'}`);
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
