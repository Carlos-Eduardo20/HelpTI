# Data Architecture & Persistence Layer

O HelpTI usa um banco SQLite com oito tabelas relacionais e SQL executado diretamente pela aplicação, sem ORM. `backend/schema.sql` é a fonte do schema e `backend/database.py` executa inicialização, versionamento e migrações compatíveis.

## Database Configuration

| Service/Module | DB Type | Profile | Driver | Connection | Migration Tool |
| --- | --- | --- | --- | --- | --- |
| Flask application | SQLite | All environments | Python `sqlite3` standard library | Local SQLite file or configured persistent file path | Application-managed SQL schema and versioned startup migrations; no external migration tool |

O banco não usa servidor separado nem pool externo. A aplicação executa o schema inicial e usa `PRAGMA user_version` com migrações implementadas no próprio módulo de banco. O modo de demonstração insere os tipos de chamado e a conta de teste por SQL de seed.

## Data Ownership per Service

| Service | Tables Owned | ORM Framework | Caching | Notes |
| --- | --- | --- | --- | --- |
| Flask application and SQLite database | `usuario`, `cliente`, `tipo_chamado`, `grupo_solucionadores`, `chamado`, `historico_chamado`, `escalonamento`, `documentacao` | None; direct SQL through a small `sqlite3` connection wrapper | None identified | One SQLite database; workspace ownership is represented by user and workspace foreign keys |

## Entity Model

The schema is defined in `backend/schema.sql`; data access and explicit transaction commits/rollbacks are in `backend/app.py`. SQLite foreign keys define the relationships below. There are no foreign-key columns protected by a `UNIQUE` constraint, so the schema does not enforce any 1:1 relationship. `chamado.cliente` is text, not a foreign key to `cliente` or `usuario`.

<!-- mermaid-checked: every attribute is `<type> <name> [<key>] ["<description>"]` with at most one of PK/FK/UK, no \n in descriptions, no {} in descriptions, every relationship label is double-quoted -->
```mermaid
erDiagram
    USUARIO o|--o{ USUARIO : "organizes workspace accounts"
    USUARIO ||--o{ CLIENTE : "owns contact rows"
    USUARIO o|--o{ CLIENTE : "scopes contacts by workspace"
    USUARIO ||--o{ GRUPO_SOLUCIONADORES : "owns team members"
    USUARIO o|--o{ CHAMADO : "records tickets"
    USUARIO o|--o{ DOCUMENTACAO : "owns documentation"
    TIPO_CHAMADO ||--o{ CHAMADO : "classifies"
    GRUPO_SOLUCIONADORES o|--o{ CHAMADO : "handles assigned tickets"
    CHAMADO ||--o{ HISTORICO_CHAMADO : "records history"
    CHAMADO ||--o{ ESCALONAMENTO : "records escalations"
    GRUPO_SOLUCIONADORES o|--o{ ESCALONAMENTO : "receives escalations"
    GRUPO_SOLUCIONADORES o|--o{ DOCUMENTACAO : "authors"

    USUARIO {
        int id_usuario PK
        int id_workspace FK "nullable self reference"
        string nome
        string email
        string tipo_usuario
        string status
    }

    CLIENTE {
        int id_cliente PK
        int id_usuario FK "required company owner"
        int id_workspace FK "nullable workspace owner"
        string nome
        string email
        string telefone
    }

    TIPO_CHAMADO {
        int id_tipo_chamado PK
        string nome
        string classificacao
        string descricao
    }

    GRUPO_SOLUCIONADORES {
        int id_grupo_solucionadores PK
        int id_usuario FK
        string nome
        string email
        string cargo
        string setor
        string status
    }

    CHAMADO {
        int id_chamado PK
        int id_tipo_chamado FK
        int id_grupo_solucionadores FK "nullable assignee"
        int id_usuario FK "nullable workspace owner"
        string cliente "text value without foreign key"
        string setor
        string status
        string descricao
    }

    HISTORICO_CHAMADO {
        int id_historico PK
        int id_chamado FK
        string evento
        string descricao
        string autor
    }

    ESCALONAMENTO {
        int id_escalonamento PK
        int id_chamado FK
        int id_grupo_destino FK "nullable destination"
        string motivo
        int nivel
        string setor_destino
    }

    DOCUMENTACAO {
        int id_documentacao PK
        int id_usuario FK "nullable workspace owner"
        int id_grupo_solucionadores FK "nullable author"
        string titulo
        string fornecedor
        string conteudo
    }
```

`CHAMADO` and `GRUPO_SOLUCIONADORES` have a logical N:N relationship over time through `ESCALONAMENTO`: a ticket can have multiple escalation records and a team member can be a destination in multiple records. The intermediary table also stores the reason, level, sector text and date. It is not a direct N:N foreign key.

`setor` is stored as text in `grupo_solucionadores` and `chamado`; the transfer destination is text in `escalonamento.setor_destino`. No `setor` table exists. The customer name and contact details copied into a ticket are text fields and are not constrained to match a customer record.

## Key Repository Methods

The project has no repository classes. Database reads and writes are SQL statements inside application functions.

| Service | Repository | Notable Methods | Purpose |
| --- | --- | --- | --- |
| Flask application | `backend/app.py` | `get_equipe()` | Lists team rows filtered to the current workspace |
| Flask application | `backend/app.py` | `get_setores()` | Reads distinct non-empty sector text values from team rows |
| Flask application | `backend/app.py` | `create_cliente()` | Creates a customer company and its contact rows in SQLite |
| Flask application | `backend/app.py` | `create_equipe()` | Creates a team member as a workspace-owned record |
| Flask application | `backend/app.py` | Ticket and escalation handlers | Persist tickets, their history and escalation records using explicit SQL transactions |

## Caching Strategy

No application-level or database query cache was identified. SQLite reads use direct SQL; the application does not configure a second-level ORM cache or an external cache provider.

## Data Ownership Boundaries

All eight tables are held in one SQLite file owned by the Flask application. Workspace isolation is implemented by filtering rows using workspace ownership fields. Foreign keys maintain references within the database, but the schema does not use composite foreign keys to prove that every linked row belongs to the same workspace. Several ownership fields are nullable, so the application also supplies part of the tenant boundary.

### Data Classification & Sensitivity

| Entity | Sensitive Fields | Classification | Controls in Place |
| --- | --- | --- | --- |
| `usuario` | Names, email, phone, address, CNPJ | PII and business identifiers | Workspace-level application filtering; no field-level encryption or masking is defined in the schema |
| `cliente` | Contact name, email and phone | PII | Workspace-level application filtering; no field-level encryption or masking is defined in the schema |
| `grupo_solucionadores` | Employee name, email, phone and password hash | PII and authentication data | Password is stored as a hash; no field-level encryption or masking is defined in the schema |
| `chamado` | Requester name, email, phone and free-text description | PII | Workspace-level application filtering; no field-level encryption or masking is defined in the schema |
| `historico_chamado` | Event author and free-text description | Potential PII | Stored with the related ticket; no field-level encryption or masking is defined in the schema |
| `documentacao` | Free-text technical content | Potentially sensitive operational data | Workspace-level application filtering; no field-level encryption or masking is defined in the schema |
| `tipo_chamado`, `escalonamento` | No explicit PII columns; text fields may contain user-provided details | Operational data, potentially PII in free text | No field-level encryption or masking is defined in the schema |

No dedicated PHI or PCI fields were identified in the SQLite schema. Free-text fields can still contain sensitive information entered by users.
