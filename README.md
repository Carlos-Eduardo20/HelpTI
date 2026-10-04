# HelpTI

Sistema web de gestão operacional para suporte técnico, com foco em acompanhar chamados, clientes, equipe e indicadores do atendimento de TI.

## Visão geral

O HelpTI é uma aplicação web para gestão de suporte técnico. O frontend usa HTML, CSS e JavaScript; o backend usa Flask e expõe uma API REST. Os dados são persistidos em SQLite, criado automaticamente na primeira inicialização.

O projeto reúne telas de login, dashboard, chamados, clientes, equipe, setores, relatórios, configurações, educação e planos. O Flask serve as páginas e a API no mesmo endereço.

A visualização interativa de componentes 3D da página Educação é desenhada em Python pelo Flask. Para iniciar o sistema e acessar a visualização, execute `python app.py` na raiz do projeto; não é necessário iniciar um aplicativo Tkinter separado.

---

## Estado atual do projeto

### Backend

- [backend/app.py](backend/app.py): aplicação Flask, páginas e endpoints da API
- [backend/database.py](backend/database.py): conexão SQLite e inicialização automática
- [backend/schema.sql](backend/schema.sql): tabelas, relacionamentos, índices e dados iniciais
- [backend/requirements.txt](backend/requirements.txt): dependências Python da aplicação

Chamados, clientes, contatos, equipe, setores e configurações permanecem salvos no banco local após reiniciar o servidor.

## Banco de dados

O banco padrão é SQLite. Na primeira inicialização, o sistema cria `instance/helpti.sqlite3` e aplica `backend/schema.sql`. Não é necessário instalar MySQL, usar Workbench ou configurar credenciais de banco no `.env`. Cada clone mantém seu próprio arquivo de dados, que não deve ser enviado ao Git.

### Tabelas e atributos

Os tipos abaixo são os tipos lógicos do SQLite: `INTEGER`, `TEXT` e `NUMERIC`.

| Tabela | Atributos |
| --- | --- |
| `usuario` | `id_usuario INTEGER` (PK); `nome`, `contato`, `email`, `telefone`, `telefone_empresa`, `endereco`, `cnpj`, `plano`, `acoes`, `senha_hash TEXT`; `status TEXT NOT NULL DEFAULT 'ATIVO'`; `tipo_usuario TEXT NOT NULL DEFAULT 'CLIENTE'`. Um registro `WORKSPACE` representa a empresa/conta administradora; `CLIENTE` representa uma empresa atendida. |
| `cliente` | `id_cliente INTEGER` (PK); `id_usuario INTEGER NOT NULL` (FK); `nome`, `email`, `telefone TEXT NOT NULL`. Contatos associados a uma empresa. |
| `tipo_chamado` | `id_tipo_chamado INTEGER` (PK); `nome TEXT NOT NULL`; `classificacao`, `descricao TEXT`. Os tipos iniciais são Suporte Geral, Hardware, Software e Rede. |
| `setor` | `id_setor INTEGER` (PK); `nome TEXT NOT NULL UNIQUE`; `descricao TEXT`; `niveis TEXT` (JSON). |
| `grupo_solucionadores` | `id_grupo_solucionadores INTEGER` (PK); `id_usuario INTEGER NOT NULL` (FK do workspace); `descricao`, `nome`, `email`, `cargo`, `telefone TEXT`; `nivel INTEGER`; `data_inicio`, `data_fim TEXT`; `valor_hora NUMERIC`; `status TEXT NOT NULL DEFAULT 'ATIVO'`; `senha TEXT NOT NULL DEFAULT ''`; `permissoes TEXT NOT NULL DEFAULT '[]'` (JSON); `id_setor INTEGER` (FK opcional). Apesar do nome legado, representa administradores e funcionários da equipe. |
| `chamado` | `id_chamado INTEGER` (PK); `id_tipo_chamado INTEGER NOT NULL` (FK); `id_setor`, `id_grupo_solucionadores INTEGER` (FKs opcionais); `status TEXT NOT NULL DEFAULT 'ABERTO'`; `cliente TEXT NOT NULL`; `assunto`, `descricao`, `email_cliente`, `telefone_cliente`, `contato_cliente`, `telefone_contato`, `descricao_final`, `documentacao`, `tempo_inicio`, `data_agendada`, `hora_agendada`, `classificacao TEXT`; `tempo_decorrido_segundos INTEGER NOT NULL DEFAULT 0`; `data_abertura TEXT NOT NULL` (data/hora local). |
| `escalonamento` | `id_escalonamento INTEGER` (PK); `id_chamado INTEGER NOT NULL` (FK); `motivo TEXT`; `nivel INTEGER`; `id_setor_destino`, `id_grupo_destino INTEGER` (FKs opcionais); `data_escalonamento TEXT`. |
| `historico_chamado` | `id_historico INTEGER` (PK); `id_chamado INTEGER NOT NULL` (FK); `evento`, `descricao`, `data_evento TEXT NOT NULL`. Mantém a timeline de abertura, início, pausa, escalonamento, encerramento e alterações. |
| `configuracao` | `id_configuracao INTEGER` (PK); `workspace_name`, `support_email TEXT NOT NULL`. Guarda as configurações gerais do workspace. |

