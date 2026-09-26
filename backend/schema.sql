-- ============ BANCO DE DADOS HELPTI - MYSQL ============
-- Schema para aplicação HelpTI - Sistema de Gestão de Chamados
-- Compatível com MySQL 5.7+

-- Criar banco de dados
CREATE DATABASE IF NOT EXISTS HelpTI;
USE HelpTI;

-- Tabela de Usuários (Clientes)
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200),
    contato VARCHAR(50),
    email VARCHAR(255),
    telefone VARCHAR(50),
    cnpj VARCHAR(30),
    plano VARCHAR(100),
    acoes VARCHAR(500),
    senha_hash VARCHAR(255)
);

-- Tabela de Tipos de Chamados
CREATE TABLE IF NOT EXISTS tipo_chamado (
    id_tipo_chamado INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    classificacao VARCHAR(100),
    descricao VARCHAR(500)
);

-- Tabela de Setores e níveis de alocação
CREATE TABLE IF NOT EXISTS setor (
    id_setor INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200) NOT NULL UNIQUE,
    descricao VARCHAR(500),
    niveis TEXT
);

-- Tabela de Grupos de Solucionadores
CREATE TABLE IF NOT EXISTS grupo_solucionadores (
    id_grupo_solucionadores INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    descricao VARCHAR(500),
    nivel INT,
    data_inicio DATE,
    data_fim DATE,
    nome VARCHAR(200),
    email VARCHAR(255),
    cargo VARCHAR(100),
    valor_hora DECIMAL(10, 2),
    telefone VARCHAR(50),
    status VARCHAR(50) DEFAULT 'ATIVO',
    senha VARCHAR(255) NOT NULL
);

-- Tabela de Chamados
CREATE TABLE IF NOT EXISTS chamado (
    id_chamado MEDIUMINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_tipo_chamado INT NOT NULL,
    id_setor INT,
    id_grupo_solucionadores INT,
    status VARCHAR(50) DEFAULT 'ABERTO',
    cliente VARCHAR(200) NOT NULL,
    assunto VARCHAR(255) NULL,
    descricao TEXT,
    email_cliente VARCHAR(255),
    telefone_cliente VARCHAR(50),
    contato_cliente VARCHAR(200),
    telefone_contato VARCHAR(50),
    descricao_final TEXT,
    tempo_decorrido_segundos INT NOT NULL DEFAULT 0,
    tempo_inicio DATETIME NULL,
    data_abertura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_agendada DATE,
    hora_agendada TIME,
    classificacao TEXT(255) NULL,
    FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
    FOREIGN KEY (id_setor) REFERENCES setor(id_setor),
    FOREIGN KEY (id_grupo_solucionadores) REFERENCES grupo_solucionadores(id_grupo_solucionadores)
) AUTO_INCREMENT = 100000;

-- Tabela de Escalonamento
CREATE TABLE IF NOT EXISTS escalonamento (
    id_escalonamento INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_chamado MEDIUMINT UNSIGNED NOT NULL,
    motivo VARCHAR(500),
    nivel INT,
    id_setor_destino INT,
    id_grupo_destino INT,
    data_escalonamento DATE,
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado)
);

-- Tabela de Documentação
CREATE TABLE IF NOT EXISTS documentacao (
    id_documentacao INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_grupo_solucionadores INT,
    titulo VARCHAR(255),
    conteudo TEXT,
    data_criacao DATE,
    data_atualizacao DATE,
    FOREIGN KEY (id_grupo_solucionadores) REFERENCES grupo_solucionadores(id_grupo_solucionadores)
);

CREATE TABLE IF NOT EXISTS configuracao (
    id_configuracao INT NOT NULL PRIMARY KEY,
    workspace_name VARCHAR(200) NOT NULL,
    support_email VARCHAR(255) NOT NULL
);

INSERT IGNORE INTO configuracao (id_configuracao, workspace_name, support_email)
VALUES (1, 'HelpTI Suporte', 'suporte@helpti.com.br');

-- ============ DADOS INICIAIS (OPCIONAL) ============

-- Inserir tipos de chamados
INSERT IGNORE INTO tipo_chamado (nome, classificacao, descricao) VALUES
('Suporte Geral', 'Suporte', 'Chamados gerais de suporte'),
('Hardware', 'Técnico', 'Problemas com hardware'),
('Software', 'Técnico', 'Problemas com software'),
('Rede', 'Infraestrutura', 'Problemas de rede');

-- Inserir grupos de solucionadores
INSERT IGNORE INTO grupo_solucionadores (descricao, nivel) VALUES
('Grupo Nível 1', 1),
('Grupo Nível 2', 2),
('Grupo Nível 3', 3);
