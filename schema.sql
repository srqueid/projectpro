-- =============================================================================
-- SCRIPT DE CRIAÇÃO DE TABELAS PARA O PROJETOPRO NO POSTGRESQL (VERSÃO 3.0)
-- Este script consolida todas as entidades da aplicação, organizadas em
-- SCHEMAS POR DOMÍNIO (sem utilizar o schema 'public').
--
--   schema 'rh'      -> Recursos Humanos: responsaveis, ferias, times, responsaveis_times
--   schema 'projeto' -> Projetos: projetos, tarefas, kanban_colunas, tarefa_atividades, projeto_configuracoes
--   schema 'config'  -> Configurações: configuracoes, feriados_customizados
-- =============================================================================

-- Cria os schemas por domínio (idempotente)
CREATE SCHEMA IF NOT EXISTS rh;
CREATE SCHEMA IF NOT EXISTS projeto;
CREATE SCHEMA IF NOT EXISTS config;

-- Garante que a extensão para UUIDs esteja disponível (instalada no schema 'public').
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- SCHEMA rh — RECURSOS HUMANOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela de Times
-- Armazena as equipes que podem ser associadas a projetos.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.times (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL UNIQUE
);

COMMENT ON TABLE rh.times IS 'Cadastro das equipes de trabalho.';

-- -----------------------------------------------------------------------------
-- Tabela de Responsáveis (Usuários)
-- Armazena as informações de cada pessoa que pode ser designada para uma tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.responsaveis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    modelo_trabalho VARCHAR(50),
    horas_semanais INTEGER,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rh.responsaveis IS 'Cadastro dos responsáveis pelas tarefas.';

-- -----------------------------------------------------------------------------
-- Tabela de Associação: Responsáveis <-> Times (Muitos para Muitos)
-- Define quais responsáveis pertencem a quais times.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.responsaveis_times (
    responsavel_id UUID NOT NULL REFERENCES rh.responsaveis(id) ON DELETE CASCADE,
    time_id UUID NOT NULL REFERENCES rh.times(id) ON DELETE CASCADE,
    PRIMARY KEY (responsavel_id, time_id)
);

COMMENT ON TABLE rh.responsaveis_times IS 'Tabela de junção para a relação N:M entre responsáveis e times.';

-- -----------------------------------------------------------------------------
-- Tabela de Férias
-- Permite que cada responsável tenha múltiplos períodos de férias.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.ferias (
    id SERIAL PRIMARY KEY,
    responsavel_id UUID NOT NULL REFERENCES rh.responsaveis(id) ON DELETE CASCADE,
    inicio DATE NOT NULL,
    fim DATE NOT NULL,
    CONSTRAINT chk_periodo_valido CHECK (fim >= inicio)
);

COMMENT ON TABLE rh.ferias IS 'Armazena os períodos de férias de cada responsável.';

-- =============================================================================
-- SCHEMA projeto — PROJETOS E TAREFAS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela de Projetos (com vínculo ao time de rh)
-- Centraliza todos os projetos existentes.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.projetos (
    id VARCHAR(255) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT, -- Descrição do projeto (objetivo macro)
    time_id UUID REFERENCES rh.times(id) ON DELETE SET NULL, -- Vínculo com o time (schema rh)
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE projeto.projetos IS 'Cadastro de todos os projetos, com vínculo opcional a um time.';

-- -----------------------------------------------------------------------------
-- Tabela de Tarefas
-- A tabela principal que armazena todas as tarefas de todos os projetos.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.tarefas (
    pk_id SERIAL PRIMARY KEY,
    id INTEGER NOT NULL,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    fase VARCHAR(255),
    modulo VARCHAR(255),
    tarefa VARCHAR(255),
    subtarefa VARCHAR(255),
    descricao TEXT,
    dias INTEGER DEFAULT 1,
    predecessora_id INTEGER,
    conclusao INTEGER DEFAULT 0,
    responsavel_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    baseline_inicio DATE,
    baseline_fim DATE,
    inicio DATE,
    fim DATE,
    restricao_tipo VARCHAR(50),
    restricao_data DATE,
    parent_id INTEGER,
    kanban_coluna_id VARCHAR(255),
    tipo VARCHAR(20) DEFAULT 'task',
    criterios_aceite TEXT,
    sprint VARCHAR(100),
    planejado BOOLEAN DEFAULT FALSE,
    UNIQUE(projeto_id, id)
);

CREATE INDEX IF NOT EXISTS idx_tarefas_projeto ON projeto.tarefas(projeto_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_responsavel ON projeto.tarefas(responsavel_id);

COMMENT ON COLUMN projeto.tarefas.pk_id IS 'Chave primária real, auto-incrementada e interna.';
COMMENT ON COLUMN projeto.tarefas.id IS 'ID de exibição para o usuário (sequencial por projeto).';
COMMENT ON COLUMN projeto.tarefas.predecessora_id IS 'Refere-se ao ID de exibição da tarefa predecessora dentro do mesmo projeto.';

-- -----------------------------------------------------------------------------
-- Tabela de Colunas do Kanban
-- Configuração das colunas para cada projeto.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.kanban_colunas (
    id SERIAL PRIMARY KEY,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    coluna_id VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    ordem INTEGER NOT NULL,
    progresso_padrao INTEGER,
    allow_back BOOLEAN DEFAULT TRUE,
    UNIQUE(projeto_id, coluna_id)
);

-- -----------------------------------------------------------------------------
-- Tabela de Atividades e Comentários das Tarefas
-- Armazena o histórico de alterações e os comentários de cada tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.tarefa_atividades (
    id SERIAL PRIMARY KEY,
    tarefa_pk_id INTEGER NOT NULL REFERENCES projeto.tarefas(pk_id) ON DELETE CASCADE,
    responsavel_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL, -- 'comentario' ou 'log'
    detalhe TEXT NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tarefa_atividades_tarefa ON projeto.tarefa_atividades(tarefa_pk_id);

COMMENT ON TABLE projeto.tarefa_atividades IS 'Log de atividades e comentários para cada tarefa.';

-- -----------------------------------------------------------------------------
-- Tabela de Configurações por Projeto
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.projeto_configuracoes (
    id SERIAL PRIMARY KEY,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    chave VARCHAR(255) NOT NULL,
    valor VARCHAR(255) NOT NULL,
    UNIQUE(projeto_id, chave)
);

-- =============================================================================
-- SCHEMA config — CONFIGURAÇÕES GERAIS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela de Configurações Globais
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config.configuracoes (
    chave VARCHAR(255) PRIMARY KEY,
    valor VARCHAR(255) NOT NULL
);

INSERT INTO config.configuracoes (chave, valor) VALUES ('block_weekends', 'true') ON CONFLICT (chave) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Tabela de Feriados Customizados
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config.feriados_customizados (
    data DATE PRIMARY KEY,
    descricao VARCHAR(255)
);

-- =============================================================================
-- FIM DO SCRIPT
-- =============================================================================
