# app/routes.py
import os
import io
import pandas as pd
import uuid
import json
import traceback
from flask import (
    Blueprint, render_template, request, redirect, url_for, send_file, jsonify
)
from werkzeug.utils import secure_filename
from datetime import datetime, date

from . import utils, project_manager, config

main_bp = Blueprint('main', __name__)

# =============================================================================
# ROTAS PRINCIPAIS E DE PROJETO
# =============================================================================

@main_bp.route('/')
def home():
    projetos = project_manager.carregar_projetos()
    for p in projetos:
        tarefas = project_manager.carregar_tarefas(p['id'])
        p['stats'] = project_manager.calcular_stats(tarefas)
    return render_template('home.html', projetos=projetos)

@main_bp.route('/criar_projeto', methods=['POST'])
def criar_projeto():
    nome = request.form.get('nome_projeto')
    descricao = request.form.get('descricao_projeto', '')
    if not nome:
        return redirect(url_for('main.home'))
    project_id = secure_filename(nome)
    project_manager.criar_projeto_db(project_id, nome, descricao)
    
    arquivo_csv = request.files.get('arquivo_csv')
    if arquivo_csv and arquivo_csv.filename != '':
        try:
            try:
                df = pd.read_csv(arquivo_csv, encoding='utf-8')
            except UnicodeDecodeError:
                arquivo_csv.seek(0)
                df = pd.read_csv(arquivo_csv, encoding='latin-1')
            df = df.where(pd.notnull(df), None)
            tarefas = df.to_dict('records')
            project_manager.salvar_tarefas(project_id, tarefas)
        except Exception as e:
            print(f"Erro ao processar CSV: {e}")
    return redirect(url_for('main.planilha', project_id=project_id))

@main_bp.route('/projeto/<project_id>/detalhes')
def detalhes_projeto(project_id):
    """Página de detalhes do projeto com descrição, épicos e histórias."""
    projeto = project_manager.carregar_projeto_por_id(project_id)
    tarefas = project_manager.carregar_tarefas(project_id)
    responsaveis = project_manager.carregar_responsaveis()
    
    # Separa por tipo
    epics = [t for t in tarefas if t.get('tipo') == 'epic']
    features = [t for t in tarefas if t.get('tipo') == 'feature']
    stories = [t for t in tarefas if t.get('tipo') == 'story']
    tasks = [t for t in tarefas if t.get('tipo') == 'task' or not t.get('tipo')]
    subtasks = [t for t in tarefas if t.get('tipo') == 'subtask']
    
    stats = project_manager.calcular_stats(tarefas)
    return render_template('detalhes_projeto.html', project_id=project_id, projeto=projeto, 
                          epics=epics, features=features, stories=stories, tasks=tasks, subtasks=subtasks,
                          stats=stats, responsaveis=responsaveis, page='detalhes')

@main_bp.route('/projeto/<project_id>/atualizar_descricao', methods=['POST'])
def atualizar_descricao_projeto(project_id):
    descricao = request.form.get('descricao', '')
    project_manager.atualizar_descricao_projeto(project_id, descricao)
    return redirect(url_for('main.detalhes_projeto', project_id=project_id))

@main_bp.route('/projeto/<project_id>/backlog')
def backlog(project_id):
    """Página de backlog - mostra itens não planejados."""
    tarefas = project_manager.carregar_tarefas(project_id)
    responsaveis = project_manager.carregar_responsaveis()
    
    # Filtra apenas itens não planejados
    backlog_items = [t for t in tarefas if not t.get('planejado')]
    planned_items = [t for t in tarefas if t.get('planejado')]
    
    stats = project_manager.calcular_stats(tarefas)
    return render_template('backlog.html', project_id=project_id, 
                          backlog_items=backlog_items, planned_items=planned_items,
                          stats=stats, responsaveis=responsaveis, page='backlog')

@main_bp.route('/excluir_projeto/<project_id>', methods=['POST'])
def excluir_projeto(project_id):
    project_manager.excluir_projeto_db(project_id)
    return redirect(url_for('main.home'))

# =============================================================================
# ROTAS DE CONFIGURAÇÃO
# =============================================================================

@main_bp.route('/projeto/<project_id>/configuracoes', methods=['GET', 'POST'])
def configuracoes_projeto(project_id):
    if request.method == 'POST':
        tolerancia = request.form.get('tolerancia_percent', 10)
        project_manager.salvar_config_projeto(project_id, 'tolerancia_percent', tolerancia)
        return redirect(url_for('main.configuracoes_projeto', project_id=project_id))
    
    config = project_manager.carregar_config_projeto(project_id)
    return render_template('configuracoes_projeto.html', project_id=project_id, config=config)

