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
  const nome = localStorage.getItem('perfilNome') || 'Usuário';
  document.querySelectorAll('.user-role').forEach((element) => element.textContent = nome);
  document.querySelectorAll('.user-avatar img').forEach((image) => {
    image.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=E5E7EB&color=374151`;
  });
}

async function carregarClientes() {
  const tabela = document.querySelector('#tabelaClientes');
  if (!tabela) return;
  try {
    const { buscarClientes } = await import('./api.js');
    const clientes = await buscarClientes();
    tabela.innerHTML = clientes.map((cliente) => `<tr><td><strong>${cliente.nome || '-'}</strong></td><td>${cliente.email || '-'}<br>${cliente.contato || ''}</td><td>-</td><td><span class="status-badge status-success">Ativo</span></td><td>-</td></tr>`).join('') || '<tr><td colspan="5">Nenhum cliente cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`; }
}

async function salvarCliente(event) {
  event.preventDefault();
  const form = event.target;
  const values = [...form.querySelectorAll('input')].map((input) => input.value.trim());
  try {
    const { criarCliente } = await import('./api.js');
    await criarCliente({ nome: values[0], telefone: values[1], contato: values[2], email: values[3] });
    closeModal('modal-cliente'); form.reset(); await carregarClientes(); alert('Cliente cadastrado com sucesso.');
  } catch (error) { alert(`Não foi possível cadastrar: ${error.message}`); }
}

async function carregarEquipe() {
  const tabela = document.querySelector('#tabelaEquipe');
  if (!tabela) return;
  try {
    const { buscarEquipe } = await import('./api.js');
    const equipe = await buscarEquipe();
    tabela.innerHTML = equipe.map((membro) => `<tr><td><strong>${membro.nome || membro.descricao || '-'}</strong></td><td>${membro.cargo || '-'}</td><td>0 chamados ativos</td><td><span class="status-badge status-info">${membro.status || 'ATIVO'}</span></td></tr>`).join('') || '<tr><td colspan="4">Nenhum membro cadastrado.</td></tr>';
  } catch (error) { tabela.innerHTML = `<tr><td colspan="4">${error.message}</td></tr>`; }
}

async function salvarMembro(event) {
  event.preventDefault();
  const form = event.target;
  const values = [...form.querySelectorAll('input, select')].map((input) => input.value.trim());
  try {
    const { criarMembro } = await import('./api.js');
    await criarMembro({ nome: values[0], email: values[1], cargo: values[2], valor_hora: values[3] });
    closeModal('modal-equipe'); form.reset(); await carregarEquipe(); alert('Membro cadastrado com sucesso.');
  } catch (error) { alert(`Não foi possível cadastrar: ${error.message}`); }
}

async function salvarConfiguracoes(event) {
  event.preventDefault();
  const dados = {
    workspaceName: document.getElementById('workspaceName')?.value.trim(),
    supportEmail: document.getElementById('supportEmail')?.value.trim()
  };
  try {
    const { salvarConfiguracoes: salvar } = await import('./api.js');
    await salvar(dados);
    localStorage.setItem('workspaceName', dados.workspaceName);
    localStorage.setItem('supportEmail', dados.supportEmail);
    alert('Configurações salvas com sucesso.');
  } catch (error) { alert(`Não foi possível salvar: ${error.message}`); }
}

function cancelarConfigurações() {
  window.location.href = 'dashboard.html';
}

async function carregarConfiguracoes() {
  const nome = document.getElementById('workspaceName');
  const email = document.getElementById('supportEmail');
  if (!nome || !email) return;
  try {
    const { buscarConfiguracoes } = await import('./api.js');
    const dados = await buscarConfiguracoes();
    nome.value = dados.workspaceName || '';
    email.value = dados.supportEmail || '';
  } catch (error) {
    alert(`Não foi possível carregar as configurações: ${error.message}`);
  }
}

document.addEventListener('click', () => document.getElementById('profileDropdown')?.classList.remove('active'));
document.addEventListener('DOMContentLoaded', () => { mostrarPerfil(); carregarClientes(); carregarEquipe(); carregarConfiguracoes(); });
