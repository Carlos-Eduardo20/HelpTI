# HelpTI

Sistema web para gerenciamento de suporte técnico e atendimento de TI, voltado para empresas que precisam organizar chamados, clientes, equipe interna e relatórios de SLA.

## Visão geral

O HelpTI foi pensado como uma plataforma de gestão operacional para uma empresa de prestação de serviços de tecnologia. A solução centraliza o acompanhamento de incidentes, a organização de clientes e contratos, a gestão da equipe técnica e a visualização de indicadores de desempenho.

O projeto é composto por:

- Frontend estático em HTML, CSS e JavaScript
- Estrutura de páginas para navegação do sistema
- Backend inicial em Python para futuras integrações e persistência de dados
- Banco de dados em SQL para modelagem da base de suporte

---

## Funcionalidades principais

- Cadastro e acompanhamento de chamados de suporte
- Dashboard com indicadores de operação
- Gestão de clientes e contratos
- Organização da equipe técnica
- Relatórios de SLA e consumo de horas
- Interface de login para acesso ao sistema

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
│   ├── index.html
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
│   └── pages/
│       ├── chamados.html
│       ├── clientes.html
│       ├── dashboard.html
│       ├── equipe.html
│       └── relatorios.html
└── .gitignore (se existir no projeto)
```

### Descrição de cada pasta

#### backend/
Diretório responsável pela parte lógica do sistema e persistência.

- [backend/app.py](backend/app.py): arquivo principal da aplicação backend.
- [backend/database.py](backend/database.py): responsável pela conexão e operações com banco de dados.
- [backend/schema.sql](backend/schema.sql): script SQL com a criação da estrutura do banco de dados.

#### frontend/
Contém todas as telas e recursos visuais da aplicação.

- [frontend/index.html](frontend/index.html): página de login inicial do sistema.
- [frontend/assets/css](frontend/assets/css): arquivos de estilo do projeto, incluindo layout do dashboard e login.
- [frontend/assets/js](frontend/assets/js): scripts JavaScript de interação da interface.
- [frontend/assets/images](frontend/assets/images): imagens e ícones do sistema.
- [frontend/pages](frontend/pages): páginas internas do painel administrativo.

---

## Páginas do projeto

### 1. Login
Acesso inicial ao sistema.

- [frontend/index.html](frontend/index.html)

### 2. Dashboard
Painel principal com visão geral da operação, indicadores e fila de atendimento.

- [frontend/pages/dashboard.html](frontend/pages/dashboard.html)

### 3. Chamados
Área para acompanhar, categorizar e gerenciar solicitações de suporte.

- [frontend/pages/chamados.html](frontend/pages/chamados.html)

### 4. Clientes
Módulo para cadastro e gestão de clientes e contratos.

- [frontend/pages/clientes.html](frontend/pages/clientes.html)

### 5. Equipe
Visualização e controle dos técnicos e integrantes da operação.

- [frontend/pages/equipe.html](frontend/pages/equipe.html)

### 6. Relatórios
Área para acompanhar métricas, SLA e consumo de horas.

- [frontend/pages/relatorios.html](frontend/pages/relatorios.html)

---

## Detalhes de arquivos importantes

### CSS
Os estilos estão divididos por módulos para facilitar manutenção:

- [frontend/assets/css/dashboard.css](frontend/assets/css/dashboard.css): visual do painel administrativo
- [frontend/assets/css/login.css](frontend/assets/css/login.css): visual da tela de login
- [frontend/assets/css/planos.css](frontend/assets/css/planos.css): estilos específicos para planos/contratos
- [frontend/assets/css/variables.css](frontend/assets/css/variables.css): variáveis globais de cores, espaçamentos e fontes

### JavaScript
- [frontend/assets/js/api.js](frontend/assets/js/api.js): funções para comunicação com API/backend
- [frontend/assets/js/dashboard.js](frontend/assets/js/dashboard.js): interações do painel e ações do dashboard
- [frontend/assets/js/main.js](frontend/assets/js/main.js): lógica principal do frontend

---

## Como executar o projeto

### Opção 1: abrir diretamente no navegador
Como o frontend é estático, basta abrir o arquivo abaixo em um navegador:

- [frontend/index.html](frontend/index.html)

### Opção 2: rodar localmente com servidor HTTP
Se preferir, você pode iniciar um servidor local na raiz do projeto:

```bash
cd HelpTI
python -m http.server 8000
```

Depois acesse:

```text
http://localhost:8000/frontend/index.html
```

> O backend ainda está em desenvolvimento, então a parte de autenticação e persistência de dados pode ser expandida conforme a aplicação evolui.

---

## Status do projeto

Este projeto está em fase inicial de desenvolvimento e já conta com a estrutura principal de navegação e layout do sistema. A próxima etapa pode incluir:

- integração com banco de dados real
- autenticação de usuários
- cadastro e edição de chamados
- consumo de API para dados dinâmicos
- geração de relatórios em PDF
- deploy em ambiente web

---

## Conclusão

O HelpTI é uma base sólida para um sistema de gestão de suporte técnico, com foco em organização operacional, controle de SLA e acompanhamento da equipe. A estrutura do projeto está organizada para facilitar expansão e manutenção conforme novas funcionalidades forem adicionadas.

Se quiser, também posso criar uma versão melhorada do README com:

- badges do projeto
- instruções de instalação mais detalhadas
- roadmap de desenvolvimento
- tabela de tecnologias utilizadas
- seção de screenshots e fluxo de uso
