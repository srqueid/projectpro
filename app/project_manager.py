# app/project_manager.py
import os
import json
import uuid
import psycopg2
import psycopg2.extras
from . import config, utils, database

# =============================================================================
# GERENCIAMENTO DE RESPONSÁVEIS (COM BANCO DE DADOS)
# =============================================================================
def carregar_responsaveis():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM responsaveis ORDER BY nome")
        responsaveis = [dict(row) for row in cur.fetchall()]
        for r in responsaveis:
            cur.execute("SELECT inicio, fim FROM ferias WHERE responsavel_id = %s", (r['id'],))
            r['ferias'] = [dict(row) for row in cur.fetchall()]
    return responsaveis

def adicionar_responsavel(dados):
    db = database.get_db()
    horas_semanais = dados.get('horas_semanais') or None
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO responsaveis (nome, email, modelo_trabalho, horas_semanais) VALUES (%s, %s, %s, %s) RETURNING id",
            (dados['nome'], dados['email'], dados['modelo_trabalho'], horas_semanais)
        )
        responsavel_id = cur.fetchone()[0]
        for periodo in dados.get('ferias', []):
            cur.execute("INSERT INTO ferias (responsavel_id, inicio, fim) VALUES (%s, %s, %s)", (responsavel_id, periodo['inicio'], periodo['fim']))
    db.commit()

def editar_responsavel(id, dados):
    db = database.get_db()
    horas_semanais = dados.get('horas_semanais') or None
    with db.cursor() as cur:
        cur.execute(
            "UPDATE responsaveis SET nome = %s, email = %s, modelo_trabalho = %s, horas_semanais = %s WHERE id = %s",
            (dados['nome'], dados['email'], dados['modelo_trabalho'], horas_semanais, id)
        )
        cur.execute("DELETE FROM ferias WHERE responsavel_id = %s", (id,))
        for periodo in dados.get('ferias', []):
            cur.execute("INSERT INTO ferias (responsavel_id, inicio, fim) VALUES (%s, %s, %s)", (id, periodo['inicio'], periodo['fim']))
    db.commit()

