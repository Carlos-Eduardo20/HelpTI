-- ============ BANCO DE DADOS HELPTI - MYSQL ============
-- Schema para aplicação HelpTI - Sistema de Gestão de Chamados
-- Compatível com MySQL 5.7+

-- Criar banco de dados
CREATE DATABASE IF NOT EXISTS HelpTI;
USE HelpTI;

-- Tabela de Usuários (Clientes)
CREATE TABLE usuario (
    id_usuario INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200),
    contato VARCHAR(50),
    email VARCHAR(255),
    telefone VARCHAR(50)
);

-- Tabela de Tipos de Chamados
CREATE TABLE tipo_chamado (
    id_tipo_chamado INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    classificacao VARCHAR(100),
    descricao VARCHAR(500)
);

-- Tabela de Grupos de Solucionadores
CREATE TABLE grupo_solucionadores (
    id_grupo_solucionadores INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    descricao VARCHAR(500),
    nivel INT,
    data_inicio DATE,
    data_fim DATE
);

-- Tabela de Chamados
CREATE TABLE chamado (
    id_chamado INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_tipo_chamado INT NOT NULL,
    id_grupo_solucionadores INT,
    status VARCHAR(50) DEFAULT 'ABERTO',
    FOREIGN KEY (id_tipo_chamado) REFERENCES tipo_chamado(id_tipo_chamado),
    FOREIGN KEY (id_grupo_solucionadores) REFERENCES grupo_solucionadores(id_grupo_solucionadores)
);

-- Tabela de Escalonamento
CREATE TABLE escalonamento (
    id_escalonamento INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_chamado INT NOT NULL,
    motivo VARCHAR(500),
    nivel INT,
    data_escalonamento DATE,
    FOREIGN KEY (id_chamado) REFERENCES chamado(id_chamado)
);

-- Tabela de Documentação
CREATE TABLE documentacao (
    id_documentacao INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_grupo_solucionadores INT,
    titulo VARCHAR(255),
    conteudo TEXT,
    data_criacao DATE,
    data_atualizacao DATE,
    FOREIGN KEY (id_grupo_solucionadores) REFERENCES grupo_solucionadores(id_grupo_solucionadores)
);

-- ============ DADOS INICIAIS (OPCIONAL) ============

-- Inserir tipos de chamados
INSERT INTO tipo_chamado (nome, classificacao, descricao) VALUES
('Suporte Geral', 'Suporte', 'Chamados gerais de suporte'),
('Hardware', 'Técnico', 'Problemas com hardware'),
('Software', 'Técnico', 'Problemas com software'),
('Rede', 'Infraestrutura', 'Problemas de rede');

-- Inserir grupos de solucionadores
INSERT INTO grupo_solucionadores (descricao, nivel) VALUES
('Grupo Nível 1', 1),
('Grupo Nível 2', 2),
('Grupo Nível 3', 3);