@main_bp.route('/configuracoes')
def gerenciar_configuracoes():
    responsaveis = project_manager.carregar_responsaveis()
    times = project_manager.carregar_times()
    feriados = project_manager.carregar_feriados_custom()
    settings = project_manager.carregar_settings()
    return render_template('configuracoes.html', responsaveis=responsaveis, times=times, feriados=sorted(list(feriados)), settings=settings)

@main_bp.route('/configuracoes/dias', methods=['POST'])
def salvar_configuracoes_dias():
    settings = {'block_weekends': 'block_weekends' in request.form}
    project_manager.salvar_settings(settings)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/times/adicionar', methods=['POST'])
def adicionar_time():
    dados = request.form.to_dict()
    membros = request.form.getlist('membros')
    dados['membros'] = membros
    project_manager.adicionar_time(dados)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/times/editar/<id>', methods=['POST'])
def editar_time(id):
    dados = request.form.to_dict()
    membros = request.form.getlist('membros')
    dados['membros'] = membros
    project_manager.editar_time(id, dados)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/times/excluir/<id>', methods=['POST'])
def excluir_time(id):
    project_manager.excluir_time(id)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/responsaveis/adicionar', methods=['POST'])
def adicionar_responsavel():
    dados = request.form.to_dict()
    dados['ferias'] = json.loads(request.form.get('ferias', '[]'))
    project_manager.adicionar_responsavel(dados)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/responsaveis/editar/<id>', methods=['POST'])
def editar_responsavel(id):
    dados = request.form.to_dict()
    dados['ferias'] = json.loads(request.form.get('ferias', '[]'))
    project_manager.editar_responsavel(id, dados)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/responsaveis/excluir/<id>', methods=['POST'])
def excluir_responsavel(id):
    project_manager.excluir_responsavel(id)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/feriados/adicionar', methods=['POST'])
def adicionar_feriado():
    nova_data = request.form.get('data_feriado')
    if nova_data:
        feriados = project_manager.carregar_feriados_custom()
        feriados.add(nova_data)
        project_manager.salvar_feriados_custom(feriados)
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/feriados/importar', methods=['POST'])
def importar_feriados_csv():
    arquivo = request.files.get('arquivo_csv')
    if arquivo and arquivo.filename != '':
        try:
            df = pd.read_csv(arquivo, header=None)
            novas_datas = set()
            for col in df.columns:
                for val in df[col]:
                    try:
                        novas_datas.add(pd.to_datetime(val, dayfirst=True).strftime('%Y-%m-%d'))
                    except:
                        continue
            if novas_datas:
                feriados = project_manager.carregar_feriados_custom()
                feriados.update(novas_datas)
                project_manager.salvar_feriados_custom(feriados)
        except Exception as e:
            print(f"Erro ao importar CSV de feriados: {e}")
    return redirect(url_for('main.gerenciar_configuracoes'))

@main_bp.route('/feriados/excluir', methods=['POST'])
def excluir_feriado():
    data_para_remover = request.form.get('data')
    if data_para_remover:
        feriados = project_manager.carregar_feriados_custom()
        feriados.discard(data_para_remover)
        project_manager.salvar_feriados_custom(feriados)
    return redirect(url_for('main.gerenciar_configuracoes'))

# ... (Rotas de Responsáveis, Times, Feriados)

# =============================================================================
# ROTAS DE VISUALIZAÇÃO DE PROJETO (PLANILHA, KANBAN, CRONOGRAMA)
# =============================================================================

@main_bp.route('/projeto/<project_id>/planilha')
def planilha(project_id):
    tarefas = project_manager.carregar_tarefas(project_id)
    stats = project_manager.calcular_stats(tarefas)
    responsaveis = project_manager.carregar_responsaveis()
    times = project_manager.carregar_times()
    projeto = project_manager.carregar_projeto_por_id(project_id)
    # Carrega a config Kanban para identificar a coluna "Em Andamento" (tipo 'meio')
    kanban_config = project_manager.carregar_kanban_config(project_id)
    coluna_andamento_id = ''
    for col in kanban_config.get('colunas', []):
        if col['tipo'] == 'meio':
            coluna_andamento_id = col['coluna_id']
            break
    return render_template('planilha.html', tarefas=tarefas, page='planilha', project_id=project_id, stats=stats, responsaveis=responsaveis, times=times, projeto=projeto, coluna_andamento_id=coluna_andamento_id)

@main_bp.route('/projeto/<project_id>/associar_time', methods=['POST'])
def associar_time_projeto(project_id):
    time_id = request.form.get('time_id')
    project_manager.associar_time_projeto(project_id, time_id)
    return redirect(url_for('main.planilha', project_id=project_id))

