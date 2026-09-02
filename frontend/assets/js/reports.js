import { buscarRelatorios } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const dados = await buscarRelatorios();
    const total = Object.values(dados.chamados_por_status || {}).reduce((sum, item) => sum + Number(item.total || 0), 0);
    const resolvidos = Number(dados.total_resolvidos || 0);
    const cards = document.querySelectorAll('.stat-value');
    if (cards[0]) cards[0].textContent = `${total} chamados`;
    if (cards[2]) cards[2].textContent = `${total ? ((resolvidos / total) * 100).toFixed(1) : '0.0'}%`;
  } catch (error) {
    console.error('Não foi possível carregar os relatórios:', error);
  }
});