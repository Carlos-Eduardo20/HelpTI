import { buscarRelatorios } from './api.js';

const nomesPeriodo = { todos: 'Todos os períodos', dia: 'Hoje', mes: 'Este mês' };
const coresClassificacao = ['var(--green-main)', 'var(--blue-600)', 'var(--navy-main)', 'var(--orange-main)', 'var(--pink-main)', 'var(--cyan-main)'];

function atualizarGraficoClassificacao(classificacoes = []) {
  const total = classificacoes.reduce((soma, item) => soma + Number(item.total || 0), 0);
  const anel = document.querySelector('#anel-classificacao');
  const legenda = document.querySelector('#legenda-classificacao');
  document.querySelector('#total-classificacao').textContent = total;
  legenda.replaceChildren();

  if (!total) {
    anel.style.background = 'conic-gradient(var(--border-color) 0% 100%)';
    const vazio = document.createElement('span');
    vazio.className = 'empty-legend';
    vazio.textContent = 'Sem chamados no período';
    legenda.append(vazio);
    return;
  }

  let acumulado = 0;
  const fatias = classificacoes.map((item, indice) => {
    const quantidade = Number(item.total || 0);
    const inicio = acumulado;
    acumulado += (quantidade / total) * 100;
    return `${coresClassificacao[indice % coresClassificacao.length]} ${inicio}% ${acumulado}%`;
  });
  anel.style.background = `conic-gradient(${fatias.join(', ')})`;

  classificacoes.forEach((item, indice) => {
    const quantidade = Number(item.total || 0);
    const linha = document.createElement('div');
    linha.className = 'legend-item';
    const ponto = document.createElement('span');
    ponto.className = 'dot';
    ponto.style.backgroundColor = coresClassificacao[indice % coresClassificacao.length];
    const nome = document.createElement('span');
    nome.className = 'legend-title';
    nome.textContent = item.classificacao || 'Sem classificação';
    const valor = document.createElement('strong');
    valor.className = 'legend-val';
    valor.append(`${Math.round((quantidade / total) * 100)}% `);
    const contagem = document.createElement('span');
    contagem.className = 'sub-count';
    contagem.textContent = `${quantidade} chamados`;
    valor.append(contagem);
    linha.append(ponto, nome, valor);
    legenda.append(linha);
  });
}

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
    atualizarGraficoClassificacao(dados.chamados_por_classificacao || []);
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