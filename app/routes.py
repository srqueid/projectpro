# app/routes.py
import os
import io
import pandas as pd
import uuid
import json
from flask import (
    Blueprint, render_template, request, redirect, url_for, send_file, jsonify
)
from werkzeug.utils import secure_filename
from datetime import datetime

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
    if not nome:
        return redirect(url_for('main.home'))
    project_id = secure_filename(nome)
    project_manager.criar_projeto_db(project_id, nome)
    
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

@main_bp.route('/excluir_projeto/<project_id>', methods=['POST'])
def excluir_projeto(project_id):
    project_manager.excluir_projeto_db(project_id)
    return redirect(url_for('main.home'))

# =============================================================================
# ROTAS DE CONFIGURAÇÃO
# =============================================================================

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
    return render_template('planilha.html', tarefas=tarefas, page='planilha', project_id=project_id, stats=stats, responsaveis=responsaveis, times=times, projeto=projeto)

@main_bp.route('/projeto/<project_id>/kanban')
def kanban(project_id):
    tarefas = project_manager.carregar_tarefas(project_id)
    kanban_config = project_manager.carregar_kanban_config(project_id)
    colunas = kanban_config.get('colunas', [])
    stats = project_manager.calcular_stats(tarefas)
    cards_por_coluna = {col['id']: [] for col in colunas}
    cards_por_coluna['__sem_coluna__'] = []
    for t in tarefas:
        coluna_id = t.get('kanban_coluna_id')
        if coluna_id in cards_por_coluna:
            cards_por_coluna[coluna_id].append(t)
        else:
            cards_por_coluna['__sem_coluna__'].append(t)
    return render_template('kanban.html', tarefas=tarefas, page='kanban', project_id=project_id, stats=stats, colunas=colunas, cards_por_coluna=cards_por_coluna)

@main_bp.route('/projeto/<project_id>/cronograma')
def cronograma(project_id):
    tarefas_raw = project_manager.carregar_tarefas(project_id)
    stats = project_manager.calcular_stats(tarefas_raw)
    tarefas_gantt = []
    for t in tarefas_raw:
        if t.get('baseline_inicio') and t.get('baseline_fim'):
            tarefas_gantt.append({"id": f"{t['id']}_base", "name": t['subtarefa'] or t['tarefa'], "start": t['baseline_inicio'].strftime('%Y-%m-%d'), "end": t['baseline_fim'].strftime('%Y-%m-%d'), "progress": 0, "custom_class": "gantt-bar-baseline"})
        if t.get('inicio') and t.get('fim'):
            tarefas_gantt.append({"id": str(t['id']), "name": t['subtarefa'] or t['tarefa'], "start": t['inicio'].strftime('%Y-%m-%d'), "end": t['fim'].strftime('%Y-%m-%d'), "progress": t.get('conclusao', 0), "dependencies": t.get('predecessora_id')})
    return render_template('cronograma.html', tarefas=tarefas_gantt, page='cronograma', project_id=project_id, stats=stats)

# =============================================================================
# ROTAS DE API (SALVAR, RECALCULAR, ETC.)
# =============================================================================

@main_bp.route('/projeto/<project_id>/salvar', methods=['POST'])
def salvar_lote(project_id):
    novos_dados = request.get_json()
    if novos_dados:
        dados_calculados = project_manager.recalcular_datas_cascata(novos_dados)
        project_manager.salvar_tarefas(project_id, dados_calculados)
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400

@main_bp.route('/projeto/<project_id>/recalcular_rapido', methods=['POST'])
def recalcular_rapido(project_id):
    novos_dados = request.get_json()
    if novos_dados:
        dados_calculados = project_manager.recalcular_datas_cascata(novos_dados)
        resultado = [{'id': item['id'], 'inicio': item.get('inicio', ''), 'fim': item.get('fim', ''), 'baseline_fim': item.get('baseline_fim', '')} for item in dados_calculados]
        return jsonify({"status": "sucesso", "dados": resultado}), 200
    return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400

@main_bp.route('/projeto/<project_id>/kanban_mover_card', methods=['POST'])
def kanban_mover_card(project_id):
    data = request.get_json()
    project_manager.mover_card_kanban(project_id, data['card_id'], data['coluna_destino'])
    return jsonify({"status": "sucesso"}), 200

@main_bp.route('/projeto/<project_id>/adicionar_tarefa', methods=['POST'])
def adicionar_tarefa_kanban(project_id):
    dados = request.get_json()
    project_manager.adicionar_tarefa(project_id, dados)
    return jsonify({"status": "sucesso"}), 200

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
