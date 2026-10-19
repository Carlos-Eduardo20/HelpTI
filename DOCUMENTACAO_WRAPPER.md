# HelpTI — Wrapper Geral da Documentação do Projeto
## Arquitetura, Modelagem de Dados Relacional, Regras de Negócio DeskOps e Catálogo Técnico

---

## 1. Visão Geral do Sistema HelpTI

O **HelpTI** é uma plataforma moderna e completa de gerenciamento de chamados e suporte técnico (Service Desk / Helpdesk), desenvolvida para atender tanto equipes de TI internas quanto empresas prestadoras de serviços gerenciados (MSP / DeskOps).

O projeto foi projetado com uma arquitetura desacoplada e leve:
- **Frontend:** Interface rica, responsiva e dinâmica construída em HTML5, CSS3 moderno (com suporte a variáveis de design e temas Claro/Escuro) e JavaScript ES Modules nativo.
- **Backend:** Servidor em Python com microframework Flask, estruturado para expor uma API RESTful completa, segura e de alta performance.
- **Persistência de Dados:** Suporte nativo para banco de dados relacional **MySQL** com criação automática do esquema (`backend/schema.sql`).

---

## 2. Princípios do Projeto 3 & Operação DeskOps

O projeto foi aprimorado com base nos requisitos e diretrizes de excelência do **Projeto 3 (DeskOps)**:

### 2.1. Problema Real de Permissões e Segurança
- **Visão do Cliente:** O cliente que acessa o sistema visualiza **estritamente os seus próprios chamados** vinculados ao seu registro empresarial, garantindo isolamento total dos dados de outras organizações (multitenancy seguro).
- **Visão do Atendente/Técnico:** Técnicos e analistas de suporte acessam todos os chamados da empresa/workspace em que trabalham para prestar atendimento, escalar e solucionar problemas.

### 2.2. Regras Estritas de Atendimento e Encerramento
- **Autorização para Fechamento:** Clientes finais não têm permissão para encerrar ou alterar o status operacional de chamados. Apenas técnicos ou administradores autorizados do grupo de suporte podem alterar o status (ex: Iniciar, Pausar, Escalonar e Encerrar).
- **Conclusão com Solução Registrada:** Ao encerrar um ticket, o atendente deve registrar a descrição da solução técnica aplicada e o sistema calcula e congela o tempo total de atendimento.

### 2.3. Rastreabilidade Operacional com Autor no Histórico
- Toda e qualquer movimentação realizada no ciclo de vida de um chamado (criação, início de atendimento, agendamento, pausa, escalonamento, alteração de status e encerramento) gera uma entrada cronológica na tabela de histórico (`historico_chamado`).
- **Identificação do Autor:** Cada registro no histórico identifica com precisão o responsável pela ação através do atributo `autor` (ex: nome do técnico autenticado ou `Sistema`).

### 2.4. Métricas DeskOps em Tempo Real
A interface apresenta indicadores operacionais calculados dinamicamente via endpoint dedicado (`GET /api/chamados/metricas`):
1. **Total de Tickets:** Quantidade geral de chamados ativos e processados.
2. **Triagem:** Chamados com status `ABERTO` que aguardam primeiro atendimento e atribuição.
3. **Em Andamento:** Chamados que já foram iniciados por um técnico (`ANDAMENTO`).
4. **Resolvidos Hoje:** Quantidade de chamados concluídos com sucesso na data corrente.
5. **MTTR Médio (Mean Time to Resolution):** Indicador de tempo médio de resolução dos chamados encerrados, calculado a partir da média de segundos decorridos e formatado de maneira legível (ex.: `1h 45m` ou `28m 10s`).

### 2.5. Ferramentas Operacionais da Fila de Tickets
- **Abas Rápidas (Pills):** Navegação ágil entre `Todos`, `Triagem`, `Em Andamento`, `Pausados / Aguardando` e `Resolvidos` com contadores em tempo real.
- **Filtros Avançados:** Filtro por Responsável/Técnico, Prioridade (Crítica, Alta, Média, Baixa), Departamento/Setor e Período de Abertura.
- **Exportação CSV:** Exportação com um clique de todos os chamados visíveis com cabeçalho formatado em UTF-8 com suporte nativo ao Excel.
- **Atualização da Fila:** Botão para recarregamento instantâneo da fila sem necessidade de recarregar a página do navegador.

---

## 3. Modelagem de Dados Relacional e Decisão do Atributo `setor`

