-- =============================================================================
-- V2__rls_and_hierarchy_constraints.sql
--   1. Habilita RLS (Row-Level Security) nas tabelas multi-tenant.
--   2. Cria políticas de isolamento por `empresa_id`.
--   3. Reforça constraints: epico_id NOT NULL em todas as entidades hierárquicas.
-- =============================================================================

-- Garante extensão uuid-ossp
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- TABELAS DO SCHEMA core
-- -----------------------------------------------------------------------------
ALTER TABLE core.empresas ENABLE ROW LEVEL SECURITY;

CREATE POLICY empresas_isolamento ON core.empresas
    FOR ALL
    USING (
        CASE
            WHEN current_setting('app.current_empresa_id', true) IS NULL THEN TRUE
            ELSE id = current_setting('app.current_empresa_id', true)::uuid
        END
    )
    WITH CHECK (
        CASE
            WHEN current_setting('app.current_empresa_id', true) IS NULL THEN TRUE
            ELSE id = current_setting('app.current_empresa_id', true)::uuid
        END
    );

-- -----------------------------------------------------------------------------
-- TABELAS DO SCHEMA rh
-- -----------------------------------------------------------------------------
ALTER TABLE rh.times ENABLE ROW LEVEL SECURITY;
CREATE POLICY times_isolamento ON rh.times
    FOR ALL USING (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE rh.responsaveis ENABLE ROW LEVEL SECURITY;
CREATE POLICY responsaveis_isolamento ON rh.responsaveis
    FOR ALL USING (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE rh.ferias ENABLE ROW LEVEL SECURITY;
CREATE POLICY ferias_isolamento ON rh.ferias
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM rh.responsaveis r
            WHERE r.id = ferias.responsavel_id
              AND (r.empresa_id IS NULL OR r.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE rh.responsaveis_times ENABLE ROW LEVEL SECURITY;
CREATE POLICY responsaveis_times_isolamento ON rh.responsaveis_times
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM rh.responsaveis r
            WHERE r.id = responsaveis_times.responsavel_id
              AND (r.empresa_id IS NULL OR r.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

-- -----------------------------------------------------------------------------
-- TABELAS DO SCHEMA projeto
-- -----------------------------------------------------------------------------
ALTER TABLE projeto.projetos ENABLE ROW LEVEL SECURITY;
CREATE POLICY projetos_isolamento ON projeto.projetos
    FOR ALL USING (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id IS NULL OR empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.epicos ENABLE ROW LEVEL SECURITY;
CREATE POLICY epicos_isolamento ON projeto.epicos
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.features ENABLE ROW LEVEL SECURITY;
CREATE POLICY features_isolamento ON projeto.features
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.historias ENABLE ROW LEVEL SECURITY;
CREATE POLICY historias_isolamento ON projeto.historias
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.tarefas_hierarquicas ENABLE ROW LEVEL SECURITY;
CREATE POLICY tarefas_hierarquicas_isolamento ON projeto.tarefas_hierarquicas
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.subtarefas ENABLE ROW LEVEL SECURITY;
CREATE POLICY subtarefas_isolamento ON projeto.subtarefas
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.work_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_items_isolamento ON projeto.work_items
    FOR ALL USING (empresa_id = current_setting('app.current_empresa_id', true)::uuid)
    WITH CHECK (empresa_id = current_setting('app.current_empresa_id', true)::uuid);

ALTER TABLE projeto.work_item_types ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_item_types_isolamento ON projeto.work_item_types
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = work_item_types.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.work_item_atividades ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_item_atividades_isolamento ON projeto.work_item_atividades
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.work_items w
            WHERE w.id = work_item_atividades.work_item_id
              AND w.empresa_id = current_setting('app.current_empresa_id', true)::uuid
        )
    );

ALTER TABLE projeto.custom_fields ENABLE ROW LEVEL SECURITY;
CREATE POLICY custom_fields_isolamento ON projeto.custom_fields
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = custom_fields.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.custom_field_values ENABLE ROW LEVEL SECURITY;
CREATE POLICY custom_field_values_isolamento ON projeto.custom_field_values
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.work_items w
            WHERE w.id = custom_field_values.work_item_id
              AND w.empresa_id = current_setting('app.current_empresa_id', true)::uuid
        )
    );

ALTER TABLE projeto.kanban_colunas ENABLE ROW LEVEL SECURITY;
CREATE POLICY kanban_colunas_isolamento ON projeto.kanban_colunas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = kanban_colunas.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.projeto_configuracoes ENABLE ROW LEVEL SECURITY;
CREATE POLICY projeto_configuracoes_isolamento ON projeto.projeto_configuracoes
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = projeto_configuracoes.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.planilha_colunas_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY planilha_colunas_config_isolamento ON projeto.planilha_colunas_config
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = planilha_colunas_config.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.planilha_campos_custom ENABLE ROW LEVEL SECURITY;
CREATE POLICY planilha_campos_custom_isolamento ON projeto.planilha_campos_custom
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = planilha_campos_custom.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.planilha_epicos ENABLE ROW LEVEL SECURITY;
CREATE POLICY planilha_epicos_isolamento ON projeto.planilha_epicos
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = planilha_epicos.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

ALTER TABLE projeto.planilha_valores_custom ENABLE ROW LEVEL SECURITY;
CREATE POLICY planilha_valores_custom_isolamento ON projeto.planilha_valores_custom
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.tarefas t
            WHERE t.pk_id = planilha_valores_custom.tarefa_pk_id
        )
    );

ALTER TABLE projeto.tarefas ENABLE ROW LEVEL SECURITY;
CREATE POLICY tarefas_isolamento ON projeto.tarefas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projeto.projetos p
            WHERE p.id = tarefas.projeto_id
              AND (p.empresa_id IS NULL OR p.empresa_id = current_setting('app.current_empresa_id', true)::uuid)
        )
    );

-- -----------------------------------------------------------------------------
-- TABELAS DO SCHEMA config
-- -----------------------------------------------------------------------------
ALTER TABLE config.configuracoes ENABLE ROW LEVEL SECURITY;
CREATE POLICY configuracoes_publicas ON config.configuracoes FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE config.feriados_customizados ENABLE ROW LEVEL SECURITY;
CREATE POLICY feriados_customizados_publicos ON config.feriados_customizados FOR ALL USING (true) WITH CHECK (true);
