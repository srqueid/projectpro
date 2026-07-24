-- =============================================================================
-- SCRIPT DE CRIAÇÃO DE TABELAS PARA O PROJETOPRO NO POSTGRESQL (VERSÃO 2.0)
-- Este script consolida todas as entidades da aplicação, incluindo a gestão
-- de times e a relação muitos-para-muitos com os responsáveis.
-- =============================================================================

-- Garante que a extensão para UUIDs esteja disponível.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- Tabela de Times
-- Armazena as equipes que podem ser associadas a projetos.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS times (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL UNIQUE
);

COMMENT ON TABLE times IS 'Cadastro das equipes de trabalho.';

-- -----------------------------------------------------------------------------
-- Tabela de Responsáveis (Usuários)
-- Armazena as informações de cada pessoa que pode ser designada para uma tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responsaveis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    modelo_trabalho VARCHAR(50),
    horas_semanais INTEGER,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE responsaveis IS 'Cadastro dos responsáveis pelas tarefas.';

-- -----------------------------------------------------------------------------
-- Tabela de Associação: Responsáveis <-> Times (Muitos para Muitos)
-- Define quais responsáveis pertencem a quais times.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responsaveis_times (
    responsavel_id UUID NOT NULL REFERENCES responsaveis(id) ON DELETE CASCADE,
    time_id UUID NOT NULL REFERENCES times(id) ON DELETE CASCADE,
    PRIMARY KEY (responsavel_id, time_id)
);

COMMENT ON TABLE responsaveis_times IS 'Tabela de junção para a relação N:M entre responsáveis e times.';

-- -----------------------------------------------------------------------------
-- Tabela de Férias
-- Permite que cada responsável tenha múltiplos períodos de férias.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ferias (
    id SERIAL PRIMARY KEY,
    responsavel_id UUID NOT NULL REFERENCES responsaveis(id) ON DELETE CASCADE,
    inicio DATE NOT NULL,
    fim DATE NOT NULL,
    CONSTRAINT chk_periodo_valido CHECK (fim >= inicio)
);

COMMENT ON TABLE ferias IS 'Armazena os períodos de férias de cada responsável.';

-- -----------------------------------------------------------------------------
-- Tabela de Projetos (com vínculo ao time)
-- Centraliza todos os projetos existentes.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projetos (
    id VARCHAR(255) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    time_id UUID REFERENCES times(id) ON DELETE SET NULL, -- Vínculo com o time
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE projetos IS 'Cadastro de todos os projetos, com vínculo opcional a um time.';

-- -----------------------------------------------------------------------------
-- Tabela de Tarefas
-- A tabela principal que armazena todas as tarefas de todos os projetos.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tarefas (
    pk_id SERIAL PRIMARY KEY,
    id INTEGER NOT NULL,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    fase VARCHAR(255),
    modulo VARCHAR(255),
    tarefa VARCHAR(255),
    subtarefa VARCHAR(255),
    dias INTEGER DEFAULT 1,
    predecessora_id INTEGER,
    conclusao INTEGER DEFAULT 0,
    responsavel_id UUID REFERENCES responsaveis(id) ON DELETE SET NULL,
    baseline_inicio DATE,
    baseline_fim DATE,
    inicio DATE,
    fim DATE,
    kanban_coluna_id VARCHAR(255),
    UNIQUE(projeto_id, id)
);

CREATE INDEX IF NOT EXISTS idx_tarefas_projeto ON tarefas(projeto_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_responsavel ON tarefas(responsavel_id);

COMMENT ON COLUMN tarefas.pk_id IS 'Chave primária real, auto-incrementada e interna.';
COMMENT ON COLUMN tarefas.id IS 'ID de exibição para o usuário (sequencial por projeto).';
COMMENT ON COLUMN tarefas.predecessora_id IS 'Refere-se ao ID de exibição da tarefa predecessora dentro do mesmo projeto.';

-- -----------------------------------------------------------------------------
-- Tabela de Colunas do Kanban
-- Configuração das colunas para cada projeto.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kanban_colunas (
    id SERIAL PRIMARY KEY,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    coluna_id VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    ordem INTEGER NOT NULL,
    UNIQUE(projeto_id, coluna_id)
);

-- -----------------------------------------------------------------------------
-- Tabela de Configurações Globais
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracoes (
    chave VARCHAR(255) PRIMARY KEY,
    valor VARCHAR(255) NOT NULL
);

INSERT INTO configuracoes (chave, valor) VALUES ('block_weekends', 'true') ON CONFLICT (chave) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Tabela de Feriados Customizados
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feriados_customizados (
    data DATE PRIMARY KEY,
    descricao VARCHAR(255)
);

-- =============================================================================
-- FIM DO SCRIPT
-- =============================================================================
