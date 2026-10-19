# Configuração do HelpTI com MySQL

O HelpTI usa MySQL 8+. O banco e as tabelas são criados automaticamente na primeira inicialização (`backend/schema.sql`).

## 1. Pré-requisitos

- Python 3.8+
- MySQL Server 8+ em execução (ou Docker, veja o README)

## 2. Dependências

```bash
pip install -r backend/requirements.txt
```

## 3. Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha_do_mysql
DB_NAME=helpti_app
```

O usuário precisa de permissão para criar o banco `DB_NAME`; se ele já existir, basta ter acesso. Se houver um banco antigo com esquema legado (sem `id_workspace`), use outro nome em `DB_NAME`: a aplicação recusa iniciar sobre o esquema antigo.

## 4. E-mail (Zoho Mail)

Os códigos de cadastro e recuperação de senha são enviados por SMTP. Para usar uma conta Zoho, gere uma senha de aplicativo (Zoho Account → Security → App Passwords) e configure:

```
SMTP_HOST=smtp.zoho.com
SMTP_PORT=587
SMTP_USER=seu-email@seudominio.com
SMTP_PASSWORD=senha-de-aplicativo
SMTP_FROM=seu-email@seudominio.com
```

- Porta `587` usa STARTTLS; porta `465` usa SSL.
- Outras regiões: `smtp.zoho.com.br`, `smtp.zoho.eu`, etc.
- O login continua sendo e-mail + senha. A conta é criada em `account.html`, com o código enviado ao e-mail Zoho.

## 5. Iniciar

```bash
python app.py
```

Teste: `curl http://127.0.0.1:5000/api/health`

## Solução de problemas

- **Can't connect to MySQL server**: confira o serviço (`Get-Service MySQL80`), `DB_HOST` e `DB_PORT`.
- **Access denied**: confira `DB_USER` e `DB_PASSWORD`.
- **Esquema legado**: altere `DB_NAME` para um banco novo.
- **E-mail não enviado**: confira host, porta, senha de aplicativo e `SMTP_FROM`.

Mais detalhes em [INTEGRACAO.md](./INTEGRACAO.md).