### Diagrama entidade-relacionamento

```mermaid
erDiagram
	USUARIO ||--o{ CLIENTE : possui_contatos
	USUARIO ||--o{ GRUPO_SOLUCIONADORES : administra_equipe
	TIPO_CHAMADO ||--o{ CHAMADO : classifica
	SETOR o|--o{ GRUPO_SOLUCIONADORES : organiza
	SETOR o|--o{ CHAMADO : recebe
	GRUPO_SOLUCIONADORES o|--o{ CHAMADO : atende
	CHAMADO ||--o{ ESCALONAMENTO : registra
	SETOR o|--o{ ESCALONAMENTO : destino
	GRUPO_SOLUCIONADORES o|--o{ ESCALONAMENTO : responsavel_destino
	CHAMADO ||--o{ HISTORICO_CHAMADO : possui_eventos

	USUARIO {
		INTEGER id_usuario PK
		TEXT nome
		TEXT contato
		TEXT email
		TEXT telefone
		TEXT telefone_empresa
		TEXT endereco
		TEXT status
		TEXT tipo_usuario
		TEXT cnpj
		TEXT plano
		TEXT acoes
		TEXT senha_hash
	}
	CLIENTE {
		INTEGER id_cliente PK
		INTEGER id_usuario FK
		TEXT nome
		TEXT email
		TEXT telefone
	}
	TIPO_CHAMADO {
		INTEGER id_tipo_chamado PK
		TEXT nome
		TEXT classificacao
		TEXT descricao
	}
	SETOR {
		INTEGER id_setor PK
		TEXT nome UK
		TEXT descricao
		TEXT niveis
	}
	GRUPO_SOLUCIONADORES {
		INTEGER id_grupo_solucionadores PK
		INTEGER id_usuario FK
		TEXT descricao
		INTEGER nivel
		TEXT data_inicio
		TEXT data_fim
		TEXT nome
		TEXT email
		TEXT cargo
		NUMERIC valor_hora
		TEXT telefone
		TEXT status
		TEXT senha
		TEXT permissoes
		INTEGER id_setor FK
	}
	CHAMADO {
		INTEGER id_chamado PK
		INTEGER id_tipo_chamado FK
		INTEGER id_setor FK
		INTEGER id_grupo_solucionadores FK
		TEXT status
		TEXT cliente
		TEXT assunto
		TEXT descricao
		TEXT email_cliente
		TEXT telefone_cliente
		TEXT contato_cliente
		TEXT telefone_contato
		TEXT descricao_final
		TEXT documentacao
		INTEGER tempo_decorrido_segundos
		TEXT tempo_inicio
		TEXT data_abertura
		TEXT data_agendada
		TEXT hora_agendada
		TEXT classificacao
	}
	ESCALONAMENTO {
		INTEGER id_escalonamento PK
		INTEGER id_chamado FK
		TEXT motivo
		INTEGER nivel
		INTEGER id_setor_destino FK
		INTEGER id_grupo_destino FK
		TEXT data_escalonamento
	}
	HISTORICO_CHAMADO {
		INTEGER id_historico PK
		INTEGER id_chamado FK
		TEXT evento
		TEXT descricao
		TEXT data_evento
	}
	CONFIGURACAO {
		INTEGER id_configuracao PK
		TEXT workspace_name
		TEXT support_email
	}
```

### Adaptação da modelagem de referência

O diagrama entidade-relacionamento acima representa o banco atualmente implementado no site. Para o modelo conceitual do case solicitado, `setor` deve ser um atributo de `grupo_solucionadores` (por exemplo, `setor TEXT`), sem uma tabela `setor` separada. O banco do site ainda mantém a tabela `setor` porque a aplicação permite cadastrar setores e associá-los também a chamados; essa diferença fica registrada para não confundir a proposta do case com o schema em execução.

O fluxo de atendimento da referência foi adaptado aos conceitos existentes no HelpTI:

