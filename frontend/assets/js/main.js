import { API_URL, buscarChamados, buscarClientes, atualizarCliente, atualizarMembro, criarDocumentacao } from './api.js';
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

const PAGINA_POR_PERMISSAO = {
  'dashboard.html': 'dashboard',
  'chamados.html': 'chamados',
  'chamados-detalhe.html': 'chamados',
  'clientes.html': 'clientes',
  'cliente-detalhe.html': 'clientes',
  'equipe.html': 'equipe',
  'relatorios.html': 'relatorios',
  'educacao.html': 'educacao',
  'settings.html': 'configuracoes'
};

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
    if (usuario.fotoPerfil) document.querySelectorAll('.profile-photo-avatar img').forEach((image) => { image.src = usuario.fotoPerfil; });
  } catch (error) {
  }
}

function carregarImagemPerfil(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Não foi possível abrir a imagem.'));
    reader.onload = () => {
      const imagem = new Image();
      imagem.onerror = () => reject(new Error('O arquivo selecionado não é uma imagem válida.'));
      imagem.onload = () => {
        const lado = Math.min(imagem.naturalWidth, imagem.naturalHeight, 512);
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const contexto = canvas.getContext('2d');
        const x = (imagem.naturalWidth - lado) / 2;
        const y = (imagem.naturalHeight - lado) / 2;
        contexto.drawImage(imagem, x, y, lado, lado, 0, 0, 512, 512);
        resolve(canvas.toDataURL('image/jpeg', 0.86));
      };
      imagem.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

document.querySelector('.profile-photo-edit')?.addEventListener('click', (event) => {
  event.preventDefault();
  event.stopPropagation();
  document.querySelector('.profile-photo-input')?.click();
});
document.querySelector('.profile-photo-input')?.addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10_000_000) {
    mostrarNotificacao('Escolha uma imagem JPEG, PNG ou WebP de até 10 MB.', 'error');
    return;
  }
  try {
    const foto = await carregarImagemPerfil(file);
    const response = await fetch(`${API_URL}/perfil/foto`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ foto }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.erro || 'Não foi possível salvar a foto.');
    document.querySelectorAll('.profile-photo-avatar img').forEach((image) => { image.src = data.fotoPerfil; });
    mostrarNotificacao('Foto do perfil atualizada.');
  } catch (error) {
    mostrarNotificacao(error.message || 'Não foi possível salvar a foto.', 'error');
  }
});