def excluir_responsavel(id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM responsaveis WHERE id = %s", (id,))
    db.commit()

# =============================================================================
# GERENCIAMENTO DE PROJETOS E TAREFAS (COM BANCO DE DADOS)
# =============================================================================
def carregar_projetos():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, nome, descricao FROM projetos ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def carregar_projeto_por_id(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projetos WHERE id = %s", (project_id,))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def criar_projeto_db(project_id, nome, descricao=''):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO projetos (id, nome, descricao) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING", (project_id, nome, descricao))
    db.commit()

def atualizar_descricao_projeto(project_id, descricao):
    """Atualiza a descrição do projeto."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE projetos SET descricao = %s WHERE id = %s", (descricao, project_id))
    db.commit()

def excluir_projeto_db(project_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projetos WHERE id = %s", (project_id,))
    db.commit()

def carregar_tarefas(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM tarefas WHERE projeto_id = %s ORDER BY id", (project_id,))
        return [dict(row) for row in cur.fetchall()]

def _validar_datas_tarefa(t):
    """
    Valida que as datas de execução e baseline são consistentes.
    - data de fim não pode ser anterior à data de início
    - data de baseline_fim não pode ser anterior à baseline_inicio
    Retorna uma tupla (valido, mensagem_erro).
    """
    inicio = t.get('inicio')
    fim = t.get('fim')
    if inicio and fim and fim < inicio:
        nome = t.get('tarefa') or t.get('subtarefa') or f"ID {t.get('id')}"
        return False, f"Tarefa '{nome}': data de fim ({fim}) é anterior à data de início ({inicio})."
    
    # Validar baseline
    bl_inicio = t.get('baseline_inicio')
    bl_fim = t.get('baseline_fim')
    if bl_inicio and bl_fim and bl_fim < bl_inicio:
        nome = t.get('tarefa') or t.get('subtarefa') or f"ID {t.get('id')}"
        return False, f"Tarefa '{nome}': baseline de fim ({bl_fim}) é anterior à baseline de início ({bl_inicio})."
    
    return True, None


def _validar_circular_reference(tarefas):
    """
    Valida que não existem referências circulares na hierarquia pai-filho.
    Exemplo inválido: A é pai de B, B é pai de A (ou A -> B -> C -> A).
    Levanta ValueError se encontrar ciclo.
    """
    # Construir mapa de adjacência
    adj = {}
    for t in tarefas:
        tid = str(t.get('id'))
        pid = t.get('parent_id')
        if pid is not None and str(pid).strip():
            pid_str = str(pid).strip()
            if tid not in adj:
                adj[tid] = []
            adj[tid].append(pid_str)

    # Detectar ciclo via DFS
    for node in adj:
        visited = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                nome = next((t.get('tarefa') or t.get('subtarefa') or f"ID {t.get('id')}" for t in tarefas if str(t.get('id')) == current), current)
                raise ValueError(f"Referência circular detectada na hierarquia envolvendo a tarefa '{nome}' (ID {current}).")
            visited.add(current)
            for neighbor in adj.get(current, []):
                stack.append(neighbor)
    return True


def salvar_tarefas(project_id, tarefas):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM tarefas WHERE projeto_id = %s", (project_id,))
        default_coluna_id = carregar_kanban_config(project_id)['colunas'][0]['coluna_id']
        for t in tarefas:
            # Validar datas
            valido, erro = _validar_datas_tarefa(t)
            if not valido:
                raise ValueError(erro)

            try:
                task_id = int(t['id']) if t.get('id') not in (None, '') else None
            except (ValueError, TypeError):
                task_id = None

            predecessora = t.get('predecessora')
            if predecessora == '' or predecessora is None:
                predecessora = None
            else:
                try:
                    predecessora = int(predecessora)
                except (ValueError, TypeError):
                    predecessora = None

            responsavel_id = t.get('responsavel_id')
            if responsavel_id == '' or responsavel_id is None:
                responsavel_id = None

            kanban_coluna_id = t.get('kanban_coluna_id') or default_coluna_id

            # Tratar parent_id
            parent_id = t.get('parent_id')
            if parent_id == '' or parent_id is None:
                parent_id = None
            else:
                try:
                    parent_id = int(parent_id)
                except (ValueError, TypeError):
                    parent_id = None

            print(f"Inserindo tarefa id={task_id} predecessor={predecessora} parent_id={parent_id} responsavel={responsavel_id}")
            cur.execute(
                """
                INSERT INTO tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, restricao_tipo, restricao_data, parent_id, tipo, criterios_aceite, sprint, planejado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (task_id, project_id, t.get('fase'), t.get('modulo'), t.get('tarefa'), t.get('subtarefa'), t.get('descricao'), int(t.get('dias') or 0), predecessora, int(t.get('conclusao') or 0), responsavel_id, t.get('baseline_inicio'), t.get('baseline_fim'), t.get('inicio'), t.get('fim'), kanban_coluna_id, t.get('restricao_tipo'), t.get('restricao_data'), parent_id, t.get('tipo') or 'task', t.get('criterios_aceite'), t.get('sprint'), t.get('planejado', False))
            )
    db.commit()

def salvar_tarefas_recalculadas(project_id, tarefas):
    """
    Salva apenas as datas e campos de restrição de uma lista de tarefas,
    otimizado para atualizações pós-recálculo.
    Agora atualiza baseline_inicio/baseline_fim (datas planejadas) em vez de inicio/fim (datas reais).
    """
    db = database.get_db()
    with db.cursor() as cur:
        for t in tarefas:
            cur.execute(
                "UPDATE tarefas SET baseline_inicio = %s, baseline_fim = %s, restricao_tipo = %s, restricao_data = %s WHERE projeto_id = %s AND id = %s",
                (t.get('baseline_inicio'), t.get('baseline_fim'), t.get('restricao_tipo'), t.get('restricao_data'), project_id, t['id'])
            )
    db.commit()

