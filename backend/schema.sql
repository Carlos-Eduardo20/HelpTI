CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    contato TEXT,
    email TEXT,
    telefone TEXT,
    telefone_empresa TEXT,
    endereco TEXT,
    status TEXT NOT NULL DEFAULT 'ATIVO',
    tipo_usuario TEXT NOT NULL DEFAULT 'CLIENTE',
    cnpj TEXT,
    plano TEXT,
    acoes TEXT,
    workspace_name TEXT,
    support_email TEXT,
    senha_hash TEXT,
    id_workspace INTEGER,
    CONSTRAINT fk_usuario_workspace FOREIGN KEY (id_workspace)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usuario_workspace_cliente
    ON usuario (id_workspace, tipo_usuario);

CREATE TABLE IF NOT EXISTS cliente (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    nome TEXT NOT NULL,
    contato TEXT,
    email TEXT NOT NULL,
    telefone TEXT NOT NULL,
    id_workspace INTEGER,
    FOREIGN KEY (id_workspace) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cliente_usuario ON cliente (id_usuario);
CREATE INDEX IF NOT EXISTS idx_cliente_workspace ON cliente (id_workspace);

CREATE TABLE IF NOT EXISTS tipo_chamado (
    id_tipo_chamado INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    classificacao TEXT,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS setor (
    id_setor INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    niveis TEXT,
    id_usuario INTEGER,
    UNIQUE (id_usuario, nome),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS grupo_solucionadores (
    id_grupo_solucionadores INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT,
    nivel INTEGER,
    data_inicio TEXT,
    data_fim TEXT,
    nome TEXT,
    email TEXT,
    cargo TEXT,
    valor_hora NUMERIC,
    telefone TEXT,
    setor TEXT,
    status TEXT NOT NULL DEFAULT 'ATIVO',
    email_verificado INTEGER NOT NULL DEFAULT 1,
    senha TEXT NOT NULL DEFAULT '',
    permissoes TEXT NOT NULL DEFAULT '[]',
    foto_perfil TEXT,
    id_usuario INTEGER NOT NULL,
    id_setor INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_setor) REFERENCES setor(id_setor) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_setor
    ON grupo_solucionadores (id_setor);
CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_usuario
    ON grupo_solucionadores (id_usuario);
CREATE INDEX IF NOT EXISTS idx_grupo_solucionadores_email
    ON grupo_solucionadores (email);

CREATE TABLE IF NOT EXISTS chamado (
    id_chamado INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tipo_chamado INTEGER NOT NULL DEFAULT 1,
    id_setor INTEGER,
    setor TEXT,
    id_grupo_solucionadores INTEGER,
    status TEXT NOT NULL DEFAULT 'ABERTO',
    cliente TEXT NOT NULL,
    assunto TEXT,
    descricao TEXT,
    email_cliente TEXT,
    telefone_cliente TEXT,
    contato_cliente TEXT,
    telefone_contato TEXT,
    descricao_final TEXT,
    documentacao TEXT,
    tempo_decorrido_segundos INTEGER NOT NULL DEFAULT 0,
    tempo_inicio TEXT,
    data_abertura TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fechamento TEXT,
    data_agendada TEXT,
    hora_agendada TEXT,
    classificacao TEXT,
    id_usuario INTEGER,
    FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
    FOREIGN KEY (id_setor) REFERENCES setor(id_setor) ON DELETE SET NULL,
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chamado_status_data ON chamado (status, data_abertura);
CREATE INDEX IF NOT EXISTS idx_chamado_setor ON chamado (id_setor);
CREATE INDEX IF NOT EXISTS idx_chamado_workspace ON chamado (id_usuario, id_chamado);

CREATE TABLE IF NOT EXISTS historico_chamado (
    id_historico INTEGER PRIMARY KEY AUTOINCREMENT,
    id_chamado INTEGER NOT NULL,
    evento TEXT NOT NULL,
    descricao TEXT NOT NULL,
    autor TEXT NOT NULL DEFAULT 'Sistema',
    data_evento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_historico_chamado_data
    ON historico_chamado (id_chamado, data_evento);

CREATE TABLE IF NOT EXISTS escalonamento (
    id_escalonamento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_chamado INTEGER NOT NULL,
    motivo TEXT,
    nivel INTEGER,
    setor_destino TEXT,
    id_setor_destino INTEGER,
    id_grupo_destino INTEGER,
    data_escalonamento TEXT,
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado) ON DELETE CASCADE,
    FOREIGN KEY (id_setor_destino) REFERENCES setor(id_setor) ON DELETE SET NULL,
    FOREIGN KEY (id_grupo_destino)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_escalonamento_chamado
    ON escalonamento (id_chamado);

CREATE TABLE IF NOT EXISTS documentacao (
    id_documentacao INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor TEXT,
    id_grupo_solucionadores INTEGER,
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_documentacao_workspace ON documentacao (id_usuario);
CREATE INDEX IF NOT EXISTS idx_documentacao_grupo ON documentacao (id_grupo_solucionadores);

CREATE TABLE IF NOT EXISTS codigo_recuperacao_senha (
    id_codigo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_grupo_solucionadores INTEGER NOT NULL,
    codigo_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TEXT NOT NULL,
    tentativas INTEGER NOT NULL DEFAULT 0,
    usado INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_codigo_recuperacao_usuario
    ON codigo_recuperacao_senha (id_grupo_solucionadores, criado_em);

CREATE TABLE IF NOT EXISTS verificacao_cadastro_email (
    id_verificacao INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    empresa TEXT NOT NULL,
    email TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    codigo_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TEXT NOT NULL,
    tentativas INTEGER NOT NULL DEFAULT 0,
    usado INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_verificacao_cadastro_email
    ON verificacao_cadastro_email (email, criado_em);

CREATE TABLE IF NOT EXISTS identidade_microsoft (
    id_identidade INTEGER PRIMARY KEY AUTOINCREMENT,
    id_grupo_solucionadores INTEGER NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    UNIQUE (tenant_id, object_id),
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS login_rate_limit (
    client_hash TEXT PRIMARY KEY,
    window_started TEXT NOT NULL,
    attempts INTEGER NOT NULL
);

INSERT OR IGNORE INTO tipo_chamado (id_tipo_chamado, nome, classificacao, descricao) VALUES
(1, 'Suporte Geral', 'Suporte', 'Chamados gerais de suporte'),
(2, 'Hardware', 'Técnico', 'Problemas com hardware'),
(3, 'Software', 'Técnico', 'Problemas com software'),
(4, 'Rede', 'Infraestrutura', 'Problemas de rede');