### 3.1. Diretriz de Negócio do Atributo `setor`
Conforme especificação explícita do projeto, **o setor não necessita de uma tabela independente no modelo relacional conceitual**. Em vez de forçar junções complexas com tabelas auxiliares para departamentos simples, o setor é tratado como um **atributo de texto desnormalizado**:
- `chamado.setor`: Nome do departamento ou setor demandado pelo chamado (ex: "Financeiro", "TI", "RH", "Infraestrutura").
- `grupo_solucionadores.setor`: Nome do setor/departamento onde o técnico atua.
- `escalonamento.setor_destino`: Nome do setor para o qual o chamado foi transferido.

*Nota técnica:* Para fins de compatibilidade retroativa com configurações de níveis hierárquicos e autocompletes visuais do frontend, a tabela `setor` é mantida no MySQL de forma auxiliar, sem restringir a integridade referencial dos chamados.

### 3.2. Dicionário das Tabelas do Sistema (Conforme ERD)

#### 1. `cliente`
Representa os clientes atendidos e seus contatos associados.
- `id_cliente` (INTEGER, PK): Identificador único do contato/cliente.
- `id_usuario` (INTEGER, FK -> `usuario.id_usuario`): Vínculo com a empresa/workspace.
- `nome` (TEXT, NOT NULL): Nome do cliente ou funcionário de contato.
- `email` (TEXT, NOT NULL): Endereço de e-mail do cliente.
- `telefone` (TEXT, NOT NULL): Telefone de contato.
- `contato` (TEXT): Nome da pessoa de contato principal.

#### 2. `tipo_chamado`
Classificação padrão de tipos de atendimento do helpdesk.
- `id_tipo_chamado` (INTEGER, PK): Identificador único do tipo.
- `nome` (TEXT, NOT NULL): Nome do tipo (ex: "Suporte Geral", "Hardware", "Software", "Redes").
- `classificacao` (TEXT): Subcategoria ou classificação técnica.
- `descricao` (TEXT): Descrição do escopo do tipo de chamado.

#### 3. `grupo_solucionadores`
Técnicos, analistas e membros das equipes de resolução de chamados.
- `id_grupo_solucionadores` (INTEGER, PK): Identificador do solucionador.
- `id_usuario` (INTEGER, FK -> `usuario.id_usuario`): Workspace ao qual o técnico pertence.
- `id_setor` (INTEGER, FK opcional): Referência opcional à tabela auxiliar de setores.
- `nome` (TEXT): Nome completo do atendente.
- `email` (TEXT): E-mail corporativo.
- `cargo` (TEXT): Função/cargo na equipe.
- `telefone` (TEXT): Telefone de contato.
- `setor` (TEXT): **Atributo de setor/departamento** do atendente.
- `nivel` (INTEGER): Nível de atendimento (N1, N2, N3).
- `status` (TEXT): 'ATIVO' ou 'INATIVO'.
- `permissoes` (TEXT): Permissões de acesso em formato JSON.

