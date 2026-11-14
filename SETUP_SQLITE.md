# Configuração do banco de dados SQLite

O HelpTI usa exclusivamente SQLite. O Python já inclui o driver; na primeira execução, a aplicação cria o banco e as tabelas automaticamente.

## Desenvolvimento local

Por padrão, o banco fica em `instance/helpti.sqlite3`. Para escolher outro caminho, defina `DB_SQLITE_PATH`:

```text
DB_SQLITE_PATH=instance/helpti.sqlite3
```

Inicie a aplicação com `python app.py`. O arquivo do banco contém os chamados, clientes, equipe, setores e configurações; não o apague se quiser preservar esses dados.

## Docker Compose

O `compose.yaml` monta o volume persistente `help-ti-data` em `/app/instance`. Reiniciar ou recriar o contêiner não remove o volume.

## Render

O sistema de arquivos padrão da Render é temporário. Para manter os dados:

1. Adicione um disco persistente ao serviço, montado em `/var/data`.
2. Configure `DB_SQLITE_PATH=/var/data/helpti.sqlite3`.
3. Use uma única instância; o disco não pode ser compartilhado entre instâncias.

Veja [README.md](./README.md#hospedagem-na-render) e [render.yaml](./render.yaml) para a configuração completa.

## Cópias de segurança

O endpoint administrativo `/api/admin/db/backup` gera uma cópia SQL dos dados do workspace. Em produção, faça também cópias periódicas do arquivo SQLite e armazene-as fora do mesmo disco.

## Migração de um banco MySQL antigo

A aplicação não converte automaticamente bancos de outro mecanismo. Exporte os dados necessários antes de remover o banco antigo e importe-os no SQLite usando um processo de migração compatível com o esquema atual. Sem exportação ou backup, não é possível recuperar dados que estavam somente naquele banco.
