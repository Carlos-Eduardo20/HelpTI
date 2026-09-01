// Abre e fecha o dropdown do perfil no canto superior direito
function toggleProfileMenu(event) {
  event.stopPropagation();
  const dropdown = document.getElementById('profileDropdown');
  if (dropdown) {
    dropdown.classList.toggle('active');
  }
}

// Fecha o dropdown se o usuário clicar fora dele na tela
document.addEventListener('click', function () {
  const dropdown = document.getElementById('profileDropdown');
  if (dropdown && dropdown.classList.contains('active')) {
    dropdown.classList.remove('active');
  }
});

// ============ FUNÇÕES DE CHAMADOS ============

// Abre o modal de novo chamado
function abrirModalChamado() {
  document.getElementById('modalChamado').classList.add('active');
}

// Fecha o modal de chamado
function fecharModalChamado() {
  document.getElementById('modalChamado').classList.remove('active');
}

// Salva um novo chamado
async function salvarChamado(event) {
  event.preventDefault();
  
  const cliente = document.querySelector('input[placeholder="Nome do cliente"]').value;
  const assunto = document.querySelector('input[placeholder="Ex: Impressora não conecta"]').value;
  const prioridade = document.querySelector('select').value;
  const descricao = document.querySelector('textarea').value;

  if (!cliente || !assunto) {
    alert('Por favor, preencha todos os campos obrigatórios');
    return;
  }

  try {
    const { criarChamado } = await import('./api.js');
    const resultado = await criarChamado({
      cliente,
      assunto,
      prioridade,
      descricao
    });

    if (resultado) {
      alert('Chamado criado com sucesso!');
      fecharModalChamado();
      atualizarDashboard(); // Recarregar dados
    } else {
      alert('Erro ao criar chamado');
    }
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro ao criar chamado');
  }
}

// Fecha o modal se clicar fora dele
window.onclick = function(event) {
  const modal = document.getElementById('modalChamado');
  if (event.target === modal) {
    fecharModalChamado();
  }
};

// ============ FUNÇÕES DE CONFIGURAÇÕES ============

// Função para cancelar
function cancelarConfigurações() {
  window.location.href = 'dashboard.html';
}

// Função para salvar configurações
async function salvarConfiguracoes(event) {
  event.preventDefault();

  const novoNome = document.getElementById('workspaceName')?.value;
  const novoEmail = document.getElementById('supportEmail')?.value;

  if (!novoNome || !novoEmail) {
    alert('Por favor, preencha todos os campos');
    return;
  }

  try {
    const { salvarConfiguracoes: salvarConfiguracoesAPI } = await import('./api.js');
    const resultado = await salvarConfiguracoesAPI({
      workspaceName: novoNome,
      supportEmail: novoEmail
    });

    if (resultado) {
      alert('Configurações salvas com sucesso!');
      localStorage.setItem('workspaceName', novoNome);
      localStorage.setItem('supportEmail', novoEmail);
    } else {
      alert('Erro ao salvar configurações');
    }
  } catch (error) {
    // Se a API não estiver disponível, salva localmente
    localStorage.setItem('workspaceName', novoNome);
    localStorage.setItem('supportEmail', novoEmail);
    alert('Configurações salvas localmente');
  }

  window.location.href = 'dashboard.html';
}

// ============ ATUALIZAÇÃO DO DASHBOARD ============

// Importar função de API
import { buscarChamados } from './api.js';

// Função para atualizar dados do dashboard
async function atualizarDashboard() {
  try {
    const chamados = await buscarChamados();
    
    if (!chamados || chamados.length === 0) {
      console.log('Nenhum chamado encontrado');
      return;
    }

    // Contar chamados por status
    const totalAbertos = chamados.filter(c => c.status === 'ABERTO').length;
    const totalAndamento = chamados.filter(c => c.status === 'ANDAMENTO').length;
    const totalAguardando = chamados.filter(c => c.status === 'AGUARDANDO').length;
    const totalResolvidos = chamados.filter(c => c.status === 'RESOLVIDO').length;

    // Atualizar os cards na tela
    const statCards = document.querySelectorAll('.stat-value');
    if (statCards[0]) statCards[0].textContent = totalAbertos;
    if (statCards[1]) statCards[1].textContent = totalAndamento;
    if (statCards[2]) statCards[2].textContent = totalAguardando;
    if (statCards[3]) statCards[3].textContent = totalResolvidos;

    console.log('Dashboard atualizado com sucesso');
  } catch (error) {
    console.error('Erro ao atualizar dashboard:', error);
  }
}

// Carrega os dados assim que a página abre
document.addEventListener('DOMContentLoaded', atualizarDashboard);