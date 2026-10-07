# Banco de dados Oracle do HelpTI

Esta pasta contém uma definição independente do esquema HelpTI para Oracle:

- `schema_oracle.sql`: cria as tabelas, relacionamentos, índices e dados iniciais de referência.

## Importante: não está conectado à aplicação

O HelpTI continua usando SQLite. A aplicação Flask não lê nem executa este arquivo, e criar este esquema não muda a configuração do projeto.

Este SQL é uma base de estrutura para uma futura migração. A implementação futura ainda precisará adaptar a camada Python de banco, os parâmetros e consultas SQL, o tratamento de datas, a criação/inicialização do esquema e o processo de migração dos dados existentes em SQLite.

## Como criar o esquema Oracle manualmente

1. Crie um usuário/schema dedicado ao HelpTI no Oracle Database ou no Autonomous Database.
2. Conecte-se como esse usuário no Oracle SQL Developer.
3. Abra `schema_oracle.sql` e confira que a conexão selecionada é o schema HelpTI correto.
4. Execute o script inteiro uma única vez. O script cria as tabelas e índices e inclui as configurações e categorias de chamado padrão; não cria usuário administrador nem dados de clientes/chamados.
5. Verifique no painel Connections do SQL Developer que as tabelas `USUARIO`, `CLIENTE`, `TIPO_CHAMADO`, `SETOR`, `GRUPO_SOLUCIONADORES`, `CHAMADO`, `HISTORICO_CHAMADO`, `ESCALONAMENTO`, `CONFIGURACAO` e `CODIGO_RECUPERACAO_SENHA` foram criadas.

O usuário Oracle precisa ter permissão para criar tabelas, índices e outros objetos no próprio schema. A sintaxe de colunas `IDENTITY` requer Oracle Database 12c ou mais recente.

Não coloque senhas de banco neste arquivo nem no Git. Guarde credenciais futuras em variáveis de ambiente ou em um gerenciador de segredos.
