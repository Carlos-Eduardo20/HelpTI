# Setup HelpTI com MySQL

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

```bash
# Copiar o template .env
cp .env.example .env

# Ou no Windows PowerShell:
Copy-Item .env.example .env
```

Edite o arquivo `.env`:
```
DB_HOST=localhost
DB_NAME=helpti
DB_USER=root
DB_PASSWORD=sua_senha_do_mysql
DB_PORT=3306
```

### 3. Criar o Banco de Dados

**Opção A: Usando MySQL Command Line**

```bash
mysql -u root -p < schema.sql
```

Vai pedir sua senha do MySQL e criar o banco automaticamente.

**Opção B: Usando MySQL Workbench**

1. Abra MySQL Workbench
2. Conecte com suas credenciais
3. Clique em `File` → `Open SQL Script`
4. Selecione `schema.sql`
5. Clique em ⚡ (Execute) ou `Ctrl+Shift+Enter`

**Opção C: Usando PowerShell (Windows)**

```powershell
Get-Content schema.sql | mysql -u root -p
```

### 4. Verificar a Conexão

```bash
python app.py
```

Se ver isso, está funcionando:
```
 * Running on http://127.0.0.1:5000
```

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
USE helpti;
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

### Erro: "Unknown database 'helpti'"
- Execute `schema.sql` novamente
- Verifique se o banco foi criado: `SHOW DATABASES;`

### Erro: "AttributeError: 'mysql.connector.cursor.MySQLCursor' object has no attribute 'description'"
- Certifique-se de executar uma query antes de usar `description`
- Use `dict_fetchall()` ou `dict_fetchone()` para converter resultados

## Parar o Servidor

No terminal onde o servidor está rodando:
```
Pressione CTRL+C
```

## Próximas Ações

1. ✅ Servidor rodando
2. ✅ Banco de dados criado
3. ➡️ Teste a API com o frontend
4. ➡️ Adicione dados aos modelos conforme necessário

## Documentação Completa

Para mais detalhes, veja [INTEGRACAO.md](./INTEGRACAO.md)