def recalcular_datas_cascata(tarefas):
    """
    Recalcula as datas planejadas (baseline_inicio/baseline_fim) em cascata.
    - Usa a data real (inicio) como ponto de partida, se existir
    - Considera predecessoras (usa o baseline_fim da predecessora)
    - Aplica restrições manuais (RN015)
    - Agrega datas das tarefas filhas nos pais: o pai começa no início da primeira filha
      e termina no fim da última filha
    - Escreve o resultado em baseline_inicio/baseline_fim (datas planejadas)
    """
    mapa_tarefas = {str(t['id']): t for t in tarefas}
    feriados_custom = carregar_feriados_custom()
    responsaveis = carregar_responsaveis()
    mapa_responsaveis = {r['id']: r for r in responsaveis}
    settings = carregar_settings()

    # Build parent-child relationships
    filhos_por_pai = {}
    for t in tarefas:
        pid = str(t.get('parent_id') or '').strip()
        if pid:
            if pid not in filhos_por_pai:
                filhos_por_pai[pid] = []
            filhos_por_pai[pid].append(t)

    alteracoes = True
    loops = 0
    while alteracoes and loops < 100:
        alteracoes = False
        loops += 1
        for t in tarefas:
            tid = str(t['id'])
            if int(t.get('conclusao', 0)) == 100: continue
            responsavel_nome = t.get('responsavel_id')
            ferias = mapa_responsaveis.get(responsavel_nome, {}).get('ferias', [])
            dias = int(t.get('dias') or 0)
            
            # Ponto de partida: usa a data planejada existente, ou a data real como fallback
            novo_inicio = utils.str_to_date(t.get('baseline_inicio') or t.get('inicio'))

            # RN015: Verificar se há restrição manual de data
            if t.get('restricao_tipo') == 'inicio_nao_antes_de' and t.get('restricao_data'):
                restricao_inicio = utils.str_to_date(t['restricao_data'])
                if not novo_inicio or novo_inicio < restricao_inicio:
                    novo_inicio = restricao_inicio

            # Se houver predecessora, a baseline_fim dela tem prioridade
            pred_id = str(t.get('predecessora_id') or t.get('predecessora') or '').lower().strip()
            if pred_id and pred_id in mapa_tarefas:
                # Usa a baseline_fim (planejada) da predecessora
                baseline_fim_pred = mapa_tarefas[pred_id].get('baseline_fim')
                if baseline_fim_pred:
                    novo_inicio_pred = utils.str_to_date(baseline_fim_pred)
                    if not novo_inicio or novo_inicio_pred > novo_inicio:
                        novo_inicio = novo_inicio_pred

            if novo_inicio:
                novo_fim = utils.date_to_str(utils.adicionar_dias_uteis(novo_inicio, dias, feriados_custom, ferias, settings.get('block_weekends', True)))
                novo_inicio_str = utils.date_to_str(novo_inicio)
                # Escreve em baseline_inicio/baseline_fim (datas planejadas)
                if t.get('baseline_inicio') != novo_inicio_str or t.get('baseline_fim') != novo_fim:
                    t['baseline_inicio'] = novo_inicio_str
                    t['baseline_fim'] = novo_fim
                    alteracoes = True

        # --- Aggregation step: parent dates are composed from children ---
        for t in tarefas:
            tid = str(t['id'])
            if tid in filhos_por_pai and len(filhos_por_pai[tid]) > 0:
                children = filhos_por_pai[tid]
                child_dates = []
                for c in children:
                    c_inicio = c.get('baseline_inicio') or c.get('inicio')
                    c_fim = c.get('baseline_fim') or c.get('fim')
                    if c_inicio:
                        child_dates.append((utils.str_to_date(c_inicio), utils.str_to_date(c_fim) if c_fim else None))
                
                if child_dates:
                    # Parent starts when the earliest child starts
                    earliest_start = min(d[0] for d in child_dates if d[0])
                    # Parent ends when the latest child ends
                    latest_end = max((d[1] for d in child_dates if d[1]), default=None)
                    
                    parent_inicio_str = utils.date_to_str(earliest_start) if earliest_start else t.get('baseline_inicio')
                    parent_fim_str = utils.date_to_str(latest_end) if latest_end else t.get('baseline_fim')
                    
                    if t.get('baseline_inicio') != parent_inicio_str or t.get('baseline_fim') != parent_fim_str:
                        t['baseline_inicio'] = parent_inicio_str
                        t['baseline_fim'] = parent_fim_str
                        alteracoes = True

    return tarefas

def calcular_stats(tarefas):
    total = len(tarefas)
    if total == 0: return {'total': 0, 'completed': 0, 'in_progress': 0, 'avg': 0}
    completed = sum(1 for t in tarefas if int(t.get('conclusao', 0) or 0) == 100)
    in_progress = sum(1 for t in tarefas if 0 < int(t.get('conclusao', 0) or 0) < 100)
    avg = int(sum(int(t.get('conclusao', 0) or 0) for t in tarefas) / total) if total > 0 else 0
    return {'total': total, 'completed': completed, 'in_progress': in_progress, 'avg': avg}

