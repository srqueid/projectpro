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
    if tabela in ('empresas',):
        return config.SCHEMA_CORE
    if tabela in ('responsaveis', 'ferias', 'times', 'responsaveis_times'):
        return config.SCHEMA_RH
    if tabela in ('projetos', 'tarefas', 'kanban_colunas', 'tarefa_atividades', 'projeto_configuracoes',
                  'epicos', 'features', 'historias', 'tarefas_hierarquicas', 'subtarefas',
                  'planilha_colunas_config', 'planilha_campos_custom', 'planilha_epicos', 'planilha_valores_custom'):
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


def _criar_tabela_se_nao_existe(cur, tabela, ddl):
    """Cria uma tabela se ela não existir."""
    if not _tabela_existe(cur, tabela):
        schema = _schema_de_tabela(tabela)
        cur.execute(f"CREATE TABLE IF NOT EXISTS {schema}.{tabela} ({ddl});")
        print(f"[MIGRAÇÃO] Tabela '{schema}.{tabela}' criada.")
        return True
    return False


def _tabela_existe(cur, tabela):
    """Verifica se uma tabela existe no schema do domínio correspondente."""
    schema = _schema_de_tabela(tabela)
    cur.execute("SELECT to_regclass(%s)", (f"{schema}.{tabela}",))
    return cur.fetchone()[0] is not None


def _garantir_schemas(cur):
    """
    Garante que os schemas por domínio existam antes de qualquer migração.
    """
    for schema in {config.SCHEMA_CORE, config.SCHEMA_RH, config.SCHEMA_PROJETO, config.SCHEMA_CONFIG}:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")

