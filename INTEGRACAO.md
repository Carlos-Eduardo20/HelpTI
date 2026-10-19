# Integração Frontend-Backend HelpTI

## Estrutura da Integração

Esta aplicação HelpTI integra frontend (HTML/CSS/JavaScript), backend (Python/Flask) e banco MySQL (veja [SETUP_MYSQL.md](SETUP_MYSQL.md)).

### Componentes

#### Frontend (HTML/CSS/JavaScript)

As páginas ficam na pasta `frontend`. O Flask as entrega pelas rotas `/frontend/...`, portanto elas não devem ser abertas por `file:///` nem por um servidor separado na porta 8000.

#### Backend (Flask)

O arquivo `backend/app.py` inicia a API e também serve o frontend. A rota `/` redireciona para a tela de login. O endereço base do sistema é `http://127.0.0.1:5000/`.

#### Banco de dados

O MySQL armazena chamados, clientes, contatos, equipe, setores, escalonamentos e configurações no banco definido por `DB_NAME` (padrão `helpti_app`). A aplicação cria o banco e aplica o schema automaticamente. No modo demonstração, a conta local `test@helpiti.com` / `HelpTI2026!` e um setor vazio `Suporte` são criados. Configure as credenciais `DB_*` em `backend/.env`.

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

1. Na raiz do repositório, instale as dependências:
```bash
python -m pip install -r backend/requirements.txt
```

2. Execute o servidor na raiz:
```bash
python app.py
```

No início, o aplicativo executa uma checagem local de configuração de segurança. O primeiro start cria o banco e as tabelas. O servidor rodará em `http://127.0.0.1:5000`. Para notificações e códigos de recuperação de senha, configure `SMTP_*` em `backend/.env`.

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
  email_cliente: 'suporte@techcorp.com.br',
  telefone_cliente: '1133334444',
  contato_cliente: 'Ana Souza',
  telefone_contato: '11999998888',
  id_setor: 1,
  id_grupo_solucionadores: 1,
  descricao: 'Falha ao conectar na rede',
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
  "email_cliente": "suporte@techcorp.com.br",
  "telefone_cliente": "1133334444",
  "contato_cliente": "Ana Souza",
  "telefone_contato": "11999998888",
  "descricao": "Falha ao conectar na rede",
  "data_agendada": null,
  "hora_agendada": null
}
```

Status possíveis: `ABERTO`, `ANDAMENTO`, `AGUARDANDO`, `PAUSADO`, `RESOLVIDO`. Para resolver, use a ação de encerramento na tela do chamado; ela registra a descrição final e envia o e-mail ao cliente.

Com SMTP configurado, também é enviado um aviso ao abrir um chamado. A recuperação de senha envia um código de seis dígitos ao email cadastrado; ele expira em 10 minutos e só pode ser usado uma vez. A conta local de teste não usa uma caixa postal real, portanto não é possível receber emails para ela.

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
- Confirme que o MySQL está ativo e que `DB_*` em `backend/.env` estão corretos.
- Confira se o schema em `backend/schema.sql` contém a tabela/coluna esperada.
- Faça backup antes de apagar ou recriar o banco: ele contém os dados da aplicação.

## Teste rápido

Com o sistema em execução, abra `http://127.0.0.1:5000/api/health`. A resposta esperada é `{"status":"API rodando corretamente"}`.

Depois, abra `http://127.0.0.1:5000/`. Digite um e-mail, entre no dashboard, crie um chamado, cliente e membro da equipe. Os registros devem permanecer após atualizar a página, e o chamado deve aparecer na agenda.

## Como ajudar no projeto

Escolha uma tarefa, faça uma branch com um nome claro e mantenha as alterações focadas. Antes de abrir um pull request:

1. Inicie o sistema com `python app.py` na raiz; o MySQL é inicializado automaticamente.
2. Teste a API e o fluxo relacionado à alteração.
3. Descreva os passos de teste no pull request. Não versione o `backend/.env`.

## Próximas Melhorias

- autenticação real e permissões por perfil
- edição e exclusão de clientes, equipe e chamados
- filtros e relatórios com dados reais
- testes automatizados para os endpoints
