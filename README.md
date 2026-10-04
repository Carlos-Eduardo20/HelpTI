# HelpTI

Sistema web de gestão operacional para suporte técnico, com foco em acompanhar chamados, clientes, equipe e indicadores do atendimento de TI.

## Visão geral

O HelpTI é uma aplicação web para gestão de suporte técnico. O frontend usa HTML, CSS e JavaScript; o backend usa Flask e expõe uma API REST. Os dados são persistidos em SQLite, criado automaticamente na primeira inicialização.

### Problema que motivou o projeto

Uma equipe de suporte interno de TI controlava seus chamados em planilhas compartilhadas e por e-mail. Com o aumento das solicitações, esse processo passou a causar problemas que também dificultavam organizar os dados e produzir relatórios confiáveis:

- **Histórico incompleto:** linhas eram apagadas ou sobrescritas, então não havia um registro confiável das alterações de status, dos responsáveis e das ações realizadas.
- **Dados inconsistentes e duplicados:** cada pessoa podia escrever status e nomes de clientes de formas diferentes, e não havia validação nem relacionamentos que impedissem referências incorretas.
- **Conflito de atendimento:** duas pessoas podiam assumir ou alterar o mesmo chamado sem perceber, causando retrabalho e informações divergentes.

O projeto foi criado para resolver esse problema com uma aplicação apoiada por um banco de dados relacional: clientes, contatos, chamados, responsáveis e histórico ficam organizados em tabelas relacionadas, com valores padronizados e alterações registradas. Isso permite consultar os atendimentos e demonstrar como a modelagem e as restrições do banco ajudam a manter os dados consistentes.

O projeto reúne telas de login, dashboard, chamados, clientes, equipe, setores, relatórios, configurações, educação e planos. O Flask serve as páginas e a API no mesmo endereço.

A visualização interativa de componentes 3D da página Educação é desenhada em Python pelo Flask. Para iniciar o sistema e acessar a visualização, execute `python app.py` na raiz do projeto; não é necessário iniciar um aplicativo Tkinter separado.

---

## Estado atual do projeto

### Backend

- [backend/app.py](backend/app.py): aplicação Flask, páginas e endpoints da API
- [backend/database.py](backend/database.py): conexão SQLite e inicialização automática
- [backend/schema.sql](backend/schema.sql): tabelas, relacionamentos, índices e dados iniciais
- [backend/demo_seed.sql](backend/demo_seed.sql): usuário e dados fictícios iniciais para apresentação
- [backend/requirements.txt](backend/requirements.txt): dependências Python da aplicação

Chamados, clientes, contatos, equipe, setores e configurações permanecem salvos no banco local após reiniciar o servidor.

## Banco de dados

O banco padrão é SQLite. Na primeira inicialização, o sistema cria `instance/helpti.sqlite3` e aplica `backend/schema.sql` e `backend/demo_seed.sql`. Os arquivos SQL são versionados para que todos recebam o mesmo esquema e os mesmos dados fictícios iniciais; o arquivo SQLite de cada pessoa permanece local e não deve ser enviado ao Git.

Para entrar localmente na conta de demonstração, use `test@helpiti.com` com a senha `HelpTI2026!`. O endereço `teste@helpiti.com` também é aceito como alias. Em uma instalação limpa, o seed cria essas contas com perfil de administrador. Depois disso, o seed não redefine a senha nem reativa uma conta alterada. A senha é pública e só pode ser usada localmente: desligue `HELPTI_DEMO_MODE` antes de hospedar o sistema.

Cada clone executa seu próprio SQLite local: todos podem usar a conta de demonstração, mas as alterações feitas em um computador não aparecem nos bancos dos outros. Sem um banco ou servidor central compartilhado, não existe sincronização ao vivo dos dados entre clones. Os scripts `.sql` versionados distribuem o mesmo esquema e o mesmo estado inicial, não uma base de dados sincronizada. A senha da demonstração é pública e destinada exclusivamente a testes.

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

