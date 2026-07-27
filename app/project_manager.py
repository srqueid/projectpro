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
        cur.execute("SELECT id, nome FROM projetos ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def carregar_projeto_por_id(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projetos WHERE id = %s", (project_id,))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def criar_projeto_db(project_id, nome):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO projetos (id, nome) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (project_id, nome))
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

def salvar_tarefas(project_id, tarefas):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM tarefas WHERE projeto_id = %s", (project_id,))
        default_coluna_id = carregar_kanban_config(project_id)['colunas'][0]['coluna_id']
        for t in tarefas:
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

            print(f"Inserindo tarefa id={task_id} predecessor={predecessora} responsavel={responsavel_id}")
            cur.execute(
                """
                INSERT INTO tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, restricao_tipo, restricao_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (task_id, project_id, t.get('fase'), t.get('modulo'), t.get('tarefa'), t.get('subtarefa'), t.get('descricao'), int(t.get('dias') or 0), predecessora, int(t.get('conclusao') or 0), responsavel_id, t.get('baseline_inicio'), t.get('baseline_fim'), t.get('inicio'), t.get('fim'), kanban_coluna_id, t.get('restricao_tipo'), t.get('restricao_data'))
            )
    db.commit()

def salvar_tarefas_recalculadas(project_id, tarefas):
    """
    Salva apenas as datas e campos de restrição de uma lista de tarefas,
    otimizado para atualizações pós-recálculo.
    """
    db = database.get_db()
    with db.cursor() as cur:
        for t in tarefas:
            cur.execute(
                "UPDATE tarefas SET inicio = %s, fim = %s, restricao_tipo = %s, restricao_data = %s WHERE projeto_id = %s AND id = %s",
                (t.get('inicio'), t.get('fim'), t.get('restricao_tipo'), t.get('restricao_data'), project_id, t['id'])
            )
    db.commit()

def recalcular_datas_cascata(tarefas):
    mapa_tarefas = {str(t['id']): t for t in tarefas}
    feriados_custom = carregar_feriados_custom()
    responsaveis = carregar_responsaveis()
    mapa_responsaveis = {r['id']: r for r in responsaveis}
    settings = carregar_settings()

    alteracoes = True
    loops = 0
    while alteracoes and loops < 100:
        alteracoes = False
        loops += 1
        for t in tarefas:
            if int(t.get('conclusao', 0)) == 100: continue
            responsavel_nome = t.get('responsavel_id')
            ferias = mapa_responsaveis.get(responsavel_nome, {}).get('ferias', [])
            dias = int(t.get('dias') or 0)
            
            # Ponto de partida para o cálculo
            novo_inicio = utils.str_to_date(t.get('inicio'))

            # RN015: Verificar se há restrição manual de data
            if t.get('restricao_tipo') == 'inicio_nao_antes_de' and t.get('restricao_data'):
                restricao_inicio = utils.str_to_date(t['restricao_data'])
                if not novo_inicio or novo_inicio < restricao_inicio:
                    novo_inicio = restricao_inicio

            # Se houver predecessora, a data dela tem prioridade (a menos que a restrição seja mais tarde)
            pred_id = str(t.get('predecessora_id') or t.get('predecessora') or '').lower().strip()
            if pred_id and pred_id in mapa_tarefas:
                fim_pred = mapa_tarefas[pred_id].get('fim')
                novo_inicio_pred = utils.str_to_date(fim_pred)
                if not novo_inicio or novo_inicio_pred > novo_inicio:
                    novo_inicio = novo_inicio_pred

            if novo_inicio:
                novo_fim = utils.date_to_str(utils.adicionar_dias_uteis(novo_inicio, dias, feriados_custom, ferias, settings.get('block_weekends', True)))
                novo_inicio_str = utils.date_to_str(novo_inicio)
                if t.get('inicio') != novo_inicio_str or t.get('fim') != novo_fim:
                    t['inicio'] = novo_inicio_str
                    t['fim'] = novo_fim
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
        cur.execute("SELECT coluna_id, nome, tipo, progresso_padrao FROM kanban_colunas WHERE projeto_id = %s ORDER BY ordem", (project_id,))
        colunas = [dict(row) for row in cur.fetchall()]
        if not colunas:
            # Se não houver configuração, retorna um padrão e salva para o projeto
            default_config = {"colunas": [{"coluna_id": "backlog", "nome": "📋 Backlog", "tipo": "backlog", "progresso_padrao": 0}, {"coluna_id": "iniciar", "nome": "🚀 Iniciar", "tipo": "inicio", "progresso_padrao": 0}, {"coluna_id": "andamento", "nome": "⚙️ Em Andamento", "tipo": "meio", "progresso_padrao": 50}, {"coluna_id": "concluido", "nome": "✅ Concluído", "tipo": "fim", "progresso_padrao": 100}]}
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
            cur.execute(
                "INSERT INTO kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem, progresso_padrao) VALUES (%s, %s, %s, %s, %s, %s)",
                (project_id, col['coluna_id'], col['nome'], col['tipo'], i, progresso)
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

def mover_card_kanban(project_id, card_id, coluna_destino_id):
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

        update_fields = {"kanban_coluna_id": coluna_destino_id}

        # RN022: Se o trabalho começou (movido para uma coluna de "meio")
        if tipo_dest == 'meio' and 'inicio' not in update_fields:
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
            INSERT INTO tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (next_id, project_id, dados.get('fase'), dados.get('modulo'), dados.get('tarefa'), dados.get('subtarefa'), dados.get('descricao'), dados.get('dias'), dados.get('predecessora_id'), dados.get('conclusao'), dados.get('responsavel_id'), dados.get('baseline_inicio'), dados.get('baseline_fim'), dados.get('inicio'), dados.get('fim'), dados.get('kanban_coluna_id'))
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
