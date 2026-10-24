INSERT INTO usuario (nome, email, status, tipo_usuario)
SELECT 'HelpTI', 'test@helpiti.com', 'ATIVO', 'WORKSPACE'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM usuario WHERE tipo_usuario = 'WORKSPACE' AND LOWER(email) = 'test@helpiti.com'
);

INSERT INTO grupo_solucionadores
    (descricao, nome, email, cargo, status, senha, permissoes, id_usuario)
SELECT
    'HelpTI',
    'Conta teste HelpTI',
    'test@helpiti.com',
    'Administrador',
    'ATIVO',
    'pbkdf2:sha256:600000$1j6gGx0UQMD8MGph$d4ac7cb3f5e59731d547e9d8f0a4ea0cd1c5c0a684f11eff6fe87d2129513696',
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
SET descricao = 'HelpTI', nome = 'Conta teste HelpTI'
WHERE LOWER(email) = 'test@helpiti.com';

UPDATE grupo_solucionadores
SET senha = 'pbkdf2:sha256:600000$1j6gGx0UQMD8MGph$d4ac7cb3f5e59731d547e9d8f0a4ea0cd1c5c0a684f11eff6fe87d2129513696'
WHERE LOWER(email) = 'test@helpiti.com'
  AND senha = 'pbkdf2:sha256:600000$helpti-demo-salt$ed4fcd7c8cb5bf394a9afaf63f2d687d4dd9a68e5728307f9ab8291b4a671aac';

INSERT INTO setor (nome, descricao, id_usuario)
SELECT 'Suporte', 'Setor inicial para testar o fluxo de chamados.', workspace.id_usuario
FROM usuario AS workspace
WHERE workspace.tipo_usuario = 'WORKSPACE'
  AND LOWER(workspace.email) = 'test@helpiti.com'
  AND NOT EXISTS (
      SELECT 1 FROM setor
      WHERE setor.id_usuario = workspace.id_usuario AND LOWER(setor.nome) = 'suporte'
  );

UPDATE usuario
SET workspace_name = COALESCE(workspace_name, 'HelpTI'),
    support_email = COALESCE(support_email, 'test@helpiti.com')
WHERE tipo_usuario = 'WORKSPACE'
  AND LOWER(email) = 'test@helpiti.com';

UPDATE grupo_solucionadores
SET id_setor = (
    SELECT setor.id_setor FROM setor
    WHERE setor.id_usuario = grupo_solucionadores.id_usuario AND LOWER(setor.nome) = 'suporte'
    ORDER BY setor.id_setor LIMIT 1
)
WHERE LOWER(email) = 'test@helpiti.com'
  AND id_setor IS NULL;