Cada clone ou Codespace recebe uma cópia inicial equivalente do esquema e dos dados fictícios. Depois disso, as alterações feitas em uma máquina não são sincronizadas com as outras: compartilhar o mesmo login não compartilha o banco local. Para a equipe trabalhar simultaneamente sobre os mesmos registros, execute uma única instância do HelpTI em um computador acessível a todos na rede local e use a mesma URL; para uso online, será necessário hospedar a aplicação e configurar um banco central com acesso seguro. Não coloque arquivos SQLite, `.env` ou credenciais no Git. O `.gitignore` já mantém esses arquivos locais fora do repositório, enquanto os scripts `.sql` permanecem versionados.

Em uma instalação sem workspace, o primeiro cadastro cria a empresa e a conta administradora. Depois que existe um workspace, o cadastro público é recusado; o administrador deve criar os outros acessos pela área Equipe. O primeiro cadastro de uma instalação nova deve ser feito e validado antes de publicar o endereço do site. Cada instalação representa somente um workspace; não use a mesma instalação para empresas diferentes. O cookie de sessão é assinado por uma chave local em `instance/`, persistida no volume quando executado via Docker.

A permissão `gerenciar_equipe` é separada da aba Equipe: ela controla criação/edição de funcionários e setores. Quem tem acesso a Chamados também recebe leituras auxiliares limitadas de clientes, técnicos e setores para preencher chamados; isso não libera as páginas de Clientes ou Equipe nem operações de escrita nesses módulos.

---

## Estrutura do projeto

```text
HelpTI/
├── README.md
├── Dockerfile
├── compose.yaml
├── wsgi.py
├── .dockerignore
├── .devcontainer/
│   └── devcontainer.json
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
4. Instale as dependências no Python disponível no sistema, sem criar ou ativar `.venv`:

```powershell
python -m pip install -r backend\requirements.txt
```

5. Não é necessário criar o banco nem configurar `DB_*` no `.env`. O SQLite, as tabelas e a conta de demonstração são inicializados automaticamente.

O arquivo `backend/.env` é opcional e local; use-o somente para configurações `SMTP_*` de envio de e-mail. Sem SMTP, os demais fluxos da aplicação continuam disponíveis, mas o encerramento com envio de e-mail informa que o serviço não está configurado. Nunca envie credenciais ao Git. O `.venv` é ignorado e não faz parte do fluxo padrão.

### Iniciar o projeto

Com as dependências instaladas, execute na pasta raiz `HelpTI`:

```powershell
python app.py
```

O arquivo [app.py](app.py) na raiz inicializa o banco local se necessário e inicia a API e o frontend. O navegador abrirá em `http://127.0.0.1:5000/`. O arquivo SQLite fica em `instance/helpti.sqlite3` e é ignorado pelo Git.

### Docker e Dev Container

O `Dockerfile` empacota o HelpTI e suas dependências em uma imagem. O `compose.yaml` inicia essa imagem como um container, publica a aplicação somente no próprio computador por padrão (`127.0.0.1:5000`) e guarda o SQLite em um volume Docker chamado `help-ti-data`. O volume mantém os dados quando o container é atualizado ou recriado. Cada computador tem seu próprio volume e seu próprio banco: Docker distribui o mesmo código, mas não sincroniza chamados entre amigos.

#### Executar no computador de cada pessoa

1. Instale e inicie o Docker Desktop no Windows ou macOS; no Linux, instale o Docker Engine com o plugin Docker Compose.
2. Para uma cópia nova, clone e entre na pasta:

```powershell
git clone https://github.com/Carlos-Eduardo20/HelpTI.git
cd HelpTI
```

   Se já tiver uma cópia, entre na pasta e execute `git pull`.
3. Abra o PowerShell/terminal na pasta raiz do HelpTI, onde estão `Dockerfile` e `compose.yaml`.
4. Inicie a aplicação:

```powershell
docker compose up --build -d
```

5. Abra `http://localhost:5000` e entre com `test@helpiti.com` e `HelpTI2026!`.
6. Para acompanhar a inicialização, use `docker compose logs -f help-ti` (Ctrl+C sai dos logs). Para parar o container sem apagar o banco, use `docker compose down`.

Em uma atualização futura, faça `git pull` e rode novamente `docker compose up --build -d`. A senha de demonstração e os dados iniciais vêm do seed versionado e são ativados localmente por padrão. `HELPTI_DEMO_MODE=false` desativa a criação do seed e bloqueia o login da conta de demonstração; essa opção é obrigatória em um ambiente público. O arquivo SQLite e a chave de sessão ficam no volume persistente, não na imagem nem no Git.