@main_bp.route('/projeto/<project_id>/kanban')
def kanban(project_id):
    tarefas = project_manager.carregar_tarefas(project_id)
    # Mostra apenas tarefas planejadas (com sprint definido) no Kanban
    tarefas = [t for t in tarefas if t.get('planejado')]
    kanban_config = project_manager.carregar_kanban_config(project_id)
    colunas = kanban_config.get('colunas', [])
    mapa_tipos_coluna = {col['coluna_id']: col['tipo'] for col in colunas}
    hoje = date.today() # Adicionado para RN024
    
    # Carrega os responsáveis para obter seus nomes
    responsaveis = project_manager.carregar_responsaveis()
    mapa_responsaveis = {str(r['id']): r['nome'] for r in responsaveis}

    mapa_tarefas = {str(t['id']): t for t in tarefas}
    for t in tarefas:
        # Adiciona o nome do responsável à tarefa
        if t.get('responsavel_id'):
            t['responsavel_nome'] = mapa_responsaveis.get(str(t['responsavel_id']))

        # Carrega atividades e comentários
        atividades = project_manager.carregar_atividades_tarefa(t['pk_id'])
        t['atividades'] = atividades

        # RN024: Identificar tarefas vencidas (Lógica existente)
        t['em_atraso'] = False
        fim_tarefa = t.get('fim')
        coluna_id = t.get('kanban_coluna_id')
        coluna_tipo = mapa_tipos_coluna.get(coluna_id)

        if coluna_tipo != 'fim' and fim_tarefa and fim_tarefa < hoje:
            t['em_atraso'] = True
            t['dias_atraso'] = (hoje - fim_tarefa).days

        # RN023: Identificar tarefas bloqueadas
        predecessora_id = str(t.get('predecessora_id') or '').strip()
        if predecessora_id and predecessora_id in mapa_tarefas:
            predecessora = mapa_tarefas[predecessora_id]
            pred_coluna_id = predecessora.get('kanban_coluna_id')
            pred_coluna_tipo = mapa_tipos_coluna.get(pred_coluna_id)

            if pred_coluna_tipo != 'fim' and predecessora.get('conclusao', 0) < 100:
                t['bloqueada_por'] = {
                    'id': predecessora['id'],
                    'nome': predecessora.get('subtarefa') or predecessora.get('tarefa') or f"Tarefa #{predecessora['id']}"
                }

    stats = project_manager.calcular_stats(tarefas)
    cards_por_coluna = {col['coluna_id']: [] for col in colunas}
    for t in tarefas:
        coluna_id = t.get('kanban_coluna_id')
        cards_por_coluna.setdefault(coluna_id, []).append(t)

    return render_template('kanban.html', tarefas=tarefas, page='kanban', project_id=project_id, stats=stats, colunas=colunas, cards_por_coluna=cards_por_coluna, responsaveis=responsaveis)

@main_bp.route('/projeto/<project_id>/cronograma')
def cronograma(project_id):
    from datetime import datetime
    tarefas_raw = project_manager.carregar_tarefas(project_id)
    stats = project_manager.calcular_stats(tarefas_raw)
    config = project_manager.carregar_config_projeto(project_id)
    tolerancia_percent = int(config.get('tolerancia_percent', 10))
    tarefas_gantt = []
    for t in tarefas_raw:
        nome_tarefa = t['subtarefa'] or t['tarefa']
        if t.get('baseline_inicio') and t.get('baseline_fim'):
            tarefas_gantt.append({"id": f"{t['id']}_base", "name": f"{nome_tarefa} (Planejamento)", "start": t['baseline_inicio'].strftime('%Y-%m-%d'), "end": t['baseline_fim'].strftime('%Y-%m-%d'), "progress": 0, "custom_class": "gantt-bar-baseline"})
        if t.get('inicio') and t.get('fim'):
            fim_execucao = t['fim']
            baseline_fim = t.get('baseline_fim')
            baseline_inicio = t.get('baseline_inicio')
            if baseline_fim and baseline_inicio:
                dias_baseline = (baseline_fim - baseline_inicio).days
                if dias_baseline > 0:
                    tolerancia_dias = dias_baseline * (tolerancia_percent / 100)
                    if fim_execucao > baseline_fim and (fim_execucao - baseline_fim).days > tolerancia_dias:
                        custom_class = "gantt-bar-atraso-grave"
                    elif fim_execucao > baseline_fim:
                        custom_class = "gantt-bar-atraso-leve"
                    else:
                        custom_class = "gantt-bar-execucao"
                else:
                    custom_class = "gantt-bar-execucao"
            else:
                custom_class = "gantt-bar-execucao"
            predecessora = t.get('predecessora_id')
            tarefas_gantt.append({"id": str(t['id']), "name": nome_tarefa, "start": t['inicio'].strftime('%Y-%m-%d'), "end": t['fim'].strftime('%Y-%m-%d'), "progress": t.get('conclusao', 0), "dependencies": [str(predecessora)] if predecessora else [], "custom_class": custom_class})
    return render_template('cronograma.html', tarefas=tarefas_gantt, page='cronograma', project_id=project_id, stats=stats)