function renderizarClientes(clientes) {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  tabela.innerHTML = clientes.map((cliente) => {
    const ativo = (cliente.status || 'ATIVO').toUpperCase() === 'ATIVO';
    return `<tr class="client-row" data-cliente-id="${detailEscape(cliente.id_cliente)}"><td><strong>${detailEscape(cliente.nome)}</strong></td><td>${detailEscape(formatBrazilianCnpj(cliente.cnpj) || '-')}</td><td>${detailEscape(cliente.contato)}</td><td>${detailEscape(cliente.telefone_empresa || cliente.telefone)}</td><td><div class="client-row-actions"><span class="client-status-badge ${ativo ? 'is-active' : 'is-inactive'}">${ativo ? 'Ativo' : 'Desativado'}</span><button type="button" class="client-delete-button" data-excluir-cliente="${detailEscape(cliente.id_cliente)}" aria-label="Excluir cliente ${detailEscape(cliente.nome || '')}" title="Excluir cliente"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14H5V6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg></button></div></td></tr>`;
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
      const possuiChamado = chamadosEmMemoria.some((chamado) => chamado.id_cliente === cliente.id_cliente && chamado.status === statusChamado);
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
    tabela.innerHTML = equipe.map((membro) => {
      const nome = membro.nome || membro.descricao || 'Funcionário';
      const detalhesId = `dados-funcionario-${membro.id_grupo_solucionadores}`;
      const detalhes = [
        ['E-mail', membro.email || 'Não informado'],
        ['Telefone', membro.telefone || 'Não informado'],
        ['Data de início', detailDate(membro.data_inicio)],
        ['Nível', membro.nivel ? `Nível ${membro.nivel}` : 'Não informado'],
      ];
      return `
        <tr class="team-member-row">
          <td>
            <div class="team-member-name">
              <button class="team-member-toggle" type="button" aria-expanded="false"
                aria-controls="${detailEscape(detalhesId)}"
                aria-label="Mostrar dados de ${detailEscape(nome)}"
                title="Mostrar dados do funcionário" data-toggle-member>
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
                  fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                  stroke-linejoin="round" aria-hidden="true">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </button>
              <strong>${detailEscape(nome)}</strong>
            </div>
          </td>
          <td>${detailEscape(membro.cargo || 'Técnico')}</td>
          <td>${detailEscape(membro.setor || 'Sem setor')}</td>
          <td><span class="status-badge status-info">${detailEscape(membro.status || 'ATIVO')}</span></td>
          <td><button class="danger-icon-button" type="button" data-remove-member="${detailEscape(membro.id_grupo_solucionadores)}" aria-label="Excluir funcionário ${detailEscape(nome)}" title="Excluir funcionário">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14H5V6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg>
          </button></td>
        </tr>
        <tr id="${detailEscape(detalhesId)}" class="team-member-details-row" hidden>
          <td colspan="5">
            <div class="team-member-details">
              ${detalhes.map(([rotulo, valor]) => `
                <div class="team-member-detail">
                  <span>${detailEscape(rotulo)}</span>
                  <strong>${detailEscape(valor)}</strong>
                </div>
              `).join('')}
            </div>
          </td>
        </tr>`;
    }).join('') || '<tr><td colspan="5">Nenhum funcionário cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="5">${detailEscape(error.message)}</td></tr>`; }
}

async function salvarMembro(event) {
  event.preventDefault();
  const form = event.target;
  const setorNome = form.elements.setor.value.trim();
  if (!/^[A-Za-zÀ-ÿ ]+$/.test(form.elements.nome.value.trim()) || !setorNome) {
    form.reportValidity();
    return;
  }
  await comCarregamento(form.querySelector('[type="submit"]'), async () => {
    try {
      const { criarMembro } = await import('./api.js');
      await criarMembro({
        nome: form.elements.nome.value.trim(),
        email: form.elements.email.value.trim(),
        telefone: formatBrazilianPhone(form.elements.telefone.value),
        setor: setorNome
      });
      closeModal('modal-equipe'); form.reset(); await carregarEquipe(); mostrarNotificacao('Funcionário cadastrado com sucesso.');
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
window.salvarConfiguracoes = salvarConfiguracoes;
window.cancelarConfigurações = cancelarConfigurações;

document.addEventListener('click', () => document.getElementById('profileDropdown')?.classList.remove('active'));
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
  carregarClientes();
  carregarEquipe();
  document.querySelector('#tabelaEquipe')?.addEventListener('click', async (event) => {
    const remover = event.target.closest('[data-remove-member]');
    if (remover) {
      event.preventDefault();
      event.stopPropagation();
      if (!window.confirm('Tem certeza que deseja excluir este funcionário?')) return;
      try {
        const { excluirMembro } = await import('./api.js');
        await excluirMembro(remover.dataset.removeMember);
        await carregarEquipe();
        mostrarNotificacao('Funcionário excluído com sucesso.');
      } catch (error) {
        mostrarErro(`Não foi possível excluir o funcionário: ${error.message}`);
      }
      return;
    }

    const botao = event.target.closest('[data-toggle-member]');
    if (!botao) return;
    const detalhes = document.getElementById(botao.getAttribute('aria-controls'));
    if (!detalhes) return;
    const expandido = botao.getAttribute('aria-expanded') !== 'true';
    const nome = botao.parentElement.querySelector('strong')?.textContent || 'funcionário';
    botao.setAttribute('aria-expanded', String(expandido));
    botao.setAttribute('aria-label', `${expandido ? 'Ocultar' : 'Mostrar'} dados de ${nome}`);
    botao.title = `${expandido ? 'Ocultar' : 'Mostrar'} dados do funcionário`;
    detalhes.hidden = !expandido;
  });
});
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('#buscaClientes')?.addEventListener('input', filtrarClientes);
  document.querySelector('#tabelaClientes')?.addEventListener('click', async (event) => {
    const botao = event.target.closest('[data-excluir-cliente]');
    if (!botao) {
      const linha = event.target.closest('tr[data-cliente-id]');
      if (linha) {
        window.location.href = `cliente-detalhe.html?id=${encodeURIComponent(linha.dataset.clienteId)}`;
      }
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm('Tem certeza que deseja excluir este cliente?')) return;
    try {
      const { excluirCliente } = await import('./api.js');
      await excluirCliente(botao.dataset.excluirCliente);
      await carregarClientes();
      mostrarNotificacao('Cliente excluído com sucesso.');
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
      document.getElementById('chamado-status').textContent = chamado.status;
      document.getElementById('chamado-descricao').textContent = chamado.descricao || 'Sem descrição cadastrada.';
    }
  }

  if (false && path.includes('cliente-detalhe.html') && idSelecionado) {
    const { buscarClientes, buscarChamados } = await import('./api.js');
    const [clientes, chamados] = await Promise.all([buscarClientes(), buscarChamados()]);
    const cliente = clientes.find((item) => item.id_cliente == idSelecionado);
    if (cliente) {
      document.getElementById('cli-nome').textContent = cliente.nome;
      document.getElementById('cli-email').textContent = cliente.email;
      document.getElementById('cli-telefone').textContent = cliente.telefone || '-';
      document.getElementById('cli-plano').textContent = cliente.plano || '-';
      document.getElementById('cli-acoes').textContent = cliente.acoes || '-';
      document.getElementById('cli-data').textContent = cliente.criado_em ? new Date(cliente.criado_em).toLocaleDateString('pt-BR') : '-';
      const tabelaChamados = document.querySelector('#tabela-chamados-cliente tbody');
      const chamadosCliente = chamados.filter((chamado) => chamado.id_cliente === cliente.id_cliente);
      tabelaChamados.innerHTML = chamadosCliente.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td>#${detailEscape(chamado.id_chamado)}</td><td>${detailEscape(chamado.status)}</td></tr>`).join('') || '<tr><td colspan="3">Nenhum chamado encontrado para este cliente.</td></tr>';
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
    const valor = registro[campo.dataset.editField] || campo.textContent.trim();
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
      try {
        const atualizado = scope === 'cliente' ? await atualizarCliente(registro.id_cliente, dados) : await atualizarMembro(registro.id_grupo_solucionadores, dados);
        registro = atualizado;
        const span = document.createElement('span');
        span.className = 'info-value';
        span.id = input.id;
        span.dataset.editField = input.dataset.editField;
        span.textContent = input.dataset.editField === 'cnpj'
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
      const cliente = clientes.find((item) => item.id_cliente === chamado.id_cliente);
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
        document.querySelector('#statusChamado')?.classList.toggle('is-resolved', status === 'RESOLVIDO');
        renderizarHistoricoChamado(chamado.historico || []);
        const valoresSidebar = document.querySelectorAll('.ticket-sidebar .sidebar-info-list .info-value');
        if (valoresSidebar.length >= 2) {
          valoresSidebar[0].textContent = responsavel?.nome || 'Não atribuído';
          valoresSidebar[1].textContent = chamado.setor_nome || responsavel?.setor || 'Não informado';
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
        setorSelect.innerHTML = setores.map((setor) => `<option value="${detailEscape(setor.nome)}">${detailEscape(setor.nome)}</option>`).join('');
        setorSelect.value = chamado.setor || '';
        const atualizarTecnicosDestino = () => {
          const setor = normalizarTexto(setorSelect.value);
          const tecnicos = equipe.filter((membro) => normalizarTexto(membro.setor) === setor && (membro.status || 'ATIVO') === 'ATIVO');
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
            const dadosResolucao = new FormData(form);
            const descricaoFinal = String(dadosResolucao.get('descricao_final') || '').trim();
            const publicarArtigo = document.querySelector('#criarArtigoResolucao')?.checked || false;
            const tituloInformado = document.querySelector('#tituloArtigoResolucao')?.value.trim() || '';
            chamado = await atualizarChamado(id, { acao: 'encerrar', descricao_final: descricaoFinal });
            atualizarTelaChamado();
            modalEncerrar?.classList.remove('active');
            form.reset();
            const campoTituloArtigo = document.querySelector('#campoTituloArtigoResolucao');
            if (campoTituloArtigo) campoTituloArtigo.hidden = true;
            if (publicarArtigo) {
              try {
                const ticket = `#TK-${String(chamado.id_chamado || id).padStart(6, '0')}`;
                const grupoId = Number(localStorage.getItem('grupoId') || sessionStorage.getItem('grupoId')) || null;
                await criarDocumentacao({
                  titulo: tituloInformado || `Solução do chamado ${ticket}`,
                  fornecedor: chamado.setor ? `HelpTI - ${chamado.setor}` : 'HelpTI',
                  id_grupo_solucionadores: grupoId,
                  conteudo: `Chamado de referência: ${ticket}\nCliente: ${chamado.cliente || 'Não informado'}\n\nProblema relatado:\n${chamado.descricao || 'Não informado'}\n\nSolução aplicada:\n${descricaoFinal}`
                });
                mostrarNotificacao('Chamado resolvido e solução adicionada à base de conhecimento.');
              } catch (erroArtigo) {
                mostrarNotificacao('Chamado resolvido com sucesso.');
                mostrarErro(`O chamado foi encerrado, mas não foi possível criar o artigo: ${erroArtigo.message}`);
              }
            } else {
              mostrarNotificacao('Chamado resolvido com sucesso.');
            }
            if (!chamado.email_enviado && chamado.aviso_email) mostrarErro(chamado.aviso_email);
          } catch (error) {
            mostrarErro(`Não foi possível encerrar o chamado: ${error.message}`);
          }
        }, 'Encerrando...');
      });
      const opcaoArtigoResolucao = document.querySelector('#criarArtigoResolucao');
      const campoTituloArtigoResolucao = document.querySelector('#campoTituloArtigoResolucao');
      opcaoArtigoResolucao?.addEventListener('change', () => {
        if (campoTituloArtigoResolucao) campoTituloArtigoResolucao.hidden = !opcaoArtigoResolucao.checked;
        if (opcaoArtigoResolucao.checked) document.querySelector('#tituloArtigoResolucao')?.focus();
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
      let cliente = clientes.find((item) => item.id_cliente == id);
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
            const resultado = await criarContatoCliente(cliente.id_cliente, dados);
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
          cliente = await atualizarCliente(cliente.id_cliente, { status: novoStatus });
          atualizarStatusCliente();
          mostrarNotificacao(`Cliente ${novoStatus === 'ATIVO' ? 'ativado' : 'desativado'} com sucesso.`);
        } catch (error) { mostrarErro(`Não foi possível atualizar o status: ${error.message}`); }
      });
      const table = document.querySelector('#tabela-chamados-cliente tbody');
      const tickets = chamados.filter((chamado) => chamado.id_cliente === cliente.id_cliente);
      if (table) table.innerHTML = tickets.map((chamado) => `<tr onclick="window.location.href='chamados-detalhe.html?id=${encodeURIComponent(chamado.id_chamado)}'" style="cursor: pointer;"><td><strong>#${detailEscape(chamado.id_chamado)}</strong></td><td>${detailEscape(chamado.status)}</td><td>${detailEscape(detailDate(chamado.data_agendada))}</td><td>${detailEscape(chamado.classificacao)}</td></tr>`).join('') || '<tr><td colspan="4">Nenhum chamado encontrado para este cliente.</td></tr>';
    }

  } catch (error) {
    console.error('Não foi possível carregar os detalhes:', error);
    const title = document.querySelector('.page-title-bar h1');
    if (title) title.textContent = error.message || 'Não foi possível carregar os detalhes.';
  }
});
