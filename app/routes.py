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
    return render_template('planilha.html', tarefas=tarefas, page='planilha', project_id=project_id, stats=stats, responsaveis=responsaveis, times=times, projeto=projeto)

@main_bp.route('/projeto/<project_id>/associar_time', methods=['POST'])
def associar_time_projeto(project_id):
    time_id = request.form.get('time_id')
    project_manager.associar_time_projeto(project_id, time_id)
    return redirect(url_for('main.planilha', project_id=project_id))

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
            resultado = [{'id': item['id'], 'inicio': item.get('inicio', ''), 'fim': item.get('fim', ''), 'baseline_fim': item.get('baseline_fim', '')} for item in dados_calculados]
            return jsonify({"status": "sucesso", "dados": resultado}), 200
        return jsonify({"status": "erro", "mensagem": "Nenhum dado recebido"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

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