Em uma instalação sem dados, o primeiro cadastro cria o workspace. Depois disso, cadastros públicos são recusados; o administrador deve criar os acessos pela área de Equipe. Isso evita que visitantes se adicionem à empresa já cadastrada.

O container roda como usuário sem privilégios e usa Gunicorn em vez do servidor de desenvolvimento do Flask. `HELPTI_HTTPS_ONLY=true` ativa o atributo `Secure` do cookie de sessão quando a aplicação está atrás de um proxy HTTPS. Não publique a porta HTTP do Compose diretamente na internet.

#### Docker, Dev Container e hospedagem não são a mesma coisa

- **Docker** monta e executa o pacote isolado da aplicação.
- **Compose** configura como iniciar esse pacote, quais portas usar e onde guardar o banco.
- **Dev Container** (`.devcontainer/devcontainer.json`) prepara um ambiente para editar e desenvolver com VS Code. Localmente usa Docker; no GitHub Codespaces, roda na infraestrutura do Codespaces. A tarefa do VS Code inicia o HelpTI ao abrir a pasta.
- **Hospedagem** é um computador/serviço na internet que mantém o container ligado. Um domínio aponta para esse serviço; HTTPS protege a conexão entre o navegador e a aplicação. O domínio, o Docker e o volume não sincronizam nem substituem um banco de dados central.

O caminho de hospedagem será: navegador → domínio/DNS → hospedagem com certificado HTTPS → proxy/entrada HTTPS → container HelpTI → armazenamento persistente do banco. O sistema suporta um workspace por instalação, não várias empresas isoladas. O primeiro cadastro cria o workspace; depois, o administrador deve cadastrar os demais acessos. Crie e valide o administrador inicial antes de expor o site publicamente. Até implementar isolamento para múltiplas empresas, não permita que empresas diferentes compartilhem a mesma instalação. Na hospedagem, `HELPTI_DEMO_MODE=false` e `HELPTI_HTTPS_ONLY=true` são configurações necessárias. O SQLite é adequado para uma demonstração de instância única; para vários servidores ou usuários simultâneos em produção, planeje migrar para um banco gerenciado como PostgreSQL. Não reutilize o volume local dos amigos como banco hospedado.

### Acesso pela rede local

O Compose publica a aplicação somente em `localhost` por padrão. Isso é intencional: a sessão de demonstração usa credenciais conhecidas e a conexão HTTP não cifra o tráfego. Não altere o endereço de publicação para compartilhar o app pela rede ou pela internet antes de configurar autenticação adequada, HTTPS e isolamento dos dados de cada empresa. Um único servidor compartilhado também significa que os usuários acessam o mesmo banco SQLite; não é equivalente a cada amigo executar seu próprio clone.

Endereços úteis:

- Aplicação: `http://127.0.0.1:5000/`
- Login direto: `http://127.0.0.1:5000/frontend/pages/login.html`
- Teste da API: `http://127.0.0.1:5000/api/health`
- Educação: `http://127.0.0.1:5000/frontend/pages/educacao.html`

Não é necessário executar `python -m http.server` nem abrir a porta 8000.

### Encerrar

Para parar o container, execute `docker compose down` na pasta do projeto. O volume `help-ti-data` não é apagado por esse comando, portanto o banco continua guardado para a próxima inicialização.

---

## Status do desenvolvimento

O projeto possui interface web, API Flask e persistência local em SQLite. A configuração e os dados iniciais são aplicados no primeiro start. SMTP é opcional e necessário somente para o envio de e-mails de resolução.

---

## Conclusão

Cada integrante trabalha com seu próprio banco SQLite local. Os dados não são enviados ao repositório nem sincronizados por `git pull`.

## Como contribuir

Antes de alterar o código, consulte [INTEGRACAO.md](INTEGRACAO.md) e a modelagem de dados acima. Faça mudanças pequenas, teste a API e o fluxo da tela correspondente e descreva no pull request o que foi alterado e como testar. Para dados locais, pare o servidor antes de copiar o arquivo de banco como backup.

---