#### 4. `chamado`
Entidade central que armazena os tickets de atendimento.
- `id_chamado` (INTEGER, PK): Identificador numérico único do ticket (#TK-XXXX).
- `id_tipo_chamado` (INTEGER, FK -> `tipo_chamado.id_tipo_chamado`): Tipo do chamado.
- `id_grupo_solucionadores` (INTEGER, FK opcional): Técnico atribuído.
- `id_setor` (INTEGER, FK opcional): Setor de suporte.
- `cliente` (TEXT, NOT NULL): Razão social ou nome da empresa cliente.
- `email_cliente` (TEXT): E-mail da empresa solicitante.
- `telefone_cliente` (TEXT): Telefone da empresa solicitante.
- `contato_cliente` (TEXT): Nome do solicitante/funcionário específico.
- `telefone_contato` (TEXT): Telefone do solicitante.
- `setor` (TEXT): **Atributo de setor/departamento** do chamado.
- `status` (TEXT, DEFAULT 'ABERTO'): Status operacional (`ABERTO`, `ANDAMENTO`, `AGUARDANDO`, `PAUSADO`, `RESOLVIDO`).
- `descricao` (TEXT, NOT NULL): Relato do problema ou necessidade.
- `descricao_final` (TEXT): Solução técnica aplicada ao encerrar o chamado.
- `tempo_inicio` (TEXT): Timestamp do início do atendimento em andamento.
- `tempo_decorrido_segundos` (INTEGER, DEFAULT 0): Segundos totais consumidos de atendimento.
- `data_abertura` (TEXT, NOT NULL): Data e hora de abertura do chamado.
- `data_fechamento` (TEXT): Data e hora de encerramento do chamado.
- `data_agendada` (TEXT): Data programada para atendimento (quando aplicável).
- `hora_agendada` (TEXT): Horário agendado.
*(Nota: Conforme a modelagem conceitual do ERD original e requisitos de simplicidade do HelpTI, a gestão de tickets não impõe o atributo de prioridade, mantendo o fluxo ágil e desimpedido).*

#### 5. `escalonamento`
Registro de transferências de chamados para outros níveis ou técnicos.
- `id_escalonamento` (INTEGER, PK): Identificador do escalonamento.
- `id_chamado` (INTEGER, FK -> `chamado.id_chamado`): Chamado escalonado.
- `id_grupo_destino` (INTEGER, FK opcional): Novo técnico responsável.
- `id_setor_destino` (INTEGER, FK opcional): Identificador do setor de destino.
- `setor_destino` (TEXT): **Atributo do nome do setor de destino**.
- `motivo` (TEXT): Justificativa do escalonamento.
- `nivel` (INTEGER): Novo nível técnico (ex: Nível 2 ou 3).
- `data_escalonamento` (TEXT): Data e hora em que ocorreu a transferência.

#### 6. `historico_chamado`
Trilha de auditoria e linha do tempo de eventos do chamado.
- `id_historico` (INTEGER, PK): Identificador do evento.
- `id_chamado` (INTEGER, FK -> `chamado.id_chamado`): Chamado relacionado.
- `evento` (TEXT, NOT NULL): Código do evento (`aberto`, `iniciado`, `pausado`, `escalonado`, `encerrado`, `agendado`, `status_alterado`).
- `descricao` (TEXT, NOT NULL): Detalhamento do que aconteceu.
- `autor` (TEXT, DEFAULT 'Sistema'): **Identificador de quem realizou a alteração** (atendente ou sistema).
- `data_evento` (TEXT, NOT NULL): Data e hora do evento.

#### 7. `documentacao` (Modelagem ERD & Base de Conhecimento)
Repositório de documentação técnica, manuais de fornecedores e procedimentos.
- `id_documentacao` (INTEGER, PK): Identificador do documento.
- `id_usuario` (INTEGER, FK -> `usuario.id_usuario`): Empresa/workspace proprietário.
- `id_grupo_solucionadores` (INTEGER, FK opcional): Técnico autor ou grupo responsável.
- `fornecedor` (TEXT): Nome do fornecedor ou fabricante (ex: "Dell", "Microsoft", "Cisco").
- `titulo` (TEXT, NOT NULL): Título do manual ou artigo técnico.
- `conteudo` (TEXT, NOT NULL): Texto completo ou procedimentos de suporte.
- `data_criacao` (TEXT, NOT NULL): Data de inclusão.
- `data_atualizacao` (TEXT, NOT NULL): Data da última revisão.

---

## 4. Arquitetura da Solução e Tecnologias

### 4.1. Camada de Aplicação (Backend)
- **Linguagem:** Python 3.10+
- **Framework Web:** Flask com rotas modulares de API RESTful.
- **Autenticação:** Sessão baseada em cookies assinados e `login_required`. Suporte a expiração de sessão e hashes criptográficos fortes via Werkzeug (`generate_password_hash` / `check_password_hash`).
- **Migrações Automáticas:** O arquivo `backend/database.py` possui um motor interno de migração incremental (`SCHEMA_VERSION = 4`) que adiciona colunas e preserva tabelas existentes sem corromper ou apagar dados.

### 4.2. Camada de Apresentação (Frontend)
- **Estrutura:** HTML5 com navegação em abas superiores (Dashboard, Chamados, Clientes, Equipe, Relatórios, Educação).
- **Estilos:** CSS3 estruturado com variáveis customizadas para consistência cromática e modo escuro/claro com troca instantânea.
- **Lógica e Dinamismo:** JavaScript Vanilla com arquitetura de módulos ES (`api.js`, `dashboard.js`, `main.js`, `notifications.js`, etc.), garantindo carregamento rápido sem necessidade de bundlers pesados como Webpack ou Vite.
- **Acessibilidade e Feedback:** Toasts flutuantes com notificações de sucesso e erro, indicadores de carregamento assíncrono em botões (`comCarregamento`) e diálogo de confirmação seguro.

---

## 5. Catálogo Completo de Endpoints da API REST

### Chamados (`/api/chamados`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/chamados` | Lista todos os chamados da empresa/cliente autenticado. Suporta parâmetros de busca e ordenação. |
| `GET` | `/api/chamados/metricas` | Retorna as métricas DeskOps consolidadas (Total, Triagem, Andamento, Resolvidos Hoje e MTTR Médio). |
| `GET` | `/api/chamados/<id>` | Retorna os detalhes de um chamado específico com histórico cronológico completo. |
| `POST` | `/api/chamados` | Abre um novo chamado técnico com atributos de setor e prioridade. |
| `PUT` | `/api/chamados/<id>` | Atualiza dados, transiciona status ou encerra o chamado (somente atendente autorizado). |
| `DELETE` | `/api/chamados/<id>` | Exclui um chamado do sistema (permissão administrativa). |

### Documentações Técnicas (`/api/documentacoes`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/documentacoes` | Lista documentos técnicos com filtros opcionais por fornecedor e busca textual. |
| `GET` | `/api/documentacoes/<id>` | Obtém o conteúdo na íntegra de uma documentação técnica. |
| `POST` | `/api/documentacoes` | Cadastra novo artigo ou manual técnico vinculado ao grupo solucionador. |
| `PUT` | `/api/documentacoes/<id>` | Atualiza dados e conteúdo de uma documentação técnica existente. |
| `DELETE` | `/api/documentacoes/<id>` | Remove um documento técnico da base de conhecimento. |

### Clientes e Contatos (`/api/clientes`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/clientes` | Lista todas as empresas clientes cadastradas no workspace. |
| `POST` | `/api/clientes` | Cadastra uma nova empresa cliente com contatos associados. |
| `PUT` | `/api/clientes/<id>` | Atualiza informações da empresa cliente. |
| `DELETE` | `/api/clientes/<id>` | Remove uma empresa cliente. |
| `POST` | `/api/clientes/<id>/contatos` | Adiciona um funcionário/contato à empresa cliente. |

### Equipe e Técnicos (`/api/equipe`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/equipe` | Lista todos os técnicos e membros cadastrados no grupo solucionador. |
| `POST` | `/api/equipe` | Adiciona novo membro à equipe técnica. |
| `PUT` | `/api/equipe/<id>` | Atualiza informações, cargo, nível ou setor do técnico. |
| `DELETE` | `/api/equipe/<id>` | Remove um membro da equipe técnica. |

### Setores e Departamentos (`/api/setores`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/setores` | Lista os setores disponíveis com estrutura de níveis de atendimento. |
| `POST` | `/api/setores` | Cria um novo setor. |
| `DELETE` | `/api/setores/<id>` | Exclui um setor. |

### Relatórios e Métricas (`/api/relatorios`)
| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/relatorios?periodo=todos` | Retorna agregados analíticos de desempenho, volume e distribuição de tickets. |

---

## 6. Suíte de Testes Automatizados e Qualidade

O projeto conta com uma suíte de testes unitários e de integração desenvolvida em Python com o módulo padrão `unittest`:
- **Arquivo de testes DeskOps:** `backend/tests/test_deskops_project3.py`
- **Total de testes:** 34 testes automatizados cobrindo:
  1. Criação e persistência correta dos atributos `setor` e `prioridade`.
  2. Cálculo exato do MTTR Médio e formatação legível para horas e minutos.
  3. Bloqueio de clientes tentando alterar status ou encerrar chamados de suporte.
  4. Permissão para que clientes visualizem estritamente os seus próprios tickets.
  5. Rastreabilidade com gravação e persistência do `autor` no histórico do chamado.
  6. Operações de CRUD completas da tabela `documentacao`.
  7. Migração idempotente do esquema de banco sem perda de dados.

Para executar todos os testes da aplicação:
```bash
python -m unittest discover -s backend/tests
```
Resultado validado: **34 testes executados e 100% aprovados**.

---

## 7. Scripts SQL para Ambientes de Produção

### 7.1. MySQL (`backend/schema.sql`)
O arquivo `backend/schema.sql` contém a definição relacional (InnoDB, utf8mb4) com índices para aceleração de consultas por workspace, cliente, status e datas.

### 7.2. Oracle Database (`Banco de dados ORACLE/schema_oracle.sql`)
O arquivo `Banco de dados ORACLE/schema_oracle.sql` contém as instruções DDL corporativas prontas para deploy em Oracle Database:
- Tipos de dados específicos do Oracle (`NUMBER`, `VARCHAR2`, `TIMESTAMP`, `CLOB`).
- Sequências automáticas e `IDENTITY COLUMNS` para chaves primárias.
- Definição completa de `FOREIGN KEY` com integridade referencial.
- Tabela `DOCUMENTACAO` com campos para fornecedor, conteúdo em `CLOB` e índices de busca.
