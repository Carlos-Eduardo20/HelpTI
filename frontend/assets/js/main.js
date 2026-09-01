// Abrir e Fechar Modais
function openModal(modalId) {
  document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('active');
}

// Fechar ao clicar fora do card
window.onclick = function(event) {
  if (event.target.classList.contains('modal-overlay')) {
    event.target.classList.remove('active');
  }
};

// Funções de envio de formulário
function salvarCliente(e) {
  e.preventDefault();
  alert("Cliente salvo com sucesso!");
  closeModal('modal-cliente');
}

function salvarMembro(e) {
  e.preventDefault();
  alert("Novo técnico adicionado à equipe!");
  closeModal('modal-equipe');
}