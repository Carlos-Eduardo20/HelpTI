# HelpTI

Sistema web de gestão operacional para suporte técnico, com foco em acompanhar chamados, clientes, equipe e indicadores do atendimento de TI.

## Visão geral

O HelpTI está em desenvolvimento como uma interface administrativa para empresas de suporte técnico. A estrutura atual do projeto está voltada para a apresentação visual e navegação do sistema, com páginas para login, dashboard, chamados, clientes, equipe e relatórios.
Atualmente, o projeto está em uma fase de protótipo/front-end, com foco em layout, experiência do usuário e organização das funcionalidades principais. O backend ainda está inicial e não está integrado de forma completa ao fluxo da aplicação.
O HelpTI está em desenvolvimento como uma aplicação administrativa para empresas de suporte técnico. O frontend em HTML, CSS e JavaScript se comunica com uma API Flask, que persiste os dados em MySQL.

---

## Estado atual do projeto

### Frontend
O frontend já conta com a estrutura principal do sistema em HTML, CSS e JavaScript.

- Tela de login com autenticação visual simulada
- Dashboard com indicadores de operação
- Agenda de chamados por dia e técnico
- Modal para abertura de novos chamados
- Dropdown de perfil com ações de configuração e logout
- Navegação entre páginas do painel

### Backend
O backend já possui rotas funcionais para os principais cadastros.

- [backend/app.py](backend/app.py): API Flask e rotas de chamados, clientes, equipe, relatórios e configurações
- [backend/schema.sql](backend/schema.sql): criação do banco e das tabelas MySQL
- [backend/database.py](backend/database.py): utilitários de conexão com o banco
- [backend/requirements.txt](backend/requirements.txt): dependências Python

Os registros de chamados, clientes e equipe são salvos no MySQL e permanecem após atualizar o navegador.

---

## Estrutura do projeto

```text
HelpTI/
├── README.md
├── backend/
│   ├── app.py
│   ├── database.py
│   └── schema.sql
├── frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   ├── dashboard.css
│   │   │   ├── login.css
│   │   │   ├── planos.css
│   │   │   └── variables.css
│   │   ├── images/
│   │   └── js/
│   │       ├── api.js
│   │       ├── dashboard.js
│   │       └── main.js
│   ├── pages/
│   │   ├── chamados.html
│   │   ├── clientes.html
│   │   ├── dashboard.html
│   │   ├── equipe.html
│   │   ├── login.html
│   │   └── relatorios.html
│   └── planos.html
└── .gitignore
```

---

## Páginas existentes

### Login
Página inicial de acesso ao sistema.

- [frontend/pages/login.html](frontend/pages/login.html)

### Dashboard
Painel principal com visão geral operacional e fila de atendimentos.

- [frontend/pages/dashboard.html](frontend/pages/dashboard.html)

### Chamados
Estrutura para gestão e acompanhamento de chamados.

- [frontend/pages/chamados.html](frontend/pages/chamados.html)

### Clientes
Área para cadastro e organização de clientes e contratos.

- [frontend/pages/clientes.html](frontend/pages/clientes.html)

### Equipe
Visualização da equipe técnica e estrutura departamental.

- [frontend/pages/equipe.html](frontend/pages/equipe.html)

### Relatórios
Módulo para indicadores e relatórios futuros.

- [frontend/pages/relatorios.html](frontend/pages/relatorios.html)

---

## Arquivos principais

### CSS
- [frontend/assets/css/dashboard.css](frontend/assets/css/dashboard.css): layout e estilos do dashboard
- [frontend/assets/css/login.css](frontend/assets/css/login.css): estilos da tela de login
- [frontend/assets/css/variables.css](frontend/assets/css/variables.css): paleta de cores e variáveis globais
- [frontend/assets/css/planos.css](frontend/assets/css/planos.css): estilos de planos e contratos

### JavaScript
- [frontend/assets/js/dashboard.js](frontend/assets/js/dashboard.js): agenda, criação e atualização de chamados
- [frontend/assets/js/api.js](frontend/assets/js/api.js): funções de comunicação com a API
- [frontend/assets/js/main.js](frontend/assets/js/main.js): modais, cadastros e telas de detalhe

---

## Como executar

O projeto roda com um único processo. O Flask serve as páginas do frontend, disponibiliza a API e abre o navegador automaticamente.

### Primeira configuração

1. Instale Python 3.8 ou superior e MySQL Server.
2. Clone ou copie o projeto para o computador.
3. Abra o projeto no VS Code e abra um terminal na raiz da pasta `HelpTI`.
4. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

5. Instale as dependências:

```powershell
python -m pip install -r backend\requirements.txt
```

6. Crie o banco e o arquivo `backend\.env` conforme [SETUP_MYSQL.md](SETUP_MYSQL.md).

### Iniciar o projeto

Com o MySQL em execução e o ambiente virtual ativado:

```powershell
cd backend
python app.py
```

O comando acima inicia a API e o frontend juntos. O navegador abrirá em `http://127.0.0.1:5000/`.

Endereços úteis:

- Aplicação: `http://127.0.0.1:5000/`
- Login direto: `http://127.0.0.1:5000/frontend/pages/login.html`
- Teste da API: `http://127.0.0.1:5000/api/health`

Não é necessário executar `python -m http.server` nem abrir a porta 8000.

### Encerrar

No terminal em que o Flask está rodando, pressione `Ctrl+C`.

---

## Status do desenvolvimento

O projeto possui uma base funcional de interface, API e persistência. Próximas etapas sugeridas:

- integração real com banco de dados
- autenticação de usuários
- persistência de chamados e clientes
- API para comunicação entre frontend e backend
- geração de relatórios e indicadores automáticos
- refinamento do fluxo administrativo completo

---

## Conclusão

O HelpTI hoje representa uma base sólida de interface e estrutura para um sistema de gestão de suporte técnico. O projeto já demonstra a organização visual do painel e os módulos principais, mas ainda está em fase inicial de implementação da parte lógica e de persistência.
- autenticação real e controle de permissões
- validação e edição de clientes e membros da equipe
- associação de chamados a clientes e técnicos por ID
- filtros, relatórios e indicadores mais completos
- testes automatizados da API e do frontend

## Como contribuir

Antes de alterar o código, leia [INTEGRACAO.md](INTEGRACAO.md) e [SETUP_MYSQL.md](SETUP_MYSQL.md). Faça mudanças pequenas, teste a API e o fluxo da tela correspondente e descreva no pull request o que foi alterado e como testar.

---

