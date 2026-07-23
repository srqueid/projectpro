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
        for t in tarefas:
            cur.execute(
                """
                INSERT INTO tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (t.get('id'), project_id, t.get('fase'), t.get('modulo'), t.get('tarefa'), t.get('subtarefa'), t.get('dias'), t.get('predecessora'), t.get('conclusao'), t.get('responsavel_id'), t.get('baseline_inicio'), t.get('baseline_fim'), t.get('inicio'), t.get('fim'), t.get('kanban_coluna_id'))
            )
    db.commit()

def recalcular_datas_cascata(tarefas):
    # (Esta função permanece a mesma, mas agora opera sobre os dados antes de serem salvos no BD)
    mapa_tarefas = {str(t['id']): t for t in tarefas}
    feriados_custom = carregar_feriados_custom()
    responsaveis = carregar_responsaveis()
    mapa_responsaveis = {r['nome']: r for r in responsaveis}
    settings = carregar_settings()

    for t in tarefas:
        responsavel_nome = t.get('responsavel')
        ferias = mapa_responsaveis.get(responsavel_nome, {}).get('ferias', [])
        baseline_inicio_str = t.get('baseline_inicio')
        dias = int(t.get('dias') or 0)
        if baseline_inicio_str:
            baseline_inicio_obj = utils.str_to_date(baseline_inicio_str)
            if baseline_inicio_obj:
                novo_baseline_fim = utils.date_to_str(utils.adicionar_dias_uteis(baseline_inicio_obj, dias, feriados_custom, ferias, settings.get('block_weekends', True)))
                if t.get('baseline_fim') != novo_baseline_fim:
                    t['baseline_fim'] = novo_baseline_fim
    
    alteracoes = True
    loops = 0
    while alteracoes and loops < 100:
        alteracoes = False
        loops += 1
        for t in tarefas:
            if int(t.get('conclusao', 0)) == 100: continue
            responsavel_nome = t.get('responsavel')
            ferias = mapa_responsaveis.get(responsavel_nome, {}).get('ferias', [])
            dias = int(t.get('dias') or 0)
            pred_id = str(t.get('predecessora')).lower().strip()
            if pred_id and pred_id in mapa_tarefas:
                fim_pred = mapa_tarefas[pred_id].get('fim')
                novo_inicio = utils.str_to_date(fim_pred)
            else:
                novo_inicio = utils.str_to_date(t.get('inicio'))
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
        cur.execute("SELECT coluna_id, nome, tipo FROM kanban_colunas WHERE projeto_id = %s ORDER BY ordem", (project_id,))
        colunas = [dict(row) for row in cur.fetchall()]
        return {"colunas": colunas} if colunas else {"colunas": [{"id": "backlog", "nome": "📋 Backlog", "tipo": "backlog"}, {"id": "iniciar", "nome": "🚀 Iniciar", "tipo": "inicio"}, {"id": "andamento", "nome": "⚙️ Em Andamento", "tipo": "meio"}, {"id": "concluido", "nome": "✅ Concluído", "tipo": "fim"}]}

def salvar_kanban_config(project_id, config_data):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM kanban_colunas WHERE projeto_id = %s", (project_id,))
        for i, col in enumerate(config_data.get('colunas', [])):
            cur.execute(
                "INSERT INTO kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem) VALUES (%s, %s, %s, %s, %s)",
                (project_id, col['id'], col['nome'], col['tipo'], i)
            )
    db.commit()
