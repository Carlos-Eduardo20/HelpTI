export const API_URL = 'http://127.0.0.1:5000/api';

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  } catch (error) {
    throw new Error('Não foi possível conectar à API. Inicie o backend com "python app.py" na pasta backend e tente novamente.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.erro || `Erro HTTP ${response.status}`);
  return data;
}

// ============ CHAMADOS ============

// Busca a lista de chamados do backend
export async function buscarChamados() {
  return request('/chamados');
}

// Busca um chamado específico pelo ID
export async function buscarChamadoPorId(id) {
  return request(`/chamados/${id}`);
}

// Envia um novo chamado para o backend
export async function criarChamado(dadosChamado) {
  return request('/chamados', { method: 'POST', body: JSON.stringify(dadosChamado) });
}

// Atualiza um chamado existente
export async function atualizarChamado(id, dadosChamado) {
  return request(`/chamados/${id}`, { method: 'PUT', body: JSON.stringify(dadosChamado) });
}

// ============ CLIENTES ============

// Busca a lista de clientes
export async function buscarClientes() {
  return request('/clientes');
}

// Cria um novo cliente
export async function criarCliente(dadosCliente) {
  return request('/clientes', { method: 'POST', body: JSON.stringify(dadosCliente) });
}

// ============ EQUIPE ============

// Busca a lista de técnicos/equipe
export async function buscarEquipe() {
  return request('/equipe');
}

export async function criarMembro(dados) {
  return request('/equipe', { method: 'POST', body: JSON.stringify(dados) });
}

export async function buscarSetores() {
  return request('/setores');
}

export async function criarSetor(dados) {
  return request('/setores', { method: 'POST', body: JSON.stringify(dados) });
}

// ============ RELATÓRIOS ============

// Busca dados para relatórios
export async function buscarRelatorios(periodo = 'todos') {
  return request(`/relatorios?periodo=${encodeURIComponent(periodo)}`);
}

// ============ CONFIGURAÇÕES ============

// Busca configurações do workspace
export async function buscarConfiguracoes() {
  return request('/configuracoes');
}

// Atualiza configurações do workspace
export async function salvarConfiguracoes(dados) {
  return request('/configuracoes', { method: 'PUT', body: JSON.stringify(dados) });
}