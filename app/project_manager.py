# app/project_manager.py
import os
import json
import uuid
import psycopg2
import psycopg2.extras
from . import config, utils, database

# ... (código de times e responsáveis)

# =============================================================================
# GERENCIAMENTO DE PROJETOS E TAREFAS (COM BANCO DE DADOS)
# =============================================================================
# ... (funções de carregar, criar, excluir projetos e tarefas)

def mover_card_kanban(project_id, card_id, coluna_destino_id):
    """Move um card para uma nova coluna no Kanban e atualiza as datas."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM kanban_colunas WHERE projeto_id = %s", (project_id,))
        mapa_colunas = {col['coluna_id']: dict(col) for col in cur.fetchall()}
        
        col_dest = mapa_colunas.get(coluna_destino_id, {})
        tipo_dest = col_dest.get('tipo')

        update_fields = {"kanban_coluna_id": coluna_destino_id}
        if tipo_dest == 'inicio':
            update_fields['inicio'] = datetime.now().strftime('%Y-%m-%d')
        elif tipo_dest == 'fim':
            update_fields['fim'] = datetime.now().strftime('%Y-%m-%d')
            update_fields['conclusao'] = 100
        
        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
        params = list(update_fields.values()) + [project_id, card_id]
        
        cur.execute(f"UPDATE tarefas SET {set_clause} WHERE projeto_id = %s AND id = %s", params)
    db.commit()

# ... (restante do arquivo)
