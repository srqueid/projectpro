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
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS rh;
CREATE SCHEMA IF NOT EXISTS projeto;
CREATE SCHEMA IF NOT EXISTS config;

-- =============================================================================
-- SCHEMA core — NÚCLEO MULTI-TENANT
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela de Empresas (Tenant)
-- Contexto multi-tenant: todas as entidades pertencem a uma empresa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.empresas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(20),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE core.empresas IS 'Cadastro de empresas (tenants) para isolamento multi-tenant.';

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
    empresa_id UUID REFERENCES core.empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    UNIQUE(empresa_id, nome)
);

COMMENT ON TABLE rh.times IS 'Cadastro das equipes de trabalho.';

-- -----------------------------------------------------------------------------
-- Tabela de Perfis (Papéis de Acesso e Alçadas)
-- Define os perfis de usuário usados na matriz de promoção/rebaixamento:
--   product_manager   -> Gerente de Produto (aprova Feature ↔ Épico)
--   scrum_master      -> Gestor do Projeto (gestão do fluxo Scrum)
--   product_owner     -> Dono do Produto (aprova Tarefa/História ↔ Feature)
--   executor          -> Executor (decide livremente em Subtarefa ↔ Tarefa)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.perfis (
    id VARCHAR(50) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT
);

COMMENT ON TABLE rh.perfis IS 'Perfis de usuário e suas alçadas de aprovação.';

INSERT INTO rh.perfis (id, nome, descricao) VALUES
    ('product_manager', 'Gerente de Produto', 'Aprova transições envolvendo Épicos (Feature ↔ Épico).'),
    ('scrum_master', 'Gestor do Projeto', 'Gestão do fluxo Scrum; coordena o time e o andamento das entregas.'),
    ('product_owner', 'Dono do Produto', 'Aprova transições envolvendo Features (Tarefa/História ↔ Feature).'),
    ('executor', 'Executor', 'Decide livremente em Subtarefa ↔ Tarefa.')
ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, descricao = EXCLUDED.descricao;

-- -----------------------------------------------------------------------------
-- Tabela de Responsáveis (Usuários)
-- Armazena as informações de cada pessoa que pode ser designada para uma tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rh.responsaveis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID REFERENCES core.empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    modelo_trabalho VARCHAR(50),
    horas_semanais INTEGER,
    perfil VARCHAR(50) DEFAULT 'executor' REFERENCES rh.perfis(id),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(empresa_id, email)
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
    empresa_id UUID REFERENCES core.empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT, -- Descrição do projeto (objetivo macro)
    time_id UUID REFERENCES rh.times(id) ON DELETE SET NULL, -- Vínculo com o time (schema rh)
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(empresa_id, id)
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
-- Tabela de Épicos (maior nível hierárquico dentro de um projeto)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.epicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    status VARCHAR(50) DEFAULT 'PLANEJADO',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_epicos_projeto ON projeto.epicos(projeto_id);
CREATE INDEX IF NOT EXISTS idx_epicos_empresa ON projeto.epicos(empresa_id);

-- -----------------------------------------------------------------------------
-- Tabela de Features (filhas de um Épico)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    status VARCHAR(50) DEFAULT 'EM_ANDAMENTO',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_features_epico ON projeto.features(epico_id);

-- -----------------------------------------------------------------------------
-- Tabela de Histórias de Usuário (filhas de uma Feature)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.historias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
    feature_id UUID NOT NULL REFERENCES projeto.features(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    pontos INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'A_FAZER',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historias_epico ON projeto.historias(epico_id);
CREATE INDEX IF NOT EXISTS idx_historias_feature ON projeto.historias(feature_id);

-- -----------------------------------------------------------------------------
-- Tabela de Tarefas (normais ou extraordinárias)
-- - historia_id OBRIGATÓRIO para tarefas normais
-- - historia_id NULL + is_extraordinaria TRUE para tarefas extraordinárias
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.tarefas_hierarquicas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
    historia_id UUID REFERENCES projeto.historias(id) ON DELETE CASCADE,
    is_extraordinaria BOOLEAN NOT NULL DEFAULT FALSE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    status VARCHAR(50) DEFAULT 'A_FAZER',
    prioridade VARCHAR(20) DEFAULT 'MEDIA',
    responsavel_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    dias INTEGER DEFAULT 1,
    conclusao INTEGER DEFAULT 0,
    baseline_inicio DATE,
    baseline_fim DATE,
    inicio DATE,
    fim DATE,
    kanban_coluna_id VARCHAR(255),
    sprint VARCHAR(100),
    planejado BOOLEAN DEFAULT FALSE,
    predecessora_id UUID,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Regra de negócio: tarefa sem história é, obrigatoriamente, extraordinária.
    CONSTRAINT chk_tarefa_extraordinaria CHECK (
        (historia_id IS NOT NULL AND is_extraordinaria = FALSE) OR
        (historia_id IS NULL AND is_extraordinaria = TRUE)
    ),
    CONSTRAINT chk_tarefa_extraordinaria_titulo CHECK (titulo <> '')
);