# =============================================================================
# (As funções abaixo ainda usam arquivos JSON e serão migradas depois)
# =============================================================================
def carregar_settings():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT valor FROM configuracoes WHERE chave = 'block_weekends'")
        row = cur.fetchone()
        return {"block_weekends": row['valor'] == 'true'} if row else {"block_weekends": True}

def salvar_settings(settings):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE configuracoes SET valor = %s WHERE chave = 'block_weekends'", (str(settings['block_weekends']).lower(),))
    db.commit()

def carregar_config_projeto(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT chave, valor FROM projeto_configuracoes WHERE projeto_id = %s", (project_id,))
        rows = cur.fetchall()
        config = {}
        for row in rows:
            config[row['chave']] = row['valor']
        return config

def salvar_config_projeto(project_id, chave, valor):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO projeto_configuracoes (projeto_id, chave, valor) VALUES (%s, %s, %s) ON CONFLICT (projeto_id, chave) DO UPDATE SET valor = EXCLUDED.valor", (project_id, chave, str(valor)))
    db.commit()

def carregar_feriados_custom():
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SELECT data FROM feriados_customizados")
        return {row[0].strftime('%Y-%m-%d') for row in cur.fetchall()}

def salvar_feriados_custom(lista_datas):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM feriados_customizados")
        for data in lista_datas:
            cur.execute("INSERT INTO feriados_customizados (data) VALUES (%s)", (data,))
    db.commit()

def carregar_kanban_config(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT coluna_id, nome, tipo, progresso_padrao, allow_back FROM kanban_colunas WHERE projeto_id = %s ORDER BY ordem", (project_id,))
        colunas = [dict(row) for row in cur.fetchall()]
        # Converte allow_back para booleano
        for col in colunas:
            col['allow_back'] = col.get('allow_back', True) if col.get('allow_back') is not None else True
        if not colunas:
            # Se não houver configuração, retorna um padrão e salva para o projeto
            default_config = {"colunas": [{"coluna_id": "backlog", "nome": "📋 Backlog", "tipo": "backlog", "progresso_padrao": 0, "allow_back": True}, {"coluna_id": "iniciar", "nome": "🚀 Iniciar", "tipo": "inicio", "progresso_padrao": 0, "allow_back": True}, {"coluna_id": "andamento", "nome": "⚙️ Em Andamento", "tipo": "meio", "progresso_padrao": 50, "allow_back": True}, {"coluna_id": "concluido", "nome": "✅ Concluído", "tipo": "fim", "progresso_padrao": 100, "allow_back": True}]}
            salvar_kanban_config(project_id, default_config)
            return default_config
        return {"colunas": colunas}

def salvar_kanban_config(project_id, config_data):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM kanban_colunas WHERE projeto_id = %s", (project_id,))
        for i, col in enumerate(config_data.get('colunas', [])):
            # Garante que o progresso seja um inteiro ou nulo
            progresso = col.get('progresso_padrao')
            progresso = int(progresso) if progresso is not None and str(progresso).isdigit() else None
            allow_back = col.get('allow_back', True)
            if isinstance(allow_back, str):
                allow_back = allow_back.lower() == 'true'
            cur.execute(
                "INSERT INTO kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem, progresso_padrao, allow_back) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (project_id, col['coluna_id'], col['nome'], col['tipo'], i, progresso, allow_back)
            )
    db.commit()

def carregar_times():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM times ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def associar_time_projeto(project_id, time_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("UPDATE projetos SET time_id = %s WHERE id = %s", (time_id if time_id else None, project_id))
    db.commit()

def replanejar_tarefa(project_id, card_id):
    """
    Replaneja uma tarefa que saiu da coluna 'Concluído':
    - Se 'manter_data': mantém a data de fim real, mas volta para backlog/iniciar
    - Se 'replanejar': limpa as datas reais (inicio/fim) e coloca no backlog para recalcular
    """
    db = database.get_db()
    from datetime import datetime
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            "UPDATE tarefas SET conclusao = 0, kanban_coluna_id = 'backlog', inicio = NULL, fim = NULL WHERE projeto_id = %s AND id = %s",
            (project_id, card_id)
        )
    db.commit()
    # Recalcula o projeto
    tarefas_atuais = carregar_tarefas(project_id)
    tarefas_recalculadas = recalcular_datas_cascata(tarefas_atuais)
    salvar_tarefas_recalculadas(project_id, tarefas_recalculadas)
    return True


def mover_card_kanban(project_id, card_id, coluna_destino_id, manter_data=False):
    db = database.get_db()
    from datetime import datetime
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Carrega a coluna de destino para obter seu tipo e progresso padrão
        cur.execute("SELECT tipo, progresso_padrao FROM kanban_colunas WHERE projeto_id = %s AND coluna_id = %s", (project_id, coluna_destino_id))
        col_dest = cur.fetchone()
        
        if not col_dest:
            # Se a coluna não for encontrada, apenas atualiza a coluna da tarefa sem outras ações.
            cur.execute("UPDATE tarefas SET kanban_coluna_id = %s WHERE projeto_id = %s AND id = %s", (coluna_destino_id, project_id, card_id))
            db.commit()
            return

        tipo_dest = col_dest['tipo']
        progresso_padrao = col_dest['progresso_padrao']

        # Carrega dados atuais da tarefa e da coluna de origem
        cur.execute("SELECT kanban_coluna_id, inicio FROM tarefas WHERE projeto_id = %s AND id = %s", (project_id, card_id))
        tarefa_atual = cur.fetchone()
        coluna_origem_id = tarefa_atual['kanban_coluna_id'] if tarefa_atual else None
        inicio_existente = tarefa_atual['inicio'] if tarefa_atual else None

        # Obtém o tipo da coluna de origem
        tipo_origem = None
        if coluna_origem_id:
            cur.execute("SELECT tipo FROM kanban_colunas WHERE projeto_id = %s AND coluna_id = %s", (project_id, coluna_origem_id))
            col_orig = cur.fetchone()
            if col_orig:
                tipo_origem = col_orig['tipo']

        update_fields = {"kanban_coluna_id": coluna_destino_id}

        # Se o card voltou para a coluna "Iniciar" (tipo 'inicio'), apaga as datas de início e fim
        if tipo_dest == 'inicio':
            update_fields['inicio'] = None
            update_fields['fim'] = None

        # Se o card saiu da coluna "Iniciar" (tipo 'inicio') e NÃO voltou para "Backlog" (tipo 'backlog'),
        # insere a data de início se ainda não existir
        if tipo_origem == 'inicio' and tipo_dest != 'backlog' and not inicio_existente:
            update_fields['inicio'] = datetime.now().strftime('%Y-%m-%d')

        # RN022: Se o trabalho começou (movido para uma coluna de "meio") e ainda não tem data de início
        if tipo_dest == 'meio' and 'inicio' not in update_fields and not inicio_existente:
             update_fields['inicio'] = datetime.now().strftime('%Y-%m-%d')

        # RN019: Se a tarefa foi concluída
        if tipo_dest == 'fim':
            update_fields['fim'] = datetime.now().strftime('%Y-%m-%d')
            update_fields['conclusao'] = 100
        elif progresso_padrao is not None:
            update_fields['conclusao'] = progresso_padrao

        set_clauses = [f"{key} = %s" for key in update_fields.keys()]
        params = list(update_fields.values()) + [int(card_id), project_id]
        
        cur.execute(f"UPDATE tarefas SET {', '.join(set_clauses)} WHERE id = %s AND projeto_id = %s", params)

        # RN016: Se a tarefa foi concluída, recalcular o projeto para adiantar sucessoras
        if tipo_dest == 'fim':
            tarefas_atuais = carregar_tarefas(project_id)
            tarefas_recalculadas = recalcular_datas_cascata(tarefas_atuais)
            salvar_tarefas_recalculadas(project_id, tarefas_recalculadas)

    db.commit()

def adicionar_tarefa(project_id, dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM tarefas WHERE projeto_id = %s", (project_id,))
        next_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, parent_id, tipo, criterios_aceite, sprint, planejado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (next_id, project_id, dados.get('fase'), dados.get('modulo'), dados.get('tarefa'), dados.get('subtarefa'), dados.get('descricao'), dados.get('dias'), dados.get('predecessora_id'), dados.get('conclusao'), dados.get('responsavel_id'), dados.get('baseline_inicio'), dados.get('baseline_fim'), dados.get('inicio'), dados.get('fim'), dados.get('kanban_coluna_id'), dados.get('parent_id'), dados.get('tipo') or 'task', dados.get('criterios_aceite'), dados.get('sprint'), dados.get('planejado', False))
        )
    db.commit()

def adicionar_log_atividade(cur, tarefa_pk_id, responsavel_id, detalhe):
    """Adiciona um log de atividade para uma tarefa."""
    cur.execute(
        "INSERT INTO tarefa_atividades (tarefa_pk_id, responsavel_id, tipo, detalhe) VALUES (%s, %s, 'log', %s)",
        (tarefa_pk_id, responsavel_id, detalhe)
    )

def editar_tarefa(project_id, task_id, dados):
    """Atualiza os campos de uma única tarefa."""
    # Validar datas antes de atualizar
    valido, erro = _validar_datas_tarefa(dados)
    if not valido:
        raise ValueError(erro)

    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Carrega a tarefa atual para comparar as mudanças
        cur.execute("SELECT * FROM tarefas WHERE projeto_id = %s AND id = %s", (project_id, task_id))
        tarefa_antiga = dict(cur.fetchone())

        # Constrói a query dinamicamente para atualizar apenas os campos fornecidos
        update_fields = {}
        campos_para_log = ['tarefa', 'subtarefa', 'responsavel_id', 'inicio', 'fim', 'dias', 'conclusao']
        for key in campos_para_log + ['descricao']:
            if key in dados:
                # Normaliza valores para comparação
                valor_antigo = tarefa_antiga.get(key)
                valor_novo = dados[key]
                if str(valor_antigo or '') != str(valor_novo or ''):
                    update_fields[key] = valor_novo

        if not update_fields: return

        set_clauses = [f"{key} = %s" for key in update_fields.keys()]
        params = list(update_fields.values()) + [project_id, task_id]
        cur.execute(f"UPDATE tarefas SET {', '.join(set_clauses)} WHERE projeto_id = %s AND id = %s", params)

        # Adiciona logs de atividade para as mudanças
        # (Assume que o usuário logado é passado em 'dados' ou obtido de outro lugar)
        # Para simplificar, vamos usar um ID de usuário fixo ou nulo por enquanto.
        responsavel_pela_acao = None 
        for campo, valor_novo in update_fields.items():
            if campo in campos_para_log:
                valor_antigo = tarefa_antiga.get(campo)
                detalhe = f"Campo '{campo}' alterado de '{valor_antigo or 'vazio'}' para '{valor_novo or 'vazio'}'."
                adicionar_log_atividade(cur, tarefa_antiga['pk_id'], responsavel_pela_acao, detalhe)

    db.commit()

def adicionar_comentario_tarefa(tarefa_pk_id, responsavel_id, comentario):
    """Adiciona um comentário a uma tarefa."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO tarefa_atividades (tarefa_pk_id, responsavel_id, tipo, detalhe) VALUES (%s, %s, 'comentario', %s)",
            (tarefa_pk_id, responsavel_id, comentario)
        )
    db.commit()

def carregar_atividades_tarefa(tarefa_pk_id):
    """Carrega todos os comentários e logs de uma tarefa."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT a.*, r.nome as responsavel_nome
            FROM tarefa_atividades a
            LEFT JOIN responsaveis r ON a.responsavel_id = r.id
            WHERE a.tarefa_pk_id = %s
            ORDER BY a.criado_em DESC
        """, (tarefa_pk_id,))
        return [dict(row) for row in cur.fetchall()]

def adicionar_time(dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO times (nome) VALUES (%s) RETURNING id", (dados['nome'],))
        time_id = cur.fetchone()[0]
        for membro_id in dados.get('membros', []):
            cur.execute("INSERT INTO responsaveis_times (responsavel_id, time_id) VALUES (%s, %s)", (membro_id, time_id))
    db.commit()

def adicionar_time(dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO times (nome) VALUES (%s) RETURNING id", (dados['nome'],))
        time_id = cur.fetchone()[0]
        for membro_id in dados.get('membros', []):
            cur.execute("INSERT INTO responsaveis_times (responsavel_id, time_id) VALUES (%s, %s)", (membro_id, time_id))
    db.commit()

def editar_time(id, dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE times SET nome = %s WHERE id = %s", (dados['nome'], id))
        cur.execute("DELETE FROM responsaveis_times WHERE time_id = %s", (id,))
        for membro_id in dados.get('membros', []):
            cur.execute("INSERT INTO responsaveis_times (responsavel_id, time_id) VALUES (%s, %s)", (membro_id, id))
    db.commit()

def excluir_time(id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM times WHERE id = %s", (id,))
    db.commit()
