# Setup legado HelpTI com MySQL

> **Este guia não descreve mais a configuração padrão do projeto.** O HelpTI agora usa SQLite local e cria `instance/helpti.sqlite3` automaticamente. Para uma instalação nova, siga a seção “Como executar” do [README](README.md); não instale MySQL nem execute os comandos deste guia.
>
> Esta página foi mantida apenas como referência para instalações antigas. Os dados existentes no MySQL não são apagados nem migrados automaticamente para o SQLite. Faça backup e planeje uma migração explícita antes de deixar de usar a base antiga.

## Pré-requisitos

1. **Python 3.8+** instalado
2. **MySQL Server** instalado e rodando
3. **pip** (gerenciador de pacotes Python)

## Passo a Passo

### 1. Instalar Dependências

```bash
cd backend
pip install -r requirements.txt
```

Isso vai instalar:
- Flask 2.3.3
- Flask-CORS 4.0.0
- mysql-connector-python 8.0.33
- python-dotenv 1.0.0

### 2. Configurar Variáveis de Ambiente

Copie `backend/.env.example` para `backend/.env` e ajuste o usuário e a senha usados na sua instalação local do MySQL. O arquivo `.env` não deve ser enviado ao GitHub, pois contém a senha do banco:

```
DB_HOST=localhost
DB_NAME=HelpTI
DB_USER=root
DB_PASSWORD=sua_senha_do_mysql
DB_PORT=3306

# Configuração de e-mail para avisos de chamados resolvidos
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=senha-de-app-do-email
SMTP_FROM=seu-email@gmail.com
```

O `SMTP_PASSWORD` deve ser uma senha de aplicativo do provedor de e-mail, e não a senha normal da conta. Para outro provedor, use o host e a porta SMTP correspondentes.

### Contas temporárias do projeto

É possível criar contas como `ana@helpTI.com` e `carlos@helpTI.com` para uso durante o projeto e removê-las depois. Isso só funciona se a equipe controlar o domínio `helpTI.com` e contratar/configurar um serviço de e-mail para esse domínio. O endereço do remetente deve ser uma conta ou alias autorizado pelo provedor SMTP.

Cada integrante deve copiar `backend/.env.example` para `backend/.env` e preencher suas próprias credenciais. Não compartilhe senhas SMTP no Git. O endereço digitado no chamado continua sendo o destinatário e pode ser diferente do remetente.

### 3. Criar o Banco de Dados

**Opção A: Usando MySQL Command Line**

Execute o arquivo [backend/schema.sql](backend/schema.sql). Ele cria o banco `HelpTI`, incluindo as tabelas `chamado`, `tipo_chamado`, `usuario` e `grupo_solucionadores`.
```bash
cd backend
mysql -u root -p < schema.sql
```

Vai pedir sua senha do MySQL e criar o banco automaticamente.

**Opção B: Usando MySQL Workbench**

1. Abra MySQL Workbench
2. Conecte com suas credenciais
3. Clique em `File` → `Open SQL Script`
4. Selecione `backend/schema.sql`
5. Clique em ⚡ (Execute) ou `Ctrl+Shift+Enter`

Se o banco já existia antes da coluna de senha ser adicionada, execute também este comando no Workbench:

```sql
USE HelpTI;

ALTER TABLE grupo_solucionadores
ADD COLUMN senha VARCHAR(255);
```

Se aparecer o erro de que a coluna já existe, não execute o comando novamente. Confirme a estrutura com:

```sql
DESCRIBE grupo_solucionadores;
```

A coluna `senha` deve aparecer no resultado.

Para bancos criados antes do campo de e-mail dos chamados, execute:

```sql
USE HelpTI;
ALTER TABLE chamado ADD COLUMN email_cliente VARCHAR(255) NULL;
```

Chamados antigos sem e-mail não poderão ser marcados como resolvidos até que o endereço seja preenchido.

**Opção C: Usando PowerShell (Windows)**

```powershell
Get-Content backend/schema.sql | mysql -u root -p
```

### 4. Verificar a Conexão

Na pasta `backend`, execute:

```bash
python app.py
```

Se aparecer uma mensagem semelhante a esta, a API iniciou:

```
 * Running on http://127.0.0.1:5000
```

O navegador também será aberto automaticamente na tela de login. Frontend e backend usam esse mesmo processo.

### 5. Usar a API

A API estará disponível em: `http://127.0.0.1:5000/api`

**Testar a saúde da API:**
```bash
curl http://127.0.0.1:5000/api/health
```

**Listar chamados:**
```bash
curl http://127.0.0.1:5000/api/chamados
```

## Verificação do MySQL

**Verificar se MySQL está rodando:**

```bash
# Windows - Services
services.msc

# Ou via PowerShell:
Get-Service MySQL80
```

**Conectar ao MySQL:**
```bash
mysql -u root -p
```

**Ver bancos disponíveis:**
```sql
SHOW DATABASES;
```

**Usar banco HelpTI:**
```sql
USE HelpTI;
SHOW TABLES;
```

## Solução de Problemas

### Erro: "Can't connect to MySQL server"
- Verifique se MySQL está rodando
- Corrija o `DB_HOST` no `.env`
- Verifique a porta (padrão: 3306)

### Erro: "Access denied for user 'root'"
- Verifique a senha em `.env`
- Resete a senha do MySQL se necessário

### Erro: "Unknown database 'HelpTI'"
- Execute `schema.sql` novamente
- Verifique se o banco foi criado: `SHOW DATABASES;`

### Limpar os dados de teste

Para apagar chamados, clientes e equipe sem remover as tabelas, execute no Workbench:

```sql
USE HelpTI;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE chamado;
TRUNCATE TABLE usuario;
TRUNCATE TABLE grupo_solucionadores;
TRUNCATE TABLE escalonamento;
TRUNCATE TABLE documentacao;
SET FOREIGN_KEY_CHECKS = 1;
```

Os tipos de chamado e as configurações são mantidos.

### Erro: "AttributeError: 'mysql.connector.cursor.MySQLCursor' object has no attribute 'description'"
- Certifique-se de executar uma query antes de usar `description`
- Use `dict_fetchall()` ou `dict_fetchone()` para converter resultados

## Parar o Servidor

No terminal onde o servidor está rodando:
```
Pressione CTRL+C
```

## Próximas Ações

1. Instale as dependências Python.
2. Execute o `backend/schema.sql` no MySQL Workbench.
3. Crie o arquivo `backend/.env` com as credenciais do MySQL local.
4. Inicie o sistema completo com `python app.py` dentro de `backend`.
5. Use a aplicação em `http://127.0.0.1:5000/`.

## Documentação Completa

Para mais detalhes, veja [INTEGRACAO.md](./INTEGRACAO.md)