def _migrar_para_work_items(cur):
    """
    Migração 015: Migra os dados da hierarquia de 5 tabelas (epicos, features, etc.)
    para a nova estrutura genérica `projeto.work_items`.
    """
    if not _tabela_existe(cur, 'work_items'):
        return
    # 1. Verificar se a migração já foi executada ou se é necessária
    cur.execute("SELECT 1 FROM projeto.work_items LIMIT 1")
    if cur.fetchone() is not None:
        return # Já migrado

    if not _tabela_existe(cur, 'epicos'):
        return # Nenhuma hierarquia para migrar

    print("[MIGRAÇÃO 015] Iniciando migração para a estrutura Work Items...")

    # 2. Obter todos os projetos
    cur.execute("SELECT id, empresa_id FROM projeto.projetos")
    projects = cur.fetchall()
    if not projects:
        print("[MIGRAÇÃO 015] Nenhum projeto encontrado.")
        return

    for proj in projects:
        project_id = proj[0]
        empresa_id = proj[1]
        if not empresa_id:
            print(f"  - [AVISO] Projeto '{project_id}' sem empresa associada. Ignorando migração para este projeto.")
            continue
        
        # Extrai um prefixo do ID do projeto (ex: 'my-project' -> 'MYP')
        prefix = ''.join(part[0] for part in project_id.upper().replace('_', '-').split('-') if part)[:3]
        
        print(f"  - Processando projeto: {project_id} (Prefixo: {prefix})")

        # 3. Criar Work Item Types padrão para o projeto
        type_map = {}
        cur.execute("INSERT INTO projeto.work_item_types (projeto_id, nome, icone, cor) VALUES (%s, 'Epic', 'fa-star', '#9333ea') RETURNING id", (project_id,))
        type_map['epic'] = cur.fetchone()[0]
        cur.execute("INSERT INTO projeto.work_item_types (projeto_id, nome, icone, cor, parent_type_id) VALUES (%s, 'Feature', 'fa-flag', '#d97706', %s) RETURNING id", (project_id, type_map['epic']))
        type_map['feature'] = cur.fetchone()[0]
        cur.execute("INSERT INTO projeto.work_item_types (projeto_id, nome, icone, cor, parent_type_id) VALUES (%s, 'Story', 'fa-book-open', '#2563eb', %s) RETURNING id", (project_id, type_map['feature']))
        type_map['story'] = cur.fetchone()[0]
        cur.execute("INSERT INTO projeto.work_item_types (projeto_id, nome, icone, cor, parent_type_id) VALUES (%s, 'Task', 'fa-check-square', '#16a34a', %s) RETURNING id", (project_id, type_map['story']))
        type_map['task'] = cur.fetchone()[0]
        cur.execute("INSERT INTO projeto.work_item_types (projeto_id, nome, icone, cor, parent_type_id) VALUES (%s, 'Subtask', 'fa-tasks', '#64748b', %s) RETURNING id", (project_id, type_map['task']))
        type_map['subtask'] = cur.fetchone()[0]

        # 4. Migrar dados, tabela por tabela
        project_seq_counter = 1

        # Epics
        cur.execute("SELECT * FROM projeto.epicos WHERE projeto_id = %s", (project_id,))
        for item in cur.fetchall():
            chave = f"{prefix}-{project_seq_counter}"
            cur.execute("""
                INSERT INTO projeto.work_items (id, empresa_id, projeto_id, chave, type_id, titulo, descricao, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['id'], empresa_id, project_id, chave, type_map['epic'], item['titulo'], item['descricao'], item['criado_em'], item['criado_em']))
            project_seq_counter += 1

        # Features
        cur.execute("SELECT f.* FROM projeto.features f JOIN projeto.epicos e ON f.epico_id = e.id WHERE e.projeto_id = %s", (project_id,))
        for item in cur.fetchall():
            chave = f"{prefix}-{project_seq_counter}"
            cur.execute("""
                INSERT INTO projeto.work_items (id, empresa_id, projeto_id, chave, type_id, parent_id, titulo, descricao, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['id'], empresa_id, project_id, chave, type_map['feature'], item['epico_id'], item['titulo'], item['descricao'], item['criado_em'], item['criado_em']))
            project_seq_counter += 1

        # Stories
        cur.execute("SELECT h.* FROM projeto.historias h JOIN projeto.epicos e ON h.epico_id = e.id WHERE e.projeto_id = %s", (project_id,))
        for item in cur.fetchall():
            chave = f"{prefix}-{project_seq_counter}"
            cur.execute("""
                INSERT INTO projeto.work_items (id, empresa_id, projeto_id, chave, type_id, parent_id, titulo, descricao, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['id'], empresa_id, project_id, chave, type_map['story'], item['feature_id'], item['titulo'], item['descricao'], item['criado_em'], item['criado_em']))
            project_seq_counter += 1

        # Tarefas Hierárquicas
        cur.execute("SELECT t.* FROM projeto.tarefas_hierarquicas t JOIN projeto.epicos e ON t.epico_id = e.id WHERE e.projeto_id = %s", (project_id,))
        for item in cur.fetchall():
            chave = f"{prefix}-{project_seq_counter}"
            parent_id = item['historia_id'] if not item['is_extraordinaria'] else item['epico_id']
            cur.execute("""
                INSERT INTO projeto.work_items (id, empresa_id, projeto_id, chave, type_id, parent_id, titulo, descricao, responsavel_id, data_inicio, data_fim, data_vencimento, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['id'], empresa_id, project_id, chave, type_map['task'], parent_id, item['titulo'], item['descricao'], item['responsavel_id'], item['inicio'], item['fim'], item['baseline_fim'], item['criado_em'], item['criado_em']))
            project_seq_counter += 1

        # Subtarefas
        cur.execute("SELECT s.* FROM projeto.subtarefas s JOIN projeto.epicos e ON s.epico_id = e.id WHERE e.projeto_id = %s", (project_id,))
        for item in cur.fetchall():
            chave = f"{prefix}-{project_seq_counter}"
            cur.execute("""
                INSERT INTO projeto.work_items (id, empresa_id, projeto_id, chave, type_id, parent_id, titulo, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['id'], empresa_id, project_id, chave, type_map['subtask'], item['tarefa_id'], item['titulo'], item['criado_em'], item['criado_em']))
            project_seq_counter += 1

    print("[MIGRAÇÃO 015] Migração para Work Items concluída com sucesso.")

def _migrar_hierarquia_legado(cur):
    """
    Migração 014: Redistribui os dados da antiga tabela única 'projeto.tarefas'
    para a nova hierarquia em 5 tabelas (epicos, features, historias,
    tarefas_hierarquicas, subtarefas), preservando as relações pai-filho.

    Lógica:
      - tipo 'epic'    -> projeto.epicos
      - tipo 'feature' -> projeto.features
      - tipo 'story'   -> projeto.historias
      - tipo 'task'    -> projeto.tarefas_hierarquicas (historia_id = pai)
      - tipo 'subtask' -> projeto.subtarefas (tarefa_id = pai)
      - tarefas sem história pai e sem tipo 'subtask' -> tarefa extraordinária
    """
    # Verifica se a tabela legada existe e se já migramos (evita reprocessamento)
    if not _tabela_existe(cur, 'tarefas'):
        return
    cur.execute("SELECT 1 FROM projeto.subtarefas LIMIT 1")
    if cur.fetchone() is not None:
        return  # já migrado

    print("[MIGRAÇÃO 014] Iniciando migração da hierarquia legada...")

    # Garante pelo menos uma empresa default para vincular os dados antigos
    cur.execute("SELECT id FROM core.empresas ORDER BY criado_em LIMIT 1")
    row = cur.fetchone()
    if row is None:
        cur.execute("""
            INSERT INTO core.empresas (nome, cnpj) VALUES ('Empresa Padrão', NULL) RETURNING id
        """)
        empresa_id = cur.fetchone()[0]
    else:
        empresa_id = row[0]

    # Carrega todas as tarefas legadas ordenadas por id (para processar pais antes de filhos)
    cur.execute("""
        SELECT pk_id, id, projeto_id, tarefa, subtarefa, descricao, dias, predecessora_id,
               conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim,
               kanban_coluna_id, parent_id, tipo, criterios_aceite, sprint, planejado
        FROM projeto.tarefas
        ORDER BY id
    """)
    tarefas = cur.fetchall()

# Mapeia tipo -> nível hierárquico
    tipo_nivel = {'epic': 1, 'feature': 2, 'story': 3, 'task': 4, 'subtask': 5}

    # Estruturas de acumulação
    epicos = {}       # id_display -> (uuid, projeto_id)
    features = {}     # id_display -> (uuid, epico_uuid)
    historias = {}    # id_display -> (uuid, feature_uuid, epico_uuid)
    tarefas_hie = {}  # id_display -> (uuid, historia_uuid, epico_uuid, is_extra)
    subtarefas = {}   # id_display -> uuid
    projetos = {}     # projeto_id -> empresa_id

    # Garante que todos os projetos existam (caso não tenham empresa definida)
    cur.execute("SELECT id, empresa_id FROM projeto.projetos")
    projetos_existentes = {r[0]: r[1] for r in cur.fetchall()}

    for t in tarefas:
        pk_id, t_id, projeto_id, nome, subtarefa, descricao, dias, predecessora, \
            conclusao, responsavel, bl_inicio, bl_fim, inicio, fim, kanban_col, \
            parent_id, tipo, criterios, sprint, planejado = t

        titulo = nome or subtarefa or f'Tarefa {t_id}'
        tipo_atual = tipo or 'task'
        nivel = tipo_nivel.get(tipo_atual, 4)

        # Projeto -> empresa
        if projeto_id not in projetos_existentes:
            # Cria o projeto sem empresa específica (usa default)
            cur.execute("""
                INSERT INTO projeto.projetos (id, nome, empresa_id)
                VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING
            """, (projeto_id, projeto_id, empresa_id))
            projetos_existentes[projeto_id] = empresa_id
        emp_do_projeto = projetos_existentes.get(projeto_id) or empresa_id

        # Localiza o pai resolvido (se houver)
        pai_uuid = None
        if parent_id is not None:
            pid_display = str(parent_id)
            pai_uuid = (epicos.get(pid_display) or features.get(pid_display)
                        or historias.get(pid_display) or tarefas_hie.get(pid_display)
                        or subtarefas.get(pid_display))
            if isinstance(pai_uuid, tuple):
                pai_uuid = pai_uuid[0]

        # Insere conforme o nível
        if tipo_atual == 'epic':
            cur.execute("""
                INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (emp_do_projeto, projeto_id, titulo, descricao))
            novo_uuid = cur.fetchone()[0]
            epicos[str(t_id)] = (novo_uuid, projeto_id)

        elif tipo_atual == 'feature':
            epico_uuid = _extrair_uuid(epicos, pai_uuid)
            if epico_uuid is None:
                # Feature sem épico: cria um épico padrão
                cur.execute("""
                    INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (emp_do_projeto, projeto_id, f'Épico do projeto {projeto_id}', None))
                epico_uuid = cur.fetchone()[0]
                epicos[str(t_id)] = (epico_uuid, projeto_id)
            cur.execute("""
                INSERT INTO projeto.features (empresa_id, epico_id, titulo, descricao)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (emp_do_projeto, epico_uuid, titulo, descricao))
            novo_uuid = cur.fetchone()[0]
            features[str(t_id)] = (novo_uuid, epico_uuid)

        elif tipo_atual == 'story':
            feat_uuid = _extrair_uuid(features, pai_uuid)
            epico_uuid = None
            if feat_uuid:
                # Obtém o epico da feature
                for k, (f_uuid, e_uuid) in features.items():
                    if f_uuid == feat_uuid:
                        epico_uuid = e_uuid
                        break
            if epico_uuid is None:
                # Cria feature e épico padrão
                cur.execute("""
                    INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (emp_do_projeto, projeto_id, f'Épico do projeto {projeto_id}', None))
                epico_uuid = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO projeto.features (empresa_id, epico_id, titulo, descricao)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (emp_do_projeto, epico_uuid, f'Feature do projeto {projeto_id}', None))
                feat_uuid = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO projeto.historias (empresa_id, epico_id, feature_id, titulo, descricao)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (emp_do_projeto, epico_uuid, feat_uuid, titulo, descricao))
            novo_uuid = cur.fetchone()[0]
            historias[str(t_id)] = (novo_uuid, feat_uuid, epico_uuid)

        elif tipo_atual == 'subtask':
            # Subtarefa pertence a uma tarefa
            tarefa_uuid = _extrair_uuid(tarefas_hie, pai_uuid)
            if tarefa_uuid is None:
                # Órfã: cria uma tarefa extraordinária padrão
                cur.execute("""
                    INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (emp_do_projeto, projeto_id, f'Épico do projeto {projeto_id}', None))
                epico_uuid = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO projeto.tarefas_hierarquicas
                        (empresa_id, epico_id, historia_id, is_extraordinaria, titulo, descricao)
                    VALUES (%s, %s, NULL, TRUE, %s, %s) RETURNING id
                """, (emp_do_projeto, epico_uuid, f'Tarefa Extraordinária do projeto {projeto_id}', None))
                tarefa_uuid = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO projeto.subtarefas (empresa_id, epico_id, tarefa_id, titulo, concluida)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (emp_do_projeto, _epico_de_tarefa(tarefas_hie, tarefa_uuid), tarefa_uuid, titulo,
                  (conclusao or 0) >= 100))
            novo_uuid = cur.fetchone()[0]
            subtarefas[str(t_id)] = novo_uuid

        else:
            # 'task' -> projeto.tarefas_hierarquicas
            historia_uuid = _extrair_uuid(historias, pai_uuid)
            epico_uuid = None
            is_extra = False
            if historia_uuid:
                for k, (h_uuid, f_uuid, e_uuid) in historias.items():
                    if h_uuid == historia_uuid:
                        epico_uuid = e_uuid
                        break
            if epico_uuid is None:
                # Tarefa sem história: cria um épico padrão e marca como extraordinária
                cur.execute("""
                    INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (emp_do_projeto, projeto_id, f'Épico do projeto {projeto_id}', None))
                epico_uuid = cur.fetchone()[0]
                is_extra = True

            cur.execute("""
                INSERT INTO projeto.tarefas_hierarquicas
                    (empresa_id, epico_id, historia_id, is_extraordinaria, titulo, descricao,
                     dias, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim,
                     kanban_coluna_id, sprint, planejado, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (emp_do_projeto, epico_uuid, historia_uuid, is_extra, titulo, descricao,
                  dias, conclusao, responsavel, bl_inicio, bl_fim, inicio, fim,
                  kanban_col, sprint, planejado, 'A_FAZER'))
            novo_uuid = cur.fetchone()[0]
            tarefas_hie[str(t_id)] = (novo_uuid, historia_uuid, epico_uuid, is_extra)

    print("[MIGRAÇÃO 014] Hierarquia legada migrada com sucesso.")


def _extrair_uuid(estrutura, pai_uuid):
    """Dada uma estrutura de mapeamento, retorna o UUID do pai informado."""
    if pai_uuid is None:
        resultado = next(iter(estrutura.values()), None)
        if resultado:
            return (resultado[0] if isinstance(resultado, tuple) else resultado)
        return None
    return pai_uuid


def _epico_de_tarefa(tarefas_hie, tarefa_uuid):
    """Retorna o epico_id de uma tarefa hierárquica pelo seu UUID."""
    for k, v in tarefas_hie.items():
        if isinstance(v, tuple) and v[0] == tarefa_uuid:
            return v[2]
        if not isinstance(v, tuple) and v == tarefa_uuid:
            return v
    return None


def _aplicar_rls(cur):
    """
    Migração 019: habilita RLS (Row-Level Security) em todas as tabelas
    multi-tenant e cria políticas de isolamento por `empresa_id`.

    Retorna o número de "passos aplicados" para contabilizar como migrações.
    Como a operação é idempotente, usamos uma flag em config.configuracoes
    para evitar recriar policies repetidamente.
    """
    cur.execute("SELECT to_regclass('config.configuracoes')")
    if cur.fetchone()[0] is None:
        return 0

    cur.execute("""
        SELECT valor FROM config.configuracoes WHERE chave = 'rls_aplicado_v1'
    """)
    row = cur.fetchone()
    if row and row[0] == 'true':
        return 0

    # Tabelas com coluna empresa_id direta (politicas simples)
    tabelas_diretas = [
        ('rh', 'times'),
        ('rh', 'responsaveis'),
        ('projeto', 'projetos'),
        ('projeto', 'epicos'),
        ('projeto', 'features'),
        ('projeto', 'historias'),
        ('projeto', 'tarefas_hierarquicas'),
        ('projeto', 'subtarefas'),
        ('projeto', 'work_items'),
    ]
    for schema, tabela in tabelas_diretas:
        cur.execute(f"""
            DO $$ BEGIN
                ALTER TABLE {schema}.{tabela} ENABLE ROW LEVEL SECURITY;
            EXCEPTION WHEN OTHERS THEN NULL; END $$;
        """)
        policy_name = f"{tabela}_isolamento"
        cur.execute(f"""
            DROP POLICY IF EXISTS {policy_name} ON {schema}.{tabela};
        """)
        cur.execute(f"""
            CREATE POLICY {policy_name} ON {schema}.{tabela}
            FOR ALL
            USING (
                empresa_id IS NULL
                OR current_setting('app.current_empresa_id', true) IS NULL
                OR empresa_id = current_setting('app.current_empresa_id', true)::uuid
            )
            WITH CHECK (
                empresa_id IS NULL
                OR current_setting('app.current_empresa_id', true) IS NULL
                OR empresa_id = current_setting('app.current_empresa_id', true)::uuid
            );
        """)

    # Tabelas core.empresas (isolamento pelo próprio id)
    cur.execute("DO $$ BEGIN ALTER TABLE core.empresas ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN OTHERS THEN NULL; END $$;")
    cur.execute("DROP POLICY IF EXISTS empresas_isolamento ON core.empresas;")
    cur.execute("""
        CREATE POLICY empresas_isolamento ON core.empresas
        FOR ALL
        USING (
            current_setting('app.current_empresa_id', true) IS NULL
            OR id = current_setting('app.current_empresa_id', true)::uuid
        )
        WITH CHECK (
            current_setting('app.current_empresa_id', true) IS NULL
            OR id = current_setting('app.current_empresa_id', true)::uuid
        );
    """)

    # Tabelas com associação indireta (checam via FK)
    associativas = [
        ('rh', 'ferias', 'responsavel_id', 'rh', 'responsaveis'),
        ('rh', 'responsaveis_times', 'responsavel_id', 'rh', 'responsaveis'),
        ('projeto', 'work_item_types', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'work_item_atividades', 'work_item_id', 'projeto', 'work_items'),
        ('projeto', 'custom_fields', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'custom_field_values', 'work_item_id', 'projeto', 'work_items'),
        ('projeto', 'kanban_colunas', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'projeto_configuracoes', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'planilha_colunas_config', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'planilha_campos_custom', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'planilha_epicos', 'projeto_id', 'projeto', 'projetos'),
        ('projeto', 'tarefas', 'projeto_id', 'projeto', 'projetos'),
    ]
    for (schema, tabela, fk_col, ref_schema, ref_tabela) in associativas:
        cur.execute(f"DO $$ BEGIN ALTER TABLE {schema}.{tabela} ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN OTHERS THEN NULL; END $$;")
        policy_name = f"{tabela}_isolamento"
        cur.execute(f"DROP POLICY IF EXISTS {policy_name} ON {schema}.{tabela};")
        cur.execute(f"""
            CREATE POLICY {policy_name} ON {schema}.{tabela}
            FOR ALL
            USING (
                current_setting('app.current_empresa_id', true) IS NULL
                OR EXISTS (
                    SELECT 1 FROM {ref_schema}.{ref_tabela} ref
                    WHERE ref.id = {schema}.{tabela}.{fk_col}
                      AND (
                          ref.empresa_id IS NULL
                          OR ref.empresa_id = current_setting('app.current_empresa_id', true)::uuid
                      )
                )
            );
        """)

    # Tabelas públicas (config)
    for schema, tabela in [('config', 'configuracoes'), ('config', 'feriados_customizados')]:
        cur.execute(f"DO $$ BEGIN ALTER TABLE {schema}.{tabela} ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN OTHERS THEN NULL; END $$;")
        cur.execute(f"DROP POLICY IF EXISTS {tabela}_publicas ON {schema}.{tabela};")
        cur.execute(f"""
            CREATE POLICY {tabela}_publicas ON {schema}.{tabela}
            FOR ALL USING (true) WITH CHECK (true);
        """)

    # Marca flag para não reexecutar
    cur.execute("""
        INSERT INTO config.configuracoes (chave, valor)
        VALUES ('rls_aplicado_v1', 'true')
        ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor;
    """)

    print("[MIGRAÇÃO 019] RLS / políticas por empresa_id aplicadas com sucesso.")
    return 1


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

        # ---------------------------------------------------------------
        # Migração 012: Tabela de Perfis (alçadas) + coluna 'perfil' em responsaveis
        # ---------------------------------------------------------------
        if not _tabela_existe(cur, 'perfis'):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rh.perfis (
                    id VARCHAR(50) PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    descricao TEXT
                )
            """)
            print("[MIGRAÇÃO] Tabela 'rh.perfis' criada.")
            migracoes_aplicadas += 1

        # Seed dos perfis (idempotente)
        cur.execute("""
            INSERT INTO rh.perfis (id, nome, descricao) VALUES
                ('product_manager', 'Gerente de Produto', 'Aprova transições envolvendo Épicos (Feature ↔ Épico).'),
                ('scrum_master', 'Gestor do Projeto', 'Gestão do fluxo Scrum; coordena o time e o andamento das entregas.'),
                ('product_owner', 'Dono do Produto', 'Aprova transições envolvendo Features (Tarefa/História ↔ Feature).'),
                ('executor', 'Executor', 'Decide livremente em Subtarefa ↔ Tarefa.')
            ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, descricao = EXCLUDED.descricao
        """)

        # Coluna perfil em rh.responsaveis
        if not _coluna_existe(cur, 'responsaveis', 'perfil'):
            # Adiciona sem FK primeiro para evitar falha se a tabela não existia
            cur.execute("ALTER TABLE rh.responsaveis ADD COLUMN perfil VARCHAR(50) DEFAULT 'executor';")
            print("[MIGRAÇÃO] Coluna 'perfil' adicionada à tabela 'rh.responsaveis'.")
            migracoes_aplicadas += 1

        # Garante a FK de perfil (idempotente) - se a coluna foi criada acima ou já existia
        cur.execute("""
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'rh' AND constraint_name = 'responsaveis_perfil_fkey'
        """)
        if cur.fetchone() is None:
            cur.execute("""
                ALTER TABLE rh.responsaveis
                ADD CONSTRAINT responsaveis_perfil_fkey
                FOREIGN KEY (perfil) REFERENCES rh.perfis(id)
            """)
            print("[MIGRAÇÃO] FK responsaveis.perfil -> rh.perfis criada.")

        # ---------------------------------------------------------------
        # Migração 013: Estrutura multi-tenant (empresas) e hierarquia em 5 tabelas
        # ---------------------------------------------------------------
        # Tabela de empresas (tenant)
        if not _tabela_existe(cur, 'empresas'):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS core.empresas (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    nome VARCHAR(255) NOT NULL,
                    cnpj VARCHAR(20),
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[MIGRAÇÃO] Tabela 'core.empresas' criada.")
            migracoes_aplicadas += 1

        # Coluna empresa_id nas tabelas existentes
        for tabela, tipo in [
            ('projetos', 'UUID'),
            ('responsaveis', 'UUID'),
            ('times', 'UUID'),
        ]:
            schema = _schema_de_tabela(tabela)
            if not _coluna_existe(cur, tabela, 'empresa_id'):
                cur.execute(f"ALTER TABLE {schema}.{tabela} ADD COLUMN empresa_id {tipo};")
                print(f"[MIGRAÇÃO] Coluna 'empresa_id' adicionada à tabela '{schema}.{tabela}'.")
                migracoes_aplicadas += 1

        # Tabelas hierárquicas (5 níveis)
        hierarquia = {
            'epicos': """
                CREATE TABLE IF NOT EXISTS projeto.epicos (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
                    projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
                    titulo VARCHAR(255) NOT NULL,
                    descricao TEXT,
                    status VARCHAR(50) DEFAULT 'PLANEJADO',
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'features': """
                CREATE TABLE IF NOT EXISTS projeto.features (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
                    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
                    titulo VARCHAR(255) NOT NULL,
                    descricao TEXT,
                    status VARCHAR(50) DEFAULT 'EM_ANDAMENTO',
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'historias': """
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
                )
            """,
            'tarefas_hierarquicas': """
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
                    kanban_coluna_id VARCHAR(255) DEFAULT 'backlog',
                    sprint VARCHAR(100),
                    planejado BOOLEAN DEFAULT FALSE,
                    predecessora_id UUID,
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT chk_tarefa_extraordinaria CHECK (
                        (historia_id IS NOT NULL AND is_extraordinaria = FALSE) OR
                        (historia_id IS NULL AND is_extraordinaria = TRUE)
                    )
                )
            """,
            'subtarefas': """
                CREATE TABLE IF NOT EXISTS projeto.subtarefas (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    empresa_id UUID NOT NULL REFERENCES core.empresas(id) ON DELETE CASCADE,
                    epico_id UUID NOT NULL REFERENCES projeto.epicos(id) ON DELETE CASCADE,
                    tarefa_id UUID NOT NULL REFERENCES projeto.tarefas_hierarquicas(id) ON DELETE CASCADE,
                    titulo VARCHAR(255) NOT NULL,
                    concluida BOOLEAN DEFAULT FALSE,
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """,
        }
        for nome, ddl in hierarquia.items():
            if not _tabela_existe(cur, nome):
                cur.execute(ddl)
                print(f"[MIGRAÇÃO] Tabela 'projeto.{nome}' criada.")
                migracoes_aplicadas += 1

        # Migração 016: tarefas da estrutura hierárquica devem nascer em uma
        # coluna visível do Kanban; itens antigos sem coluna voltam ao Backlog.
        cur.execute("""
            ALTER TABLE projeto.tarefas_hierarquicas
            ALTER COLUMN kanban_coluna_id SET DEFAULT 'backlog'
        """)
        cur.execute("""
            UPDATE projeto.tarefas_hierarquicas
            SET kanban_coluna_id = 'backlog'
            WHERE kanban_coluna_id IS NULL
        """)

        # Migração 017: uma tarefa vinculada a uma sprint participa da
        # execução. Os registros legados entram pela coluna Iniciar, sem
        # alterar itens que já avançaram para outra coluna do Kanban.
        for tabela in ('tarefas', 'tarefas_hierarquicas'):
            cur.execute(f"""
                UPDATE projeto.{tabela}
                SET planejado = TRUE,
                    kanban_coluna_id = CASE
                        WHEN kanban_coluna_id IS NULL OR kanban_coluna_id = 'backlog' THEN 'iniciar'
                        ELSE kanban_coluna_id
                    END
                WHERE NULLIF(BTRIM(sprint), '') IS NOT NULL
            """)

        # FK de empresa_id nas tabelas existentes (idempotente)
        for tabela in ['projetos', 'responsaveis', 'times']:
            schema = _schema_de_tabela(tabela)
            fk_name = f"{tabela}_empresa_id_fkey"
            cur.execute("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_schema = %s AND constraint_name = %s
            """, (schema, fk_name))
            if cur.fetchone() is None:
                cur.execute(f"""
                    ALTER TABLE {schema}.{tabela}
                    ADD CONSTRAINT {fk_name}
                    FOREIGN KEY (empresa_id) REFERENCES core.empresas(id) ON DELETE CASCADE
                """)
                print(f"[MIGRAÇÃO] FK {schema}.{tabela}.empresa_id -> core.empresas criada.")

        # ---------------------------------------------------------------
        # Migração 014: Migração automática de dados (tarefas antigas -> nova hierarquia)
        # ---------------------------------------------------------------
        _migrar_hierarquia_legado(cur)

        # ---------------------------------------------------------------
        # Migração 015: Migração para o novo Work Item Engine
        # ---------------------------------------------------------------
        _migrar_para_work_items(cur)

        # ---------------------------------------------------------------
        # Migração 018: Criar tabelas de configuração da planilha
        # ---------------------------------------------------------------
        if _criar_tabela_se_nao_existe(cur, 'planilha_colunas_config', """
            id SERIAL PRIMARY KEY,
            projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
            coluna_id VARCHAR(100) NOT NULL,
            visivel BOOLEAN DEFAULT TRUE,
            ordem INTEGER DEFAULT 0,
            UNIQUE(projeto_id, coluna_id)
        """):
            migracoes_aplicadas += 1

        if _criar_tabela_se_nao_existe(cur, 'planilha_campos_custom', """
            id SERIAL PRIMARY KEY,
            projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('texto', 'data', 'numerico', 'texto_longo')),
            ordem INTEGER DEFAULT 0,
            UNIQUE(projeto_id, nome)
        """):
            migracoes_aplicadas += 1

        if _criar_tabela_se_nao_existe(cur, 'planilha_epicos', """
            projeto_id VARCHAR(255) NOT NULL REFERENCES projeto.projetos(id) ON DELETE CASCADE,
            tarefa_pk_id INTEGER NOT NULL REFERENCES projeto.tarefas(pk_id) ON DELETE CASCADE,
            PRIMARY KEY (projeto_id, tarefa_pk_id)
        """):
            migracoes_aplicadas += 1

        if _criar_tabela_se_nao_existe(cur, 'planilha_valores_custom', """
            tarefa_pk_id INTEGER NOT NULL REFERENCES projeto.tarefas(pk_id) ON DELETE CASCADE,
            campo_id INTEGER NOT NULL REFERENCES projeto.planilha_campos_custom(id) ON DELETE CASCADE,
            valor_texto TEXT,
            valor_data DATE,
            valor_numerico NUMERIC,
            PRIMARY KEY (tarefa_pk_id, campo_id)
        """):
            migracoes_aplicadas += 1

        # ---------------------------------------------------------------
        # Migração 019: RLS (Row-Level Security) por empresa_id
        # ---------------------------------------------------------------
        migracoes_aplicadas += _aplicar_rls(cur)

    db.commit()

    if migracoes_aplicadas > 0:
        print(f"[MIGRAÇÕES] {migracoes_aplicadas} migração(ões) aplicada(s) com sucesso.")
    else:
        print("[MIGRAÇÕES] Nenhuma migração necessária. Schema atualizado.")
