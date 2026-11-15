export const API_URL = `${window.location.origin}/api`;

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...options });
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

// Busca as métricas DeskOps para cards superiores (Total, Triagem, Andamento, Resolvidos Hoje, MTTR)
export async function buscarMetricasDeskops() {
  return request('/chamados/metricas');
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

export async function excluirChamado(id) {
  return request(`/chamados/${id}`, { method: 'DELETE' });
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

export async function criarContatoCliente(id, dadosContato) {
  return request(`/clientes/${id}/contatos`, { method: 'POST', body: JSON.stringify(dadosContato) });
}

export async function atualizarCliente(id, dadosCliente) {
  return request(`/clientes/${id}`, { method: 'PUT', body: JSON.stringify(dadosCliente) });
}

export async function excluirCliente(id) {
  return request(`/clientes/${id}`, { method: 'DELETE' });
}

export async function buscarEquipamentosCliente(id) {
  return request(`/clientes/${id}/equipamentos`);
}

export async function criarEquipamentoCliente(id, dados) {
  return request(`/clientes/${id}/equipamentos`, { method: 'POST', body: JSON.stringify(dados) });
}

export async function atualizarEquipamentoCliente(id, equipamentoId, dados) {
  return request(`/clientes/${id}/equipamentos/${equipamentoId}`, {
    method: 'PUT',
    body: JSON.stringify(dados),
  });
}

export async function excluirEquipamentoCliente(id, equipamentoId) {
  return request(`/clientes/${id}/equipamentos/${equipamentoId}`, { method: 'DELETE' });
}

// ============ EQUIPE ============

// Busca a lista de técnicos/equipe
export async function buscarEquipe() {
  return request('/equipe');
}

export async function criarMembro(dados) {
  return request('/equipe', { method: 'POST', body: JSON.stringify(dados) });
}

export async function atualizarMembro(id, dados) {
  return request(`/equipe/${id}`, { method: 'PUT', body: JSON.stringify(dados) });
}

export async function excluirMembro(id) {
  return request(`/equipe/${id}`, { method: 'DELETE' });
}

export async function buscarMembros() {
  return request('/membros');
}

export async function buscarSetores() {
  return request('/setores');
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

// ============ DOCUMENTAÇÃO TÉCNICA (MODELAGEM ERD) ============

export async function buscarDocumentacoes(busca = '', fornecedor = '', grupoId = '') {
  const params = new URLSearchParams();
  if (busca) params.append('busca', busca);
  if (fornecedor) params.append('fornecedor', fornecedor);
  if (grupoId) params.append('id_grupo_solucionadores', grupoId);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/documentacoes${qs}`);
}

export async function buscarDocumentacaoPorId(id) {
  return request(`/documentacoes/${id}`);
}

export async function criarDocumentacao(dados) {
  return request('/documentacoes', { method: 'POST', body: JSON.stringify(dados) });
}

export async function atualizarDocumentacao(id, dados) {
  return request(`/documentacoes/${id}`, { method: 'PUT', body: JSON.stringify(dados) });
}

export async function excluirDocumentacao(id) {
  return request(`/documentacoes/${id}`, { method: 'DELETE' });
}