export function gerarUrlAvatar(nome) {
  const estilos = getComputedStyle(document.documentElement);
  const fundo = estilos.getPropertyValue('--avatar-background').trim().replace(/^#/, '');
  const texto = estilos.getPropertyValue('--avatar-text').trim().replace(/^#/, '');
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=${fundo}&color=${texto}`;
}
