import { buscarRelatorios } from './api.js';

const nomesPeriodo = { todos: 'Todos os períodos', dia: 'Hoje', mes: 'Este mês' };

async function carregarRelatorios(periodo = 'todos') {
  try {
    const dados = await buscarRelatorios(periodo);
    const total = Number(dados.total_chamados || 0);
    const resolvidos = Number(dados.total_resolvidos || 0);
    const pendentes = Number(dados.total_pendentes ?? total - resolvidos);
    const taxa = total ? ((resolvidos / total) * 100).toFixed(1) : '0.0';

    document.querySelector('#total-chamados').textContent = total;
    document.querySelector('#total-resolvidos').textContent = resolvidos;
    document.querySelector('#total-pendentes').textContent = pendentes;
    document.querySelector('#taxa-resolucao').textContent = `${taxa}%`;
    document.querySelector('#periodo-atual').textContent = nomesPeriodo[periodo];
    document.querySelectorAll('[data-status]').forEach((item) => {
      const quantidade = Number(dados.status?.[item.dataset.status] || 0);
      const percentual = total ? Math.round((quantidade / total) * 100) : 0;
      item.querySelector('.status-percent').textContent = `${percentual}%`;
      item.querySelector('.count-text').textContent = `${quantidade} chamados`;
      item.querySelector('.progress-bar-fill').style.width = `${percentual}%`;
    });
  } catch (error) {
    console.error('Não foi possível carregar os relatórios:', error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-periodo]').forEach((botao) => {
    botao.addEventListener('click', () => {
      document.querySelectorAll('[data-periodo]').forEach((item) => item.classList.remove('active'));
      botao.classList.add('active');
      carregarRelatorios(botao.dataset.periodo);
    });
  });
  carregarRelatorios();
});