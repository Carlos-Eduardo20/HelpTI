BEGIN;

INSERT INTO usuario (nome, email, status, tipo_usuario)
SELECT 'Logix Logística', 'test@helpiti.com', 'ATIVO', 'WORKSPACE'
WHERE NOT EXISTS (
    SELECT 1 FROM usuario WHERE tipo_usuario = 'WORKSPACE'
);

INSERT INTO grupo_solucionadores
    (descricao, nome, email, cargo, status, senha, permissoes, id_usuario)
SELECT
    'Logix Logística',
    'Conta de demonstração',
    'test@helpiti.com',
    'Administrador',
    'ATIVO',
    'pbkdf2:sha256:600000$helpti-demo-salt$ed4fcd7c8cb5bf394a9afaf63f2d687d4dd9a68e5728307f9ab8291b4a671aac',
    '["dashboard","chamados","clientes","equipe","relatorios","educacao","configuracoes","gerenciar_equipe"]',
    workspace.id_usuario
FROM usuario AS workspace
WHERE workspace.tipo_usuario = 'WORKSPACE'
  AND NOT EXISTS (
      SELECT 1 FROM grupo_solucionadores
      WHERE LOWER(email) = 'test@helpiti.com'
  )
LIMIT 1;

INSERT INTO grupo_solucionadores
    (descricao, nome, email, cargo, status, senha, permissoes, id_usuario)
SELECT
    'Logix Logística',
    'Conta de demonstração',
    'teste@helpiti.com',
    'Administrador',
    'ATIVO',
    'pbkdf2:sha256:600000$helpti-demo-salt$ed4fcd7c8cb5bf394a9afaf63f2d687d4dd9a68e5728307f9ab8291b4a671aac',
    '["dashboard","chamados","clientes","equipe","relatorios","educacao","configuracoes","gerenciar_equipe"]',
    workspace.id_usuario
FROM usuario AS workspace
WHERE workspace.tipo_usuario = 'WORKSPACE'
  AND NOT EXISTS (
      SELECT 1 FROM grupo_solucionadores
      WHERE LOWER(email) = 'teste@helpiti.com'
  )
LIMIT 1;

INSERT INTO usuario
    (nome, contato, email, telefone, telefone_empresa, endereco, status, tipo_usuario)
SELECT
    'Logix Logística',
    'Mariana Costa',
    'suporte@logix.example',
    '(11) 4000-0101',
    '(11) 4000-0100',
    'Centro de Distribuição - São Paulo',
    'ATIVO',
    'CLIENTE'
WHERE NOT EXISTS (
    SELECT 1 FROM usuario
    WHERE tipo_usuario = 'CLIENTE' AND LOWER(nome) = LOWER('Logix Logística')
);

INSERT INTO cliente (id_usuario, nome, email, telefone)
SELECT empresa.id_usuario, 'Mariana Costa', 'mariana.costa@logix.example', '(11) 4000-0101'
FROM usuario AS empresa
WHERE empresa.tipo_usuario = 'CLIENTE'
  AND LOWER(empresa.nome) = LOWER('Logix Logística')
  AND NOT EXISTS (
      SELECT 1 FROM cliente
      WHERE cliente.id_usuario = empresa.id_usuario
        AND LOWER(cliente.email) = LOWER('mariana.costa@logix.example')
  );

INSERT INTO cliente (id_usuario, nome, email, telefone)
SELECT empresa.id_usuario, 'Rafael Nunes', 'rafael.nunes@logix.example', '(11) 4000-0102'
FROM usuario AS empresa
WHERE empresa.tipo_usuario = 'CLIENTE'
  AND LOWER(empresa.nome) = LOWER('Logix Logística')
  AND NOT EXISTS (
      SELECT 1 FROM cliente
      WHERE cliente.id_usuario = empresa.id_usuario
        AND LOWER(cliente.email) = LOWER('rafael.nunes@logix.example')
  );

INSERT INTO setor (nome, descricao, niveis)
SELECT 'Suporte interno', 'Atendimento de TI da Logix Logística.', '["Nível 1","Nível 2"]'
WHERE NOT EXISTS (
    SELECT 1 FROM setor WHERE LOWER(nome) = LOWER('Suporte interno')
);

INSERT INTO chamado
    (id_tipo_chamado, id_setor, status, cliente, assunto, descricao,
     email_cliente, telefone_cliente, contato_cliente, telefone_contato, classificacao)
SELECT
    1,
    (SELECT id_setor FROM setor WHERE LOWER(nome) = LOWER('Suporte interno') LIMIT 1),
    'ABERTO',
    'Logix Logística',
    'Falha ao acessar o sistema de expedição',
    'A equipe do centro de distribuição não consegue concluir a expedição dos pedidos. Registrar os testes e atualizações no histórico do chamado.',
    'suporte@logix.example',
    '(11) 4000-0100',
    'Mariana Costa',
    '(11) 4000-0101',
    'Software'
WHERE NOT EXISTS (
    SELECT 1 FROM chamado
    WHERE cliente = 'Logix Logística'
      AND assunto = 'Falha ao acessar o sistema de expedição'
);

INSERT INTO chamado
    (id_tipo_chamado, id_setor, status, cliente, assunto, descricao,
     email_cliente, telefone_cliente, contato_cliente, telefone_contato, classificacao)
SELECT
    2,
    (SELECT id_setor FROM setor WHERE LOWER(nome) = LOWER('Suporte interno') LIMIT 1),
    'ABERTO',
    'Logix Logística',
    'Computador do estoque sem conexão de rede',
    'O computador usado para registrar a entrada de mercadorias perdeu a conexão com a rede interna.',
    'suporte@logix.example',
    '(11) 4000-0100',
    'Rafael Nunes',
    '(11) 4000-0102',
    'Hardware'
WHERE NOT EXISTS (
    SELECT 1 FROM chamado
    WHERE cliente = 'Logix Logística'
      AND assunto = 'Computador do estoque sem conexão de rede'
);

COMMIT;
