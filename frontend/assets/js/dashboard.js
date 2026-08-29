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

// Funções do Pop-up de Chamado
function abrirModalChamado() {
  document.getElementById('modalChamado').classList.add('active');
}

function fecharModalChamado() {
  document.getElementById('modalChamado').classList.remove('active');
}

function salvarChamado(event) {
  event.preventDefault();
  alert('Chamado criado com sucesso!');
  fecharModalChamado();
}

// Fecha o modal caso o usuário clique na parte escura (fora do formulário)
window.onclick = function(event) {
  const modal = document.getElementById('modalChamado');
  if (event.target === modal) {
    fecharModalChamado();
  }
};