| Conceito da referência | Implementação no HelpTI |
| --- | --- |
| Cliente que relata o problema | `usuario` representa a empresa/workspace e `cliente` seus contatos cadastrados. O chamado mantém nome, e-mail e telefone do solicitante em seus próprios campos, sem FK para essas tabelas. |
| Grupo solucionador | `grupo_solucionadores`, vinculado ao workspace por `id_usuario` e opcionalmente a um `setor`. |
| Chamado | `chamado`, associado a `tipo_chamado` e, opcionalmente, a um setor e membro responsável. |
| Transferência/escalonamento | `escalonamento`, com motivo, nível e destinos opcionais de setor e membro da equipe. |
| Registro de horas | Não há tabela de apontamentos. O tempo corrido do atendimento fica em `chamado.tempo_decorrido_segundos`; `grupo_solucionadores.valor_hora` é um atributo cadastral e não gera cálculo de pagamento. |
| Fechamento/pagamento | Não há entidade financeira no schema atual. O encerramento do chamado é registrado em `chamado` e na timeline `historico_chamado`; pagamentos não fazem parte do escopo implementado. |

### Relacionamentos

- `usuario` 1:N `cliente`; excluir uma empresa exclui seus contatos.
- Um registro `usuario.tipo_usuario = 'WORKSPACE'` é o administrador/empresa responsável; `grupo_solucionadores.id_usuario` liga o administrador e seus funcionários a esse workspace.
- `tipo_chamado` 1:N `chamado`.
- `setor` 1:N `grupo_solucionadores` e `chamado`; ao excluir um setor, a referência é removida dos registros relacionados.
- `grupo_solucionadores` 1:N `chamado`; o vínculo fica nulo quando o membro é removido.
- `chamado` 1:N `escalonamento`; excluir o chamado exclui seu histórico de escalonamentos.
- `chamado` 1:N `historico_chamado`; excluir o chamado exclui seus eventos da timeline.
- `setor` e `grupo_solucionadores` também podem ser o destino de vários escalonamentos.
- `chamado` guarda os dados de cliente como texto e **não possui FK para `usuario`**; alterar o cadastro da empresa não altera chamados antigos.
- `configuracao` é independente das demais tabelas.

As chaves estrangeiras são habilitadas em cada conexão. O schema cria índices para contatos por empresa, equipe por setor, chamados por status/data e escalonamentos por chamado.

Ao migrar uma base antiga, a tabela `cliente_contato` é renomeada para `cliente` mantendo os registros. A antiga tabela `documentacao`, cujas linhas não apontavam para chamados, é arquivada como `documentacao_legado` (ou com sufixo numérico) se contiver dados; em instalações novas ela não é criada. O histórico inicial dos chamados existentes é preenchido usando `data_abertura`.

### Case do banco de dados

Uma empresa de suporte de TI recebe de um cliente o relato de uma falha em seu computador. A equipe registra o cliente, descreve o problema e abre um chamado, atribuindo-o a um técnico responsável e ao setor correspondente. Quando o atendimento começa, registra-se a data e a hora de início da resolução; ao concluir o serviço, registra-se a data e a hora do fim. Com esses dados, o sistema calcula a duração de cada atendimento e gera um relatório com o tempo total acumulado dos chamados, ajudando a equipe a acompanhar o trabalho realizado e a identificar atendimentos que ainda precisam ser concluídos.

No modelo conceitual do case, o setor fica registrado como atributo do grupo solucionador. O registro do chamado precisa guardar os instantes de início e fim da resolução para que a duração possa ser calculada pela diferença entre eles e somada no relatório. No site atual já existem chamados, equipe, setores e acompanhamento de tempo, mas o schema e o relatório implementados ainda não correspondem integralmente a esse modelo: setores são uma tabela própria e o relatório atual agrupa chamados por status e classificação, sem somar a duração de todos eles.

## API

Todos os endpoints usam o prefixo `/api` e são servidos pelo mesmo processo Flask.

| Recurso | Endpoints |
| --- | --- |
| Saúde | `GET /api/health` |
| Chamados | `GET/POST /api/chamados`, `GET/PUT/DELETE /api/chamados/<id>` |
| Clientes | `GET/POST /api/clientes`, `PUT/DELETE /api/clientes/<id>` |
| Equipe | `GET/POST /api/equipe`, `PUT/DELETE /api/equipe/<id>` |
| Setores | `GET/POST /api/setores`, `DELETE /api/setores/<id>` |
| Contas e sessão | `POST /api/contas`, `POST /api/login`, `GET /api/sessao`, `POST /api/logout` |
| Relatórios | `GET /api/relatorios?periodo=todos|mes|dia` |
| Configurações | `GET/PUT /api/configuracoes` |

### Persistência e compartilhamento

