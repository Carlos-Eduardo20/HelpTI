const API_URL = 'http://127.0.0.1:5000/api';

// ============ CHAMADOS ============

// Busca a lista de chamados do backend
export async function buscarChamados() {
  try {
    const response = await fetch(`${API_URL}/chamados`);
    if (!response.ok) throw new Error('Erro ao buscar chamados');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return [];
  }
}

// Busca um chamado específico pelo ID
export async function buscarChamadoPorId(id) {
  try {
    const response = await fetch(`${API_URL}/chamados/${id}`);
    if (!response.ok) throw new Error('Erro ao buscar chamado');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// Envia um novo chamado para o backend
export async function criarChamado(dadosChamado) {
  try {
    const response = await fetch(`${API_URL}/chamados`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dadosChamado)
    });
    if (!response.ok) throw new Error('Erro ao criar chamado');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// Atualiza um chamado existente
export async function atualizarChamado(id, dadosChamado) {
  try {
    const response = await fetch(`${API_URL}/chamados/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dadosChamado)
    });
    if (!response.ok) throw new Error('Erro ao atualizar chamado');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// ============ CLIENTES ============

// Busca a lista de clientes
export async function buscarClientes() {
  try {
    const response = await fetch(`${API_URL}/clientes`);
    if (!response.ok) throw new Error('Erro ao buscar clientes');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return [];
  }
}

// Cria um novo cliente
export async function criarCliente(dadosCliente) {
  try {
    const response = await fetch(`${API_URL}/clientes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dadosCliente)
    });
    if (!response.ok) throw new Error('Erro ao criar cliente');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// ============ EQUIPE ============

// Busca a lista de técnicos/equipe
export async function buscarEquipe() {
  try {
    const response = await fetch(`${API_URL}/equipe`);
    if (!response.ok) throw new Error('Erro ao buscar equipe');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return [];
  }
}

// ============ RELATÓRIOS ============

// Busca dados para relatórios
export async function buscarRelatorios() {
  try {
    const response = await fetch(`${API_URL}/relatorios`);
    if (!response.ok) throw new Error('Erro ao buscar relatórios');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// ============ CONFIGURAÇÕES ============

// Busca configurações do workspace
export async function buscarConfiguracoes() {
  try {
    const response = await fetch(`${API_URL}/configuracoes`);
    if (!response.ok) throw new Error('Erro ao buscar configurações');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}

// Atualiza configurações do workspace
export async function salvarConfiguracoes(dados) {
  try {
    const response = await fetch(`${API_URL}/configuracoes`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados)
    });
    if (!response.ok) throw new Error('Erro ao salvar configurações');
    return await response.json();
  } catch (error) {
    console.error('Erro na API:', error);
    return null;
  }
}