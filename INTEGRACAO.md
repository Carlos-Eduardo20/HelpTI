# Integração Frontend-Backend HelpTI

## Estrutura da Integração

Esta aplicação HelpTI possui integração entre frontend (HTML/CSS/JS) e backend (Python/Flask) com banco de dados PostgreSQL.

### Componentes

#### Frontend (Angular/Vanilla JS)
- **Location**: `/frontend`
- **API Client**: `assets/js/api.js` - Funções para comunicar com backend
- **Main JS**: `assets/js/dashboard.js` - Lógica da aplicação
- **Pages**: Páginas HTML estáticas

#### Backend (Flask)
- **Location**: `/backend`
- **Main App**: `app.py` - Servidor Flask com rotas API
- **Database**: PostgreSQL com schema em `schema.sql`

#### Database
- **Type**: PostgreSQL
- **Schema**: Definido em `schema.sql`
- **Tables**: usuario, chamado, tipo_chamado, grupo_solucionadores, escalonamento, documentacao

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
DB_NAME=helpti
DB_USER=postgres
DB_PASSWORD=sua_senha
```

4. Execute o servidor:
```bash
python app.py
```

O servidor rodará em `http://127.0.0.1:5000`

### Frontend

O frontend se conecta automaticamente à API em `http://127.0.0.1:5000/api`.

As funções disponíveis em `api.js`:

```javascript
import { 
  buscarChamados, 
  criarChamado, 
  atualizarChamado,
  buscarClientes,
  criarCliente,
  buscarEquipe,
  buscarRelatorios,
  buscarConfiguracoes,
  salvarConfiguracoes
} from './api.js';

// Uso:
const chamados = await buscarChamados();
await criarChamado({ cliente: 'Tech Corp', assunto: 'Bug', prioridade: 'ALTA' });
```

## Fluxo de Funcionamento

1. **Dashboard carrega** → Chamada automática de `atualizarDashboard()`
2. **atualizarDashboard()** → Importa e chama `buscarChamados()` da API
3. **buscarChamados()** → Faz requisição GET para `/api/chamados`
4. **Backend recebe** → Conecta ao banco e retorna dados em JSON
5. **Frontend processa** → Atualiza os cards com os valores

## Estrutura de Dados - Chamado

```json
{
  "id_chamado": 1,
  "id_tipo_chamado": 1,
  "id_grupo_solucionadores": null,
  "status": "ABERTO"
}
```

Status possíveis: `ABERTO`, `ANDAMENTO`, `AGUARDANDO`, `RESOLVIDO`

## Erros Comuns

### "Cannot GET /api/chamados"
- Backend não está rodando
- URL da API está incorreta em `api.js`

### "CORS error"
- Flask CORS não está habilitado
- Verifique se `CORS(app)` está em `app.py`

### "Connection refused"
- PostgreSQL não está rodando
- Verifique credenciais do banco

### "Module not found"
- Dependências não estão instaladas
- Execute `pip install -r requirements.txt`

## Próximas Melhorias

- [ ] Adicionar autenticação e autorização
- [ ] Implementar websockets para atualizações em tempo real
- [ ] Adicionar validação de entrada no frontend
- [ ] Implementar cache no frontend
- [ ] Adicionar testes unitários
- [ ] Implementar logging
- [ ] Dockerizar a aplicação
