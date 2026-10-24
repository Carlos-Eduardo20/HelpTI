-- Schema MySQL 8 do HelpTI. Cada comando termina com ";" no fim da linha.

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    contato VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(50),
    telefone_empresa VARCHAR(50),
    endereco VARCHAR(500),
    status VARCHAR(30) NOT NULL DEFAULT 'ATIVO',
    tipo_usuario VARCHAR(30) NOT NULL DEFAULT 'CLIENTE',
    cnpj VARCHAR(30),
    plano VARCHAR(100),
    acoes TEXT,
    workspace_name VARCHAR(255),
    support_email VARCHAR(255),
    senha_hash VARCHAR(255),
    id_workspace INT,
    INDEX idx_usuario_workspace_cliente (id_workspace, tipo_usuario),
    CONSTRAINT fk_usuario_workspace FOREIGN KEY (id_workspace)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cliente (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    nome VARCHAR(255) NOT NULL,
    contato VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(50) NOT NULL,
    id_workspace INT,
    INDEX idx_cliente_usuario (id_usuario),
    INDEX idx_cliente_workspace (id_workspace),
    FOREIGN KEY (id_workspace) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tipo_chamado (
    id_tipo_chamado INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    classificacao VARCHAR(100),
    descricao VARCHAR(500)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS setor (
    id_setor INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    niveis TEXT,
    id_usuario INT,
    UNIQUE KEY uq_setor_workspace_nome (id_usuario, nome),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS grupo_solucionadores (
    id_grupo_solucionadores INT AUTO_INCREMENT PRIMARY KEY,
    descricao VARCHAR(255),
    nivel INT,
    data_inicio DATE,
    data_fim DATE,
    nome VARCHAR(255),
    email VARCHAR(255),
    cargo VARCHAR(100),
    valor_hora DECIMAL(10,2),
    telefone VARCHAR(50),
    setor VARCHAR(150),
    status VARCHAR(30) NOT NULL DEFAULT 'ATIVO',
    email_verificado TINYINT(1) NOT NULL DEFAULT 1,
    senha VARCHAR(255) NOT NULL DEFAULT '',
    permissoes VARCHAR(1000) NOT NULL DEFAULT '[]',
    foto_perfil MEDIUMTEXT,
    id_usuario INT NOT NULL,
    id_setor INT,
    INDEX idx_grupo_solucionadores_setor (id_setor),
    INDEX idx_grupo_solucionadores_usuario (id_usuario),
    INDEX idx_grupo_solucionadores_email (email),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_setor) REFERENCES setor(id_setor) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chamado (
    id_chamado INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_chamado INT NOT NULL DEFAULT 1,
    id_setor INT,
    setor VARCHAR(150),
    id_grupo_solucionadores INT,
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTO',
    cliente VARCHAR(255) NOT NULL,
    assunto VARCHAR(500),
    descricao TEXT,
    email_cliente VARCHAR(255),
    telefone_cliente VARCHAR(50),
    contato_cliente VARCHAR(255),
    telefone_contato VARCHAR(50),
    descricao_final TEXT,
    documentacao TEXT,
    tempo_decorrido_segundos INT NOT NULL DEFAULT 0,
    tempo_inicio DATETIME NULL,
    data_abertura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fechamento DATETIME NULL,
    data_agendada VARCHAR(20),
    hora_agendada VARCHAR(20),
    classificacao VARCHAR(100),
    id_usuario INT,
    INDEX idx_chamado_status_data (status, data_abertura),
    INDEX idx_chamado_setor (id_setor),
    INDEX idx_chamado_workspace (id_usuario, id_chamado),
    FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
    FOREIGN KEY (id_setor) REFERENCES setor(id_setor) ON DELETE SET NULL,
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS historico_chamado (
    id_historico INT AUTO_INCREMENT PRIMARY KEY,
    id_chamado INT NOT NULL,
    evento VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    autor VARCHAR(255) NOT NULL DEFAULT 'Sistema',
    data_evento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_historico_chamado_data (id_chamado, data_evento),
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS escalonamento (
    id_escalonamento INT AUTO_INCREMENT PRIMARY KEY,
    id_chamado INT NOT NULL,
    motivo TEXT,
    nivel INT,
    setor_destino VARCHAR(150),
    id_setor_destino INT,
    id_grupo_destino INT,
    data_escalonamento DATE,
    INDEX idx_escalonamento_chamado (id_chamado),
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado) ON DELETE CASCADE,
    FOREIGN KEY (id_setor_destino) REFERENCES setor(id_setor) ON DELETE SET NULL,
    FOREIGN KEY (id_grupo_destino)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS documentacao (
    id_documentacao INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor VARCHAR(255),
    id_grupo_solucionadores INT,
    titulo VARCHAR(255) NOT NULL,
    conteudo MEDIUMTEXT NOT NULL,
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario INT,
    INDEX idx_documentacao_workspace (id_usuario),
    INDEX idx_documentacao_grupo (id_grupo_solucionadores),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS codigo_recuperacao_senha (
    id_codigo INT AUTO_INCREMENT PRIMARY KEY,
    id_grupo_solucionadores INT NOT NULL,
    codigo_hash VARCHAR(255) NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em DATETIME NOT NULL,
    tentativas INT NOT NULL DEFAULT 0,
    usado TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_codigo_recuperacao_usuario (id_grupo_solucionadores, criado_em),
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS verificacao_cadastro_email (
    id_verificacao INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    empresa VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    codigo_hash VARCHAR(255) NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em DATETIME NOT NULL,
    tentativas INT NOT NULL DEFAULT 0,
    usado TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_verificacao_cadastro_email (email, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS identidade_microsoft (
    id_identidade INT AUTO_INCREMENT PRIMARY KEY,
    id_grupo_solucionadores INT NOT NULL UNIQUE,
    tenant_id VARCHAR(100) NOT NULL,
    object_id VARCHAR(100) NOT NULL,
    UNIQUE KEY idx_identidade_microsoft_tenant_object (tenant_id, object_id),
    FOREIGN KEY (id_grupo_solucionadores)
        REFERENCES grupo_solucionadores(id_grupo_solucionadores) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS login_rate_limit (
    client_hash VARCHAR(64) PRIMARY KEY,
    window_started DATETIME NOT NULL,
    attempts INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO tipo_chamado (id_tipo_chamado, nome, classificacao, descricao) VALUES
(1, 'Suporte Geral', 'Suporte', 'Chamados gerais de suporte'),
(2, 'Hardware', 'Técnico', 'Problemas com hardware'),
(3, 'Software', 'Técnico', 'Problemas com software'),
(4, 'Rede', 'Infraestrutura', 'Problemas de rede');
