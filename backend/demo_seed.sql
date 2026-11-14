INSERT INTO usuario (nome, email, status, tipo_usuario)
SELECT 'HelpTI', 'test@helpiti.com', 'ATIVO', 'WORKSPACE'
WHERE NOT EXISTS (
    SELECT 1 FROM usuario WHERE tipo_usuario = 'WORKSPACE' AND LOWER(email) = 'test@helpiti.com'
);

INSERT INTO grupo_solucionadores
    (descricao, nome, email, cargo, setor, status, senha, permissoes, id_usuario)
SELECT
    'HelpTI',
    'Conta teste HelpTI',
    'test@helpiti.com',
    'Administrador',
    'Suporte',
    'ATIVO',
    'pbkdf2:sha256:600000$sLjTP06hGqfycvJO$e6d4f2b0f4d774ede113b380829767a281fd46c91b5353560c7c66181519960a',
    '["dashboard","chamados","clientes","equipe","relatorios","educacao","configuracoes","gerenciar_equipe"]',
    workspace.id_usuario
FROM usuario AS workspace
WHERE workspace.tipo_usuario = 'WORKSPACE'
  AND LOWER(workspace.email) = 'test@helpiti.com'
  AND NOT EXISTS (
      SELECT 1 FROM grupo_solucionadores
      WHERE LOWER(email) = 'test@helpiti.com'
  )
LIMIT 1;

UPDATE usuario
SET nome = 'HelpTI'
WHERE tipo_usuario = 'WORKSPACE'
  AND LOWER(email) = 'test@helpiti.com';

UPDATE grupo_solucionadores
SET descricao = 'HelpTI',
    nome = 'Conta teste HelpTI',
    setor = COALESCE(NULLIF(TRIM(setor), ''), 'Suporte')
WHERE LOWER(email) = 'test@helpiti.com';

UPDATE grupo_solucionadores
SET senha = 'pbkdf2:sha256:600000$sLjTP06hGqfycvJO$e6d4f2b0f4d774ede113b380829767a281fd46c91b5353560c7c66181519960a'
WHERE LOWER(email) = 'test@helpiti.com';

UPDATE usuario
SET workspace_name = COALESCE(workspace_name, 'HelpTI'),
    support_email = COALESCE(support_email, 'test@helpiti.com')
WHERE tipo_usuario = 'WORKSPACE'
  AND LOWER(email) = 'test@helpiti.com';
