# app/migrations.py
"""
Módulo de migrações do banco de dados.
Gerencia alterações evolutivas no schema sem perder dados existentes.
"""

from . import config, database


def _schema_de_tabela(tabela):
    """
    Retorna o schema (domínio) da tabela com base no mapeamento por domínio.
    """
    if tabela in ('responsaveis', 'ferias', 'times', 'responsaveis_times'):
        return config.SCHEMA_RH
    if tabela in ('projetos', 'tarefas', 'kanban_colunas', 'tarefa_atividades', 'projeto_configuracoes'):
        return config.SCHEMA_PROJETO
    if tabela in ('configuracoes', 'feriados_customizados'):
        return config.SCHEMA_CONFIG
    return 'public'


def _coluna_existe(cur, tabela, coluna):
    """Verifica se uma coluna existe em uma tabela, no schema do domínio correspondente."""
    schema = _schema_de_tabela(tabela)
    cur.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
        (schema, tabela, coluna)
    )
    return cur.fetchone() is not None


def _adicionar_coluna(cur, tabela, coluna, tipo):
    """Adiciona uma coluna se ela não existir."""
    if not _coluna_existe(cur, tabela, coluna):
        schema = _schema_de_tabela(tabela)
        tabela_qualificada = f"{schema}.{tabela}"
        cur.execute(f"ALTER TABLE {tabela_qualificada} ADD COLUMN {coluna} {tipo};")
        print(f"[MIGRAÇÃO] Coluna '{coluna}' adicionada à tabela '{tabela_qualificada}'.")
        return True
    return False


def _garantir_schemas(cur):
    """
    Garante que os schemas por domínio existam antes de qualquer migração.
    """
    for schema in {config.SCHEMA_RH, config.SCHEMA_PROJETO, config.SCHEMA_CONFIG}:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")


def executar_migracoes():
    """
    Verifica e aplica migrações necessárias no banco de dados.
    Esta função é segura para ser executada múltiplas vezes (idempotente).
    """
    db = database.get_db()
    with db.cursor() as cur:
        _garantir_schemas(cur)
        migracoes_aplicadas = 0

        # ---------------------------------------------------------------
        # Migração 001: Adicionar coluna 'descricao' à tabela tarefas
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'descricao', 'TEXT'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 002: Adicionar coluna 'restricao_tipo' à tabela tarefas
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'restricao_tipo', 'VARCHAR(50)'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 003: Adicionar coluna 'restricao_data' à tabela tarefas
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'restricao_data', 'DATE'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 004: Adicionar coluna 'kanban_coluna_id' à tabela tarefas
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'kanban_coluna_id', 'VARCHAR(255)'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 005: Adicionar coluna 'parent_id' à tabela tarefas
        # (auto-referência para hierarquia pai-filho)
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'parent_id', 'INTEGER'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 006: Adicionar coluna 'descricao' à tabela projetos
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'projetos', 'descricao', 'TEXT'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 007: Adicionar coluna 'tipo' à tabela tarefas
        # (epic, story, task)
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'tipo', "VARCHAR(20) DEFAULT 'task'"):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 008: Adicionar coluna 'criterios_aceite' à tabela tarefas
        # (critérios de aceite para User Stories)
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'criterios_aceite', 'TEXT'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 009: Adicionar coluna 'sprint' à tabela tarefas
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'sprint', 'VARCHAR(100)'):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 010: Adicionar coluna 'planejado' à tabela tarefas
        # (se está planejado para um sprint, mostra no Kanban)
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'tarefas', 'planejado', "BOOLEAN DEFAULT FALSE"):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 011: Adicionar coluna 'allow_back' à tabela kanban_colunas
        # (permite ou não o movimento reverso na coluna)
        # ---------------------------------------------------------------
        if _adicionar_coluna(cur, 'kanban_colunas', 'allow_back', "BOOLEAN DEFAULT TRUE"):
            migracoes_aplicadas += 1

    db.commit()

    if migracoes_aplicadas > 0:
        print(f"[MIGRAÇÕES] {migracoes_aplicadas} migração(ões) aplicada(s) com sucesso.")
    else:
        print("[MIGRAÇÕES] Nenhuma migração necessária. Schema atualizado.")

