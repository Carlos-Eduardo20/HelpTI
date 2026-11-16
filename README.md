# HelpTI — Como Rodar o Projeto

Guia direto e prático para instalação, execução e testes do **HelpTI**.

> 📖 **Documentação técnica:**
> A modelagem atual do SQLite, com tabelas, relacionamentos e diagrama editável do draw.io, está na [seção 6 deste README](#6-modelagem-do-banco-sqlite). Para arquitetura da solução, regras de negócio e catálogo da API REST, consulte [DOCUMENTACAO_WRAPPER.md](DOCUMENTACAO_WRAPPER.md).

---

## 1. Pré-requisitos

Antes de iniciar, certifique-se de possuir em seu ambiente:
- **Python:** Versão 3.8 ou superior instalada ([python.org](https://www.python.org/downloads/)).
- **Git:** Instalado e configurado no terminal.
- **Navegador Web:** Qualquer navegador moderno (Google Chrome, Microsoft Edge, Mozilla Firefox).
- *(Opcional)* **Docker e Docker Compose:** Caso prefira executar o sistema em containers.

---

## 2. Como Rodar Localmente (Passo a Passo)

### 2.1. Clonar o Repositório
Abra o terminal ou PowerShell e execute:
```bash
git clone https://github.com/Carlos-Eduardo20/HelpTI.git
cd HelpTI
```

### 2.2. Instalar as Dependências
Com o ambiente virtual ativado, instale os pacotes requeridos:
```bash
pip install -r backend/requirements.txt
```
### 2.4. Criar o arquivo `.env`
Na pasta principal do projeto — a mesma pasta onde está `app.py` — crie um arquivo chamado `.env` (sem a extensão `.txt`). Abra-o e coloque:
```bash
HELPTI_DEMO_MODE=true
HELPTI_PORT=5000
```
Salve o arquivo. O valor `true` mantém a conta de teste ativa. Não é necessário colocar configurações de banco de dados: o HelpTI usa SQLite e cria automaticamente `instance/helpti.sqlite3`. A porta `5000` já é o padrão; ela só precisa estar no `.env` se quiser deixá-la explícita.

### 2.5. Iniciar a Aplicação
Execute o arquivo principal na raiz do projeto:
```bash
python app.py
```
Com `HELPTI_DEMO_MODE=true` no `.env`, a aplicação inicia com a conta teste. Na primeira execução, ela cria o banco SQLite em `instance/helpti.sqlite3`; não é preciso criar essa pasta ou configurar outro banco. Quando a aplicação iniciar, acesse [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

Use estas credenciais para entrar:
- **E-mail:** `test@helpiti.com`
- **Senha:** `HelpTI2026!!`

---

## 3. Conta de Teste e Novo Workspace

`HELPTI_DEMO_MODE=false` **desativa a conta teste**. Não use `false` se quiser entrar com as credenciais acima. Para desativar a demonstração e cadastrar um workspace próprio, há duas opções:

- No arquivo `.env`, troque `HELPTI_DEMO_MODE=true` por `HELPTI_DEMO_MODE=false`, salve e inicie a aplicação novamente.
- Ou, no PowerShell, execute estes comandos no terminal em que vai iniciar o projeto:

```powershell
$env:HELPTI_DEMO_MODE = "false"
python app.py
```

O comando do PowerShell vale para aquele terminal; para voltar a usar a conta teste, feche-o ou execute `$env:HELPTI_DEMO_MODE = "true"` e inicie novamente. No `.env`, escreva exatamente `HELPTI_DEMO_MODE=false` (sem espaços ao redor de `=` e sem aspas). No PowerShell, `$env:HELPTI_DEMO_MODE = "false"` é o comando para definir essa configuração antes de iniciar.

**Tela de cadastro:** [http://127.0.0.1:5000/frontend/pages/account.html](http://127.0.0.1:5000/frontend/pages/account.html)

---

## 8. Documentação Completa do Projeto

Para consultar o detalhamento de:
- Arquitetura de software e diagrama de componentes
- Justificativa técnica do atributo `setor` (sem tabela própria no modelo conceitual)
- Regras de negócio DeskOps (MTTR médio, SLA, permissões de cliente vs. técnico, autor no histórico)
- Catálogo exaustivo de endpoints da API REST

A modelagem SQLite atual está na [seção 6 deste README](#6-modelagem-do-banco-sqlite). Para os demais tópicos, consulte **[DOCUMENTACAO_WRAPPER.md](DOCUMENTACAO_WRAPPER.md)**.

---