# =============================================================================
# ROTAS DE API (SALVAR, RECALCULAR, ETC.)
# =============================================================================

@main_bp.route('/projeto/<project_id>/salvar', methods=['POST'])
def salvar_lote(project_id):
    try:
        novos_dados = request.get_json()
        if novos_dados:
            dados_calculados = project_manager.recalcular_datas_cascata(novos_dados)
            project_manager.salvar_tarefas(project_id, dados_calculados)
            return jsonify({"status": "sucesso"}), 200
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@main_bp.route('/projeto/<project_id>/recalcular_rapido', methods=['POST'])
def recalcular_rapido(project_id):
    try:
        novos_dados = request.get_json()
        if novos_dados:
            dados_calculados = project_manager.recalcular_datas_cascata(novos_dados)
            resultado = [{'id': item['id'], 'baseline_inicio': item.get('baseline_inicio', ''), 'baseline_fim': item.get('baseline_fim', '')} for item in dados_calculados]
            return jsonify({"status": "sucesso", "dados": resultado}), 200
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@main_bp.route('/projeto/<project_id>/kanban_mover_card', methods=['POST'])
def kanban_mover_card(project_id):
    data = request.get_json()
    project_manager.mover_card_kanban(project_id, data['card_id'], data['coluna_destino'], manter_data=data.get('manter_data', False))
    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/kanban_replanejar', methods=['POST'])
def kanban_replanejar(project_id):
    """Replaneja uma tarefa saindo da coluna Concluído - limpa datas e volta ao backlog."""
    data = request.get_json()
    card_id = data.get('card_id')
    if card_id:
        project_manager.replanejar_tarefa(project_id, card_id)
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro", "mensagem": "card_id não informado"}), 400

@main_bp.route('/projeto/<project_id>/kanban/salvar_config', methods=['POST'])
def kanban_salvar_config(project_id):
    config_data = request.get_json()
    project_manager.salvar_kanban_config(project_id, config_data)
    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/adicionar_tarefa', methods=['POST'])
def adicionar_tarefa_kanban(project_id):
    dados = request.get_json()
    project_manager.adicionar_tarefa(project_id, dados)
    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/editar_tarefa/<task_id>', methods=['POST'])
def editar_tarefa_kanban(project_id, task_id):
    dados = request.get_json()
    project_manager.editar_tarefa(project_id, task_id, dados)

    # Se uma data ou duração foi alterada, recalcula o projeto
    if any(k in dados for k in ['inicio', 'dias']):
        tarefas_atuais = project_manager.carregar_tarefas(project_id)
        tarefas_recalculadas = project_manager.recalcular_datas_cascata(tarefas_atuais)
        project_manager.salvar_tarefas_recalculadas(project_id, tarefas_recalculadas)

    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/planejar_tarefa', methods=['POST'])
def planejar_tarefa(project_id):
    """Marca uma tarefa como planejada (para um sprint) ou remove do planejamento."""
    dados = request.get_json()
    task_id = dados.get('task_id')
    sprint = dados.get('sprint', '')
    planejado = dados.get('planejado', True)
    
    from . import database
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE tarefas SET planejado = %s, sprint = %s WHERE projeto_id = %s AND id = %s",
            (planejado, sprint if sprint else None, project_id, task_id)
        )
    db.commit()
    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/tarefa/<task_pk_id>/adicionar_comentario', methods=['POST'])
def adicionar_comentario(project_id, task_pk_id):
    dados = request.get_json()
    comentario = dados.get('comentario')
    # Em um sistema real, o ID do responsável viria da sessão do usuário logado.
    # Por enquanto, vamos permitir que seja enviado ou usar um valor fixo/nulo.
    responsavel_id = dados.get('responsavel_id') or None 
    if comentario:
        project_manager.adicionar_comentario_tarefa(task_pk_id, responsavel_id, comentario)
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro", "mensagem": "Comentário vazio"}), 400

@main_bp.route('/projeto/<project_id>/exportar_excel')
def exportar_excel(project_id):
    tarefas = project_manager.carregar_tarefas(project_id)
    df = pd.DataFrame(tarefas)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Tarefas')
    writer.close()
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'{project_id}.xlsx')

@main_bp.route('/baixar_modelo')
def baixar_modelo():
    colunas = ["ID", "Fase", "Módulo", "Tarefa", "Subtarefa", "Início", "Dias", "Fim", "Predecessora", "Conclusão %", "Responsável", "Baseline_Início", "Baseline_Fim"]
    buffer = io.BytesIO()
    pd.DataFrame(columns=colunas).to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='modelo_importacao.csv', mimetype='text/csv')