CREATE INDEX IF NOT EXISTS idx_tarefas_hie_epico ON projeto.tarefas_hierarquicas(epico_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_hie_historia ON projeto.tarefas_hierarquicas(historia_id);
CREATE INDEX IF NOT EXISTS idx_tarefas_hie_empresa ON projeto.tarefas_hierarquicas(empresa_id);

-- -----------------------------------------------------------------------------
-- Tabela de Subtarefas (menor nível hierárquico)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.subtarefas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
    tarefa_id UUID NOT NULL REFERENCES projeto.tarefas_hierarquicas(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    concluida BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subtarefas_tarefa ON projeto.subtarefas(tarefa_id);
CREATE INDEX IF NOT EXISTS idx_subtarefas_empresa ON projeto.subtarefas(empresa_id);

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

-- =============================================================================
-- NOVA ARQUITETURA (WORK ITEM ENGINE)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela de Tipos de Work Item (configurável por projeto)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.work_item_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    icone VARCHAR(50),
    cor VARCHAR(20),
    -- parent_type_id permite definir hierarquias (ex: 'Subtask' só pode ser filha de 'Task')
    parent_type_id UUID REFERENCES projeto.work_item_types(id) ON DELETE SET NULL,
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(projeto_id, nome)
);

COMMENT ON TABLE projeto.work_item_types IS 'Tipos de itens de trabalho configuráveis por projeto (Task, Bug, Campaign, etc).';

-- -----------------------------------------------------------------------------
-- Tabela Central de Work Items (substitui tarefas, epicos, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.work_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    -- Chave legível para o usuário (ex: MKT-123)
    chave VARCHAR(20) NOT NULL,
    -- ID sequencial por projeto para gerar a chave
    seq_id SERIAL,
    type_id UUID NOT NULL REFERENCES projeto.work_item_types(id) ON DELETE RESTRICT,
    parent_id UUID REFERENCES projeto.work_items(id) ON DELETE SET NULL, -- Auto-relacionamento para hierarquia
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    status_id UUID, -- FK para workflow_statuses
    prioridade_id UUID, -- FK para uma futura tabela de prioridades
    responsavel_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    reporter_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    time_id UUID REFERENCES rh.times(id) ON DELETE SET NULL,
    data_vencimento DATE,
    data_inicio DATE,
    data_conclusao DATE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(projeto_id, chave)
);

CREATE INDEX IF NOT EXISTS idx_work_items_projeto ON projeto.work_items(projeto_id);
CREATE INDEX IF NOT EXISTS idx_work_items_responsavel ON projeto.work_items(responsavel_id);
CREATE INDEX IF NOT EXISTS idx_work_items_parent ON projeto.work_items(parent_id);

COMMENT ON TABLE projeto.work_items IS 'Entidade central para todos os itens de trabalho (tarefas, bugs, campanhas, etc).';

-- -----------------------------------------------------------------------------
-- Tabela de Atividades e Comentários das Tarefas
-- Armazena o histórico de alterações e os comentários de cada tarefa.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.work_item_atividades (
    id SERIAL PRIMARY KEY,
    work_item_id UUID NOT NULL REFERENCES projeto.work_items(id) ON DELETE CASCADE,
    responsavel_id UUID REFERENCES rh.responsaveis(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL, -- 'comentario' ou 'log'
    detalhe TEXT NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_work_item_atividades_work_item ON projeto.work_item_atividades(work_item_id);

COMMENT ON TABLE projeto.work_item_atividades IS 'Log de atividades e comentários para cada Work Item.';

-- -----------------------------------------------------------------------------
-- Tabela de Campos Personalizados (definição)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.custom_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    tipo_dado VARCHAR(50) NOT NULL, -- ex: 'text', 'number', 'date', 'user_picker'
    UNIQUE(projeto_id, nome)
);

COMMENT ON TABLE projeto.custom_fields IS 'Definição de campos personalizados por projeto.';

-- -----------------------------------------------------------------------------
-- Tabela de Valores de Campos Personalizados
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projeto.custom_field_values (
    id SERIAL PRIMARY KEY,
    work_item_id UUID NOT NULL REFERENCES projeto.work_items(id) ON DELETE CASCADE,
    custom_field_id UUID NOT NULL REFERENCES projeto.custom_fields(id) ON DELETE CASCADE,
    valor_texto TEXT,
    valor_numero NUMERIC,
    valor_data TIMESTAMP WITH TIME ZONE,
    valor_uuid UUID, -- Para campos como 'user_picker'
    UNIQUE(work_item_id, custom_field_id)
);

COMMENT ON TABLE projeto.custom_field_values IS 'Armazena os valores dos campos personalizados para cada work item.';

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
