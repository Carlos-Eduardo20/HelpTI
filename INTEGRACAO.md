# Integração Frontend-Backend HelpTI

## Estrutura da Integração

Esta aplicação HelpTI possui integração entre frontend (HTML/CSS/JS) e backend (Python/Flask) com banco de dados MySQL.

### Componentes

#### Frontend (HTML/CSS/JavaScript)

As páginas ficam na pasta `frontend`. O Flask as entrega pelas rotas `/frontend/...`, portanto elas não devem ser abertas por `file:///` nem por um servidor separado na porta 8000.

#### Backend (Flask)

O arquivo `backend/app.py` inicia a API e também serve o frontend. A rota `/` redireciona para a tela de login. O endereço base do sistema é `http://127.0.0.1:5000/`.

#### Database

O MySQL armazena chamados, clientes, equipe e configurações. Cada integrante deve usar seu próprio arquivo `backend/.env` com as credenciais do MySQL instalado em sua máquina.

## Endpoints da API

### Chamados
```
GET    /api/chamados              - Lista todos os chamados
GET    /api/chamados/<id>         - Busca um chamado específico
POST   /api/chamados              - Cria um novo chamado
PUT    /api/chamados/<id>         - Atualiza um chamado
```

### Clientes
```
GET    /api/clientes              - Lista todos os clientes
POST   /api/clientes              - Cria um novo cliente
```

### Equipe
```
GET    /api/equipe                - Lista a equipe
POST   /api/equipe                - Cadastra um membro da equipe
```

### Relatórios
```
GET    /api/relatorios            - Obtém dados de relatórios
```

### Configurações
```
GET    /api/configuracoes         - Obtém configurações
PUT    /api/configuracoes         - Salva configurações
```

### Health Check
```
GET    /api/health                - Verifica se a API está rodando
```

## Como Usar

### Instalação do Backend

1. Navegue até a pasta backend:
```bash
cd backend
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente (crie um `.env`):
```
DB_HOST=localhost
DB_NAME=HelpTI
DB_USER=root
DB_PASSWORD=sua_senha
```

4. Execute o servidor:
```bash
python app.py
```

O servidor rodará em `http://127.0.0.1:5000`

### Frontend

O frontend se conecta automaticamente à API em `http://127.0.0.1:5000/api`. Como frontend e backend são servidos pelo mesmo Flask, não é necessário iniciar outro servidor HTTP.

As funções disponíveis em `api.js`:

```javascript
import { 
  buscarChamados, 
  criarChamado, 
  atualizarChamado,
  buscarClientes,
  criarCliente,
  buscarEquipe,
  criarMembro,
  buscarRelatorios,
  buscarConfiguracoes,
  salvarConfiguracoes
} from './api.js';

// Uso:
const chamados = await buscarChamados();
await criarChamado({
  cliente: 'Tech Corp',
  assunto: 'Impressora não conecta',
  descricao: 'Falha ao conectar na rede',
  data_agendada: null,
  hora_agendada: null
});
```

## Fluxo de Funcionamento

1. **Dashboard carrega** → `dashboard.js` chama `buscarChamados()`
2. **buscarChamados()** → Faz requisição GET para `/api/chamados`
3. **Backend recebe** → Conecta ao banco e retorna dados em JSON
4. **Frontend processa** → Atualiza a tabela e a agenda

## Estrutura de Dados - Chamado

```json
{
  "id_chamado": 1,
  "id_tipo_chamado": 1,
  "id_grupo_solucionadores": null,
  "status": "ABERTO",
  "cliente": "Tech Corp",
  "assunto": "Impressora não conecta",
  "descricao": "Falha ao conectar na rede",
  "data_agendada": null,
  "hora_agendada": null
}
```

Status possíveis: `ABERTO`, `ANDAMENTO`, `AGUARDANDO`, `RESOLVIDO`

## Erros Comuns

### "Não foi possível conectar à API" ou "Failed to fetch"
- Confirme que o Flask está rodando com `python app.py` dentro de `backend`.
- Confirme `http://127.0.0.1:5000/api/health` no navegador.
- Abra o frontend por `http://127.0.0.1:5000/`, não por `file:///` ou `http://localhost:8000`.

### "Cannot GET /api/chamados"

### "CORS error"

### "Connection refused"

### "Module not found"

### Erro de tabela ou coluna no MySQL
- Execute `backend/schema.sql` no MySQL Workbench.
- Confira o banco ativo com `SELECT DATABASE();`.

## Teste rápido

Com o sistema em execução, abra `http://127.0.0.1:5000/api/health`. A resposta esperada é `{"status":"API rodando corretamente"}`.

Depois, abra `http://127.0.0.1:5000/`. Digite um e-mail, entre no dashboard, crie um chamado, cliente e membro da equipe. Os registros devem permanecer após atualizar a página, e o chamado deve aparecer na agenda.

## Como ajudar no projeto

Escolha uma tarefa, faça uma branch com um nome claro e mantenha as alterações focadas. Antes de abrir um pull request:

1. Inicie o MySQL e confirme as tabelas com `SHOW TABLES`.
2. Inicie o sistema com `python app.py` dentro de `backend`.
3. Teste o fluxo relacionado à alteração e descreva os passos no pull request.

## Próximas Melhorias

- autenticação real e permissões por perfil
- edição e exclusão de clientes, equipe e chamados
- filtros e relatórios com dados reais
- testes automatizados para os endpoints