O banco SQLite fica no computador que executa o servidor. Clonar ou atualizar o repositório não compartilha os registros. Para várias pessoas usarem o mesmo workspace, uma opção de teste é executar o HelpTI em um computador da rede local e acessar a mesma URL nos navegadores; todos usarão o banco desse servidor. Para backup, pare o servidor e copie `instance/helpti.sqlite3`. Não coloque o arquivo SQLite no Git para sincronizar dados. Para uso online ou produção, hospede a aplicação e configure um banco central (por exemplo, PostgreSQL ou MySQL) com acesso seguro.

Qualquer pessoa pode criar uma conta em “Criar conta” usando um e-mail com formato válido; não há verificação de domínio ou aprovação administrativa. O cadastro autentica a pessoa automaticamente com a senha escolhida. A primeira conta inicializa o workspace; as seguintes entram no workspace existente como “Usuário”, com acesso ao Dashboard e Chamados. Contas públicas não recebem permissões administrativas; a página Equipe não oferece o cargo Administrador e a API não permite criá-lo por esse formulário. Como o cadastro é aberto, qualquer pessoa que alcance essa tela pode entrar no workspace atual e visualizar chamados; não exponha o sistema publicamente antes de implementar isolamento por conta e controles de cadastro. O cookie de sessão é assinado por uma chave local em `instance/`.

A permissão `gerenciar_equipe` é separada da aba Equipe: ela controla criação/edição de funcionários e setores. Quem tem acesso a Chamados também recebe leituras auxiliares limitadas de clientes, técnicos e setores para preencher chamados; isso não libera as páginas de Clientes ou Equipe nem operações de escrita nesses módulos.

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

## Como executar

O projeto roda com um único processo. O Flask serve as páginas do frontend, disponibiliza a API e abre o navegador automaticamente.

### Primeira configuração

1. Instale Python 3.8 ou superior.
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

6. Não é necessário criar o banco nem configurar `DB_*` no `.env`. O SQLite e as tabelas são inicializados automaticamente.

O arquivo `backend/.env` é opcional e pode conter configurações `SMTP_*` para enviar e-mails quando um chamado for resolvido. Sem SMTP, os demais fluxos da aplicação continuam disponíveis, mas o encerramento com envio de e-mail retorna uma mensagem de configuração necessária. Nunca envie credenciais ao Git.

### Iniciar o projeto

Com as dependências instaladas e o ambiente virtual ativado, execute na pasta raiz `HelpTI`:

```powershell
python app.py
```

O arquivo [app.py](app.py) na raiz inicializa o banco local se necessário e inicia a API e o frontend. O navegador abrirá em `http://127.0.0.1:5000/`. O arquivo SQLite fica em `instance/helpti.sqlite3` e é ignorado pelo Git.

### Acesso pela rede local

Para permitir que outros computadores da mesma rede usem o mesmo servidor e banco, inicie o HelpTI no computador servidor pelo PowerShell:

```powershell
$env:HELPTI_HOST = '0.0.0.0'
$env:HELPTI_DEBUG = 'false'
python app.py
```

Descubra o IPv4 do computador servidor com `ipconfig` e, nos outros computadores, abra `http://<IPV4-DO-SERVIDOR>:5000/`. Se o Windows Firewall perguntar, permita o acesso somente em redes privadas confiáveis. Mantenha o servidor ligado e não exponha essa configuração diretamente à internet. O modo de depuração é desativado automaticamente quando o host não é local.

Depois, cada pessoa pode criar sua própria conta pela tela “Criar conta” na mesma URL; o cadastro entra automaticamente no workspace atual com acesso básico ao Dashboard e Chamados.

Endereços úteis:

- Aplicação: `http://127.0.0.1:5000/`
- Login direto: `http://127.0.0.1:5000/frontend/pages/login.html`
- Teste da API: `http://127.0.0.1:5000/api/health`
- Educação: `http://127.0.0.1:5000/frontend/pages/educacao.html`

Não é necessário executar `python -m http.server` nem abrir a porta 8000.

### Encerrar

No terminal em que o Flask está rodando, pressione `Ctrl+C`.

---

## Status do desenvolvimento

O projeto possui interface web, API Flask e persistência local em SQLite. A configuração e os dados iniciais são aplicados no primeiro start. SMTP é opcional e necessário somente para o envio de e-mails de resolução.

---

## Conclusão

Cada integrante trabalha com seu próprio banco SQLite local. Os dados não são enviados ao repositório nem sincronizados por `git pull`.

## Como contribuir

Antes de alterar o código, consulte [INTEGRACAO.md](INTEGRACAO.md) e a modelagem de dados acima. Faça mudanças pequenas, teste a API e o fluxo da tela correspondente e descreva no pull request o que foi alterado e como testar. Para dados locais, pare o servidor antes de copiar o arquivo de banco como backup.

---
