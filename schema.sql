-- =============================================================================
-- SCRIPT DE CRIAÇÃO DE TABELAS PARA O PROJETOPRO NO POSTGRESQL
-- =============================================================================

-- Habilita a extensão para usar UUIDs, ideal para chaves primárias únicas.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- Tabela de Responsáveis (Usuários)
-- Armazena as informações de cada pessoa que pode ser designada para uma tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE responsaveis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    modelo_trabalho VARCHAR(50),
    horas_semanais INTEGER,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE responsaveis IS 'Cadastro dos responsáveis pelas tarefas.';
COMMENT ON COLUMN responsaveis.id IS 'Identificador único universal para cada responsável.';
COMMENT ON COLUMN responsaveis.modelo_trabalho IS 'Ex: Home Office, Híbrido, Alocado.';

-- -----------------------------------------------------------------------------
-- Tabela de Férias
-- Permite que cada responsável tenha múltiplos períodos de férias.
-- -----------------------------------------------------------------------------
CREATE TABLE ferias (
    id SERIAL PRIMARY KEY,
    responsavel_id UUID NOT NULL REFERENCES responsaveis(id) ON DELETE CASCADE,
    inicio DATE NOT NULL,
    fim DATE NOT NULL,
    CONSTRAINT chk_periodo_valido CHECK (fim >= inicio)
);

COMMENT ON TABLE ferias IS 'Armazena os períodos de férias de cada responsável.';
COMMENT ON COLUMN ferias.responsavel_id IS 'Chave estrangeira para a tabela de responsáveis.';

-- -----------------------------------------------------------------------------
-- Tabela de Projetos
-- Centraliza todos os projetos existentes.
-- -----------------------------------------------------------------------------
CREATE TABLE projetos (
    id VARCHAR(255) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE projetos IS 'Cadastro de todos os projetos.';
COMMENT ON COLUMN projetos.id IS 'ID do projeto, derivado do nome (ex: "meu-projeto-novo").';

-- -----------------------------------------------------------------------------
-- Tabela de Tarefas
-- A tabela principal que armazena todas as tarefas de todos os projetos.
-- -----------------------------------------------------------------------------
CREATE TABLE tarefas (
    id SERIAL PRIMARY KEY,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    fase VARCHAR(255),
    modulo VARCHAR(255),
    tarefa VARCHAR(255),
    subtarefa VARCHAR(255),
    dias INTEGER DEFAULT 1,
    predecessora_id INTEGER REFERENCES tarefas(id) ON DELETE SET NULL,
    conclusao INTEGER DEFAULT 0,
    responsavel_id UUID REFERENCES responsaveis(id) ON DELETE SET NULL,

    -- Datas de Previsão (Planejamento Original)
    baseline_inicio DATE,
    baseline_fim DATE,

    -- Datas de Execução (Real)
    inicio DATE,
    fim DATE,

    kanban_coluna_id VARCHAR(255)
);

CREATE INDEX idx_tarefas_projeto ON tarefas(projeto_id);
CREATE INDEX idx_tarefas_responsavel ON tarefas(responsavel_id);

COMMENT ON TABLE tarefas IS 'Armazena todas as tarefas de todos os projetos.';
COMMENT ON COLUMN tarefas.predecessora_id IS 'Referência a outra tarefa neste mesmo projeto.';
COMMENT ON COLUMN tarefas.baseline_inicio IS 'Data de início PREVISTA no planejamento.';
COMMENT ON COLUMN tarefas.inicio IS 'Data em que a tarefa REALMENTE começou.';

-- -----------------------------------------------------------------------------
-- Tabela de Colunas do Kanban
-- Configuração das colunas para cada projeto.
-- -----------------------------------------------------------------------------
CREATE TABLE kanban_colunas (
    id SERIAL PRIMARY KEY,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    coluna_id VARCHAR(255) NOT NULL, -- Ex: "backlog", "em_andamento"
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- Ex: "inicio", "meio", "fim"
    ordem INTEGER NOT NULL,
    UNIQUE(projeto_id, coluna_id)
);

COMMENT ON TABLE kanban_colunas IS 'Configuração das colunas do Kanban para cada projeto.';

-- -----------------------------------------------------------------------------
-- Tabela de Configurações Globais
-- Armazena configurações gerais da aplicação.
-- -----------------------------------------------------------------------------
CREATE TABLE configuracoes (
    chave VARCHAR(255) PRIMARY KEY,
    valor VARCHAR(255) NOT NULL
);

INSERT INTO configuracoes (chave, valor) VALUES ('block_weekends', 'true');

COMMENT ON TABLE configuracoes IS 'Configurações globais da aplicação.';

-- -----------------------------------------------------------------------------
-- Tabela de Feriados Customizados
-- Armazena feriados e bloqueios que não são nacionais.
-- -----------------------------------------------------------------------------
CREATE TABLE feriados_customizados (
    data DATE PRIMARY KEY,
    descricao VARCHAR(255)
);

COMMENT ON TABLE feriados_customizados IS 'Feriados e datas de bloqueio customizadas.';

-- =============================================================================
-- FIM DO SCRIPT
-- =============================================================================
