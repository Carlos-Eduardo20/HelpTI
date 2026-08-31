# HelpTI

Sistema web de gestão operacional para suporte técnico, com foco em acompanhar chamados, clientes, equipe e indicadores do atendimento de TI.

## Visão geral

O HelpTI está em desenvolvimento como uma interface administrativa para empresas de suporte técnico. A estrutura atual do projeto está voltada para a apresentação visual e navegação do sistema, com páginas para login, dashboard, chamados, clientes, equipe e relatórios.

Atualmente, o projeto está em uma fase de protótipo/front-end, com foco em layout, experiência do usuário e organização das funcionalidades principais. O backend ainda está inicial e não está integrado de forma completa ao fluxo da aplicação.

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
A parte de backend está em estágio inicial.

- [backend/schema.sql](backend/schema.sql): estrutura inicial do banco de dados
- [backend/app.py](backend/app.py): arquivo reservado para a aplicação backend
- [backend/database.py](backend/database.py): arquivo reservado para conexão e regras de persistência

Nesse momento, os arquivos Python ainda não possuem implementação funcional e o sistema depende principalmente do front-end estático.

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
- [frontend/assets/js/dashboard.js](frontend/assets/js/dashboard.js): interações do dashboard, dropdown e modal de chamados
- [frontend/assets/js/api.js](frontend/assets/js/api.js): estrutura para integrações com API
- [frontend/assets/js/main.js](frontend/assets/js/main.js): arquivo reservado para lógica principal do frontend

---

## Como utilizar no momento

Como o projeto ainda é um protótipo front-end, a forma mais simples de visualizar é abrir a página inicial do sistema diretamente no navegador:

- [frontend/pages/login.html](frontend/pages/login.html)

Ou, se preferir, executar um servidor local:

```bash
cd HelpTI
python -m http.server 8000
```

Depois acesse:

```text
http://localhost:8000/frontend/pages/login.html
```

> O login atual é apenas simulado e redireciona para o dashboard, sem autenticação real.

---

## Status do desenvolvimento

O projeto já possui uma base funcional de interface e navegação, mas ainda está em evolução. As próximas etapas esperadas incluem:

- integração real com banco de dados
- autenticação de usuários
- persistência de chamados e clientes
- API para comunicação entre frontend e backend
- geração de relatórios e indicadores automáticos
- refinamento do fluxo administrativo completo

---

## Conclusão

O HelpTI hoje representa uma base sólida de interface e estrutura para um sistema de gestão de suporte técnico. O projeto já demonstra a organização visual do painel e os módulos principais, mas ainda está em fase inicial de implementação da parte lógica e de persistência.

Se quiser, posso também atualizar o README para um formato mais profissional com:

- badges
- roadmap de desenvolvimento
- instruções de instalação detalhadas
- stack tecnológica
- seção de funcionalidades por módulo
