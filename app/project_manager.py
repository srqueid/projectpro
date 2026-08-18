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

# Perfis e seus níveis de alçada para a matriz de promoção/rebaixamento
PERFIS_NIVEL_ALCADA = {
    'executor': 0,         # Decide livremente em Subtarefa ↔ Tarefa
    'scrum_master': 1,     # Gestão do fluxo
    'product_owner': 2,    # Aprova Tarefa/História ↔ Feature
    'product_manager': 3   # Aprova Feature ↔ Épico
}

# Labels dos perfis em português
PERFIS_LABELS = {
    'product_manager': 'Gerente de Produto',
    'scrum_master': 'Gestor do Projeto (Scrum Master)',
    'product_owner': 'Dono do Produto (PO)',
    'executor': 'Executor'
}

def carregar_perfis():
    """Carrega a lista de perfis cadastrados."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM rh.perfis ORDER BY id")
        return [dict(row) for row in cur.fetchall()]


def adicionar_perfil(dados):
    """Cria um novo perfil (papel de acesso/alçada)."""
    perfil_id = (dados.get('id') or '').strip().lower().replace(' ', '_')
    if not perfil_id:
        raise ValueError("O ID do perfil é obrigatório.")
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO rh.perfis (id, nome, descricao) VALUES (%s, %s, %s)",
            (perfil_id, dados['nome'], dados.get('descricao') or None)
        )
    db.commit()


def editar_perfil(perfil_id, dados):
    """Atualiza o nome e a descrição de um perfil."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE rh.perfis SET nome = %s, descricao = %s WHERE id = %s",
            (dados['nome'], dados.get('descricao') or None, perfil_id)
        )
    db.commit()


def excluir_perfil(perfil_id):
    """Exclui um perfil. Se houver responsáveis usando esse perfil, o perfil
    deles volta para o padrão 'executor' antes da exclusão."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE rh.responsaveis SET perfil = 'executor' WHERE perfil = %s",
            (perfil_id,)
        )
        cur.execute("DELETE FROM rh.perfis WHERE id = %s", (perfil_id,))
    db.commit()


def carregar_responsaveis():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM rh.responsaveis ORDER BY nome")
        responsaveis = [dict(row) for row in cur.fetchall()]
        for r in responsaveis:
            cur.execute("SELECT inicio, fim FROM rh.ferias WHERE responsavel_id = %s", (r['id'],))
            r['ferias'] = [dict(row) for row in cur.fetchall()]
    return responsaveis

def adicionar_responsavel(dados):
    db = database.get_db()
    horas_semanais = dados.get('horas_semanais') or None
    perfil = dados.get('perfil') or 'executor'
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO rh.responsaveis (nome, email, modelo_trabalho, horas_semanais, perfil) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (dados['nome'], dados['email'], dados['modelo_trabalho'], horas_semanais, perfil)
        )
        responsavel_id = cur.fetchone()[0]
        for periodo in dados.get('ferias', []):
            cur.execute("INSERT INTO rh.ferias (responsavel_id, inicio, fim) VALUES (%s, %s, %s)", (responsavel_id, periodo['inicio'], periodo['fim']))
    db.commit()

def editar_responsavel(id, dados):
    db = database.get_db()
    horas_semanais = dados.get('horas_semanais') or None
    perfil = dados.get('perfil') or 'executor'
    with db.cursor() as cur:
        cur.execute(
            "UPDATE rh.responsaveis SET nome = %s, email = %s, modelo_trabalho = %s, horas_semanais = %s, perfil = %s WHERE id = %s",
            (dados['nome'], dados['email'], dados['modelo_trabalho'], horas_semanais, perfil, id)
        )
        cur.execute("DELETE FROM rh.ferias WHERE responsavel_id = %s", (id,))
        for periodo in dados.get('ferias', []):
            cur.execute("INSERT INTO rh.ferias (responsavel_id, inicio, fim) VALUES (%s, %s, %s)", (id, periodo['inicio'], periodo['fim']))
    db.commit()

def excluir_responsavel(id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM rh.responsaveis WHERE id = %s", (id,))
    db.commit()

# =============================================================================
# GERENCIAMENTO DE PROJETOS E TAREFAS (COM BANCO DE DADOS)
# =============================================================================
def carregar_projetos():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, nome, descricao FROM projeto.projetos ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def carregar_projeto_por_id(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.projetos WHERE id = %s", (project_id,))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def criar_projeto_db(project_id, nome, descricao=''):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO projeto.projetos (id, nome, descricao) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING", (project_id, nome, descricao))
    db.commit()

def atualizar_descricao_projeto(project_id, descricao):
    """Atualiza a descrição do projeto."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE projeto.projetos SET descricao = %s WHERE id = %s", (descricao, project_id))
    db.commit()

def excluir_projeto_db(project_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.projetos WHERE id = %s", (project_id,))
    db.commit()

def carregar_tarefas(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s ORDER BY id", (project_id,))
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


# Nível de hierarquia de cada tipo de item.
# Regras: Épico (1) → Feature (2) → História (3) → Tarefa (4) → Subtarefa (5)
TIPO_NIVEL = {
    'epic': 1,
    'feature': 2,
    'story': 3,
    'task': 4,
    'subtask': 5
}


def _validar_hierarquia_tipos(tarefas):
    """
    Valida a hierarquia pai-filho conforme as regras de tipo:
    - Épico não pode ser filho de nenhum item.
    - Feature só pode ser filha de Épico.
    - História só pode ser filha de Feature.
    - Tarefa só pode ser filha de História.
    - Subtarefa só pode ser filha de Tarefa.
    Levanta ValueError se encontrar vínculo inválido.
    """
    mapa = {str(t.get('id')): t for t in tarefas}
    for t in tarefas:
        pid = t.get('parent_id')
        if pid is None or str(pid).strip() == '':
            continue
        pid_str = str(pid).strip()
        child_id = str(t.get('id'))
        child_tipo = t.get('tipo') or 'task'

        # Épico não pode ser filho de ninguém
        if child_tipo == 'epic':
            nome = t.get('tarefa') or t.get('subtarefa') or f"ID {t.get('id')}"
            raise ValueError(f"Um Épico ('{nome}') não pode ser filho de nenhum item.")

        parent = mapa.get(pid_str)
        if not parent:
            continue
        parent_tipo = parent.get('tipo') or 'task'

        c_nivel = TIPO_NIVEL.get(child_tipo)
        p_nivel = TIPO_NIVEL.get(parent_tipo)
        if c_nivel is None or p_nivel is None or c_nivel != p_nivel + 1:
            nome = t.get('tarefa') or t.get('subtarefa') or f"ID {t.get('id')}"
            nome_pai = parent.get('tarefa') or parent.get('subtarefa') or f"ID {parent.get('id')}"
            raise ValueError(
                f"Hierarquia inválida: '{nome}' (ID {t.get('id')}) não pode ser filha de '{nome_pai}' (ID {parent.get('id')}). "
                f"Canal permitido: Épico → Feature → História → Tarefa → Subtarefa."
            )
    return True


# Labels dos tipos de item em português
TIPO_LABELS = {
    'epic': 'Épico',
    'feature': 'Feature',
    'story': 'História',
    'task': 'Tarefa',
    'subtask': 'Subtarefa'
}


def _perfil_de_aprovacao(tipo_atual, novo_tipo):
    """
    Retorna o perfil mínimo necessário para aprovar a conversão de um item
    entre dois tipos adjacentes, conforme a matriz de alçada:
      - Envolvendo Épico (feature ↔ epic) -> product_manager
      - Envolvendo Feature (task/story ↔ feature) -> product_owner
      - Transições operacionais (subtask ↔ task e story ↔ task) -> executor (livre)
    Retorna '' se a transição não estiver mapeada.
    """
    adjacente = {tipo_atual, novo_tipo}
    if 'epic' in adjacente and 'feature' in adjacente:
        return 'product_manager'
    if 'feature' in adjacente and ('story' in adjacente or 'task' in adjacente):
        return 'product_owner'
    # Transições entre níveis operacionais (task↔subtask e story↔task):
    # decididas livremente pelo time de desenvolvimento/engenharia.
    if len(adjacente) == 2:
        return 'executor'
    return ''


def _tem_permissao_aprovacao(perfil_do_usuario, perfil_necessario):
    """
    Verifica se o perfil do usuário tem alçada suficiente para aprovar
    a transição (mesmo nível ou superior).
    """
    if not perfil_necessario:
        return False
    return PERFIS_NIVEL_ALCADA.get(perfil_do_usuario, 0) >= PERFIS_NIVEL_ALCADA.get(perfil_necessario, 0)


def _converter_um_nivel(tarefa, direcao):
    """
    Retorna o novo tipo ao subir (promover) ou descer (rebaixar) um nível
    na hierarquia. Retorna None se já estiver no extremo.

    Hierarquia: Épico(1) → Feature(2) → História(3) → Tarefa(4) → Subtarefa(5).
    Promover sobe em direção ao Épico (nível diminui); rebaixar desce (nível aumenta).
    """
    nivel_atual = TIPO_NIVEL.get(tarefa.get('tipo') or 'task')
    if not nivel_atual:
        return None
    if direcao == 'promover':
        novo_nivel = nivel_atual - 1  # Sobe na hierarquia (ex.: subtask->task, task->story)
    else:
        novo_nivel = nivel_atual + 1  # Desce na hierarquia (ex.: story->task, task->subtask)
    novo_tipo = next((k for k, v in TIPO_NIVEL.items() if v == novo_nivel), None)
    return novo_tipo


def converter_tipo_tarefa(project_id, task_id, direcao, responsavel_id=None):
    """
    Converte (promove ou rebaixa) um item em um nível na hierarquia:
    Épico → Feature → História → Tarefa → Subtarefa.

    Realiza:
      1. Carrega a tarefa e valida a transição possível.
      2. Valida a alçada (perfil) de quem solicita a conversão.
      3. Ajusta vínculos pai/filho que ficariam inválidos (reaproveita
         o pai se continuar válido; senão desvincula).
      4. Atualiza o tipo e registra log de atividade.

    Retorna um dicionário com status e detalhes para a UI.
    """
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, task_id))
        tarefa = cur.fetchone()
        if not tarefa:
            raise ValueError(f"Tarefa ID {task_id} não encontrada no projeto.")

        tarefa = dict(tarefa)
        tipo_atual = tarefa.get('tipo') or 'task'
        novo_tipo = _converter_um_nivel(tarefa, direcao)
        if not novo_tipo:
            raise ValueError(f"A tarefa já está no extremo da hierarquia e não pode ser {'promovida' if direcao == 'promover' else 'rebaixada'}.")

        # --- Validação de alçada (perfil) ---
        perfil_necessario = _perfil_de_aprovacao(tipo_atual, novo_tipo)
        perfil_usuario = 'executor'
        if responsavel_id:
            cur.execute("SELECT perfil FROM rh.responsaveis WHERE id = %s", (responsavel_id,))
            row = cur.fetchone()
            if row:
                perfil_usuario = row['perfil'] or 'executor'
        if not _tem_permissao_aprovacao(perfil_usuario, perfil_necessario):
            raise PermissionError(
                f"Alçada insuficiente. A transição {TIPO_LABELS.get(tipo_atual)} → {TIPO_LABELS.get(novo_tipo)} "
                f"requer aprovação de: {PERFIS_LABELS.get(perfil_necessario, perfil_necessario)}."
            )

        # --- Ajuste de vínculo com o PAI ---
        parent_id = tarefa.get('parent_id')
        if parent_id:
            cur.execute("SELECT tipo FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, parent_id))
            parent_row = cur.fetchone()
            parent_tipo = (parent_row['tipo'] if parent_row else 'task') or 'task'
            # Se o novo tipo não puder ser filho do tipo atual do pai, desvincula
            if TIPO_NIVEL.get(novo_tipo) != TIPO_NIVEL.get(parent_tipo) + 1:
                cur.execute("UPDATE projeto.tarefas SET parent_id = NULL WHERE projeto_id = %s AND id = %s", (project_id, task_id))

        # --- Ajuste dos FILHOS ---
        # Filhos que não puderem ser filhos do novo tipo são desvinculados
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND parent_id = %s", (project_id, task_id))
        filhos = [dict(r) for r in cur.fetchall()]
        for filho in filhos:
            filho_tipo = filho.get('tipo') or 'task'
            if TIPO_NIVEL.get(filho_tipo) != TIPO_NIVEL.get(novo_tipo) + 1:
                cur.execute("UPDATE projeto.tarefas SET parent_id = NULL WHERE projeto_id = %s AND id = %s", (project_id, filho['id']))

        # --- Atualiza o tipo ---
        cur.execute("UPDATE projeto.tarefas SET tipo = %s WHERE projeto_id = %s AND id = %s", (novo_tipo, project_id, task_id))

        # --- Log de atividade ---
        log_detalhe = (
            f"Item '{tarefa.get('tarefa') or tarefa.get('subtarefa') or f'ID {task_id}'}' "
            f"{'promovido' if direcao == 'promover' else 'rebaixado'}: "
            f"{TIPO_LABELS.get(tipo_atual)} → {TIPO_LABELS.get(novo_tipo)}."
        )
        adicionar_log_atividade(cur, tarefa['pk_id'], responsavel_id, log_detalhe)

    db.commit()
    return {
        'status': 'sucesso',
        'tarefa_id': task_id,
        'tipo_anterior': tipo_atual,
        'tipo_novo': novo_tipo
    }


def reassociar_item(project_id, task_id, novo_parent_id, responsavel_id=None):
    """
    Reassocia um item a um novo pai na hierarquia (Modelo A - legacy).
    Valida nível hierárquico e impede ciclos.
    """
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, task_id))
        tarefa = cur.fetchone()
        if not tarefa:
            raise ValueError(f"Item ID {task_id} não encontrado no projeto.")
        tarefa = dict(tarefa)

        if novo_parent_id:
            cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, novo_parent_id))
            pai = cur.fetchone()
            if not pai:
                raise ValueError(f"Item pai ID {novo_parent_id} não encontrado no projeto.")
            pai = dict(pai)

            nivel_filho = TIPO_NIVEL.get(tarefa.get('tipo') or 'task', 4)
            nivel_pai = TIPO_NIVEL.get(pai.get('tipo') or 'task', 4)

            if nivel_filho <= nivel_pai:
                raise ValueError(
                    f"Associação inválida: {TIPO_LABELS.get(tarefa.get('tipo') or 'task')} (nível {nivel_filho}) "
                    f"não pode ser filho de {TIPO_LABELS.get(pai.get('tipo') or 'task')} (nível {nivel_pai}). "
                    f"O pai deve ser de nível superior (menor número) ao filho."
                )

            current = str(novo_parent_id)
            visited = set()
            while current:
                if current == str(task_id):
                    raise ValueError("Associação inválida: criaria uma referência circular.")
                if current in visited:
                    break
                visited.add(current)
                cur.execute("SELECT parent_id FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, current))
                row = cur.fetchone()
                current = str(row['parent_id']) if row and row['parent_id'] else None

        cur.execute(
            "UPDATE projeto.tarefas SET parent_id = %s WHERE projeto_id = %s AND id = %s",
            (novo_parent_id, project_id, task_id)
        )

        log_detalhe = (
            f"Item '{tarefa.get('tarefa') or tarefa.get('subtarefa') or f'ID {task_id}'}' "
            f"reassociado ao pai ID {novo_parent_id or 'nenhum'}."
        )
        adicionar_log_atividade(cur, tarefa['pk_id'], responsavel_id, log_detalhe)

    db.commit()


def converter_tipo_especifico(project_id, task_id, novo_tipo, responsavel_id=None):
    """
    Converte um item para um tipo específico na hierarquia (Modelo A - legacy).
    Ajusta vínculos pai/filho que ficariam inválidos e registra log.
    """
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, task_id))
        tarefa = cur.fetchone()
        if not tarefa:
            raise ValueError(f"Item ID {task_id} não encontrado no projeto.")
        tarefa = dict(tarefa)
        tipo_atual = tarefa.get('tipo') or 'task'

        if tipo_atual == novo_tipo:
            return {'status': 'sucesso', 'tarefa_id': task_id, 'tipo_anterior': tipo_atual, 'tipo_novo': novo_tipo}

        perfil_necessario = _perfil_de_aprovacao(tipo_atual, novo_tipo)
        perfil_usuario = 'executor'
        if responsavel_id:
            cur.execute("SELECT perfil FROM rh.responsaveis WHERE id = %s", (responsavel_id,))
            row = cur.fetchone()
            if row:
                perfil_usuario = row['perfil'] or 'executor'
        if not _tem_permissao_aprovacao(perfil_usuario, perfil_necessario):
            raise PermissionError(
                f"Alçada insuficiente. A transição {TIPO_LABELS.get(tipo_atual)} → {TIPO_LABELS.get(novo_tipo)} "
                f"requer aprovação de: {PERFIS_LABELS.get(perfil_necessario, perfil_necessario)}."
            )

        parent_id = tarefa.get('parent_id')
        if parent_id:
            cur.execute("SELECT tipo FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, parent_id))
            parent_row = cur.fetchone()
            parent_tipo = (parent_row['tipo'] if parent_row else 'task') or 'task'
            if TIPO_NIVEL.get(novo_tipo) != TIPO_NIVEL.get(parent_tipo) + 1:
                cur.execute("UPDATE projeto.tarefas SET parent_id = NULL WHERE projeto_id = %s AND id = %s", (project_id, task_id))

        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND parent_id = %s", (project_id, task_id))
        filhos = [dict(r) for r in cur.fetchall()]
        for filho in filhos:
            filho_tipo = filho.get('tipo') or 'task'
            if TIPO_NIVEL.get(filho_tipo) != TIPO_NIVEL.get(novo_tipo) + 1:
                cur.execute("UPDATE projeto.tarefas SET parent_id = NULL WHERE projeto_id = %s AND id = %s", (project_id, filho['id']))

        cur.execute("UPDATE projeto.tarefas SET tipo = %s WHERE projeto_id = %s AND id = %s", (novo_tipo, project_id, task_id))

        log_detalhe = (
            f"Item '{tarefa.get('tarefa') or tarefa.get('subtarefa') or f'ID {task_id}'}' "
            f"convertido: {TIPO_LABELS.get(tipo_atual)} → {TIPO_LABELS.get(novo_tipo)}."
        )
        adicionar_log_atividade(cur, tarefa['pk_id'], responsavel_id, log_detalhe)

    db.commit()
    return {
        'status': 'sucesso',
        'tarefa_id': task_id,
        'tipo_anterior': tipo_atual,
        'tipo_novo': novo_tipo
    }


# =============================================================================
# CONFIGURAÇÃO DA PLANILHA (COLUNAS, CAMPOS CUSTOM, ÉPICOS)
# =============================================================================

def carregar_config_planilha(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT coluna_id, visivel, ordem FROM projeto.planilha_colunas_config WHERE projeto_id = %s ORDER BY ordem", (project_id,))
        colunas = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT id, nome, tipo, ordem FROM projeto.planilha_campos_custom WHERE projeto_id = %s ORDER BY ordem", (project_id,))
        campos = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT tarefa_pk_id FROM projeto.planilha_epicos WHERE projeto_id = %s", (project_id,))
        epicos = [str(row['tarefa_pk_id']) for row in cur.fetchall()]

    return {'colunas': colunas, 'campos': campos, 'epicos': epicos}


def salvar_config_colunas_planilha(project_id, colunas):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.planilha_colunas_config WHERE projeto_id = %s", (project_id,))
        for idx, col in enumerate(colunas):
            cur.execute(
                "INSERT INTO projeto.planilha_colunas_config (projeto_id, coluna_id, visivel, ordem) VALUES (%s, %s, %s, %s)",
                (project_id, col['coluna_id'], col.get('visivel', True), idx)
            )
    db.commit()


def salvar_campos_custom(project_id, campos):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.planilha_campos_custom WHERE projeto_id = %s", (project_id,))
        for idx, campo in enumerate(campos):
            cur.execute(
                "INSERT INTO projeto.planilha_campos_custom (projeto_id, nome, tipo, ordem) VALUES (%s, %s, %s, %s)",
                (project_id, campo['nome'], campo['tipo'], idx)
            )
    db.commit()


def salvar_epicos_planilha(project_id, epico_ids):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.planilha_epicos WHERE projeto_id = %s", (project_id,))
        for eid in epico_ids:
            try:
                eid_int = int(eid)
            except (ValueError, TypeError):
                continue
            cur.execute("SELECT pk_id FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, eid_int))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "INSERT INTO projeto.planilha_epicos (projeto_id, tarefa_pk_id) VALUES (%s, %s)",
                    (project_id, row[0])
                )
    db.commit()


def carregar_valores_custom(tarefa_ids):
    if not tarefa_ids:
        return {}
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """
            SELECT vc.tarefa_pk_id, vc.campo_id, c.nome, c.tipo, vc.valor_texto, vc.valor_data, vc.valor_numerico
            FROM projeto.planilha_valores_custom vc
            JOIN projeto.planilha_campos_custom c ON c.id = vc.campo_id
            WHERE vc.tarefa_pk_id = ANY(%s)
            """,
            (list(tarefa_ids),)
        )
        rows = [dict(row) for row in cur.fetchall()]
    result = {}
    for row in rows:
        tid = str(row['tarefa_pk_id'])
        if tid not in result:
            result[tid] = {}
        result[tid][row['nome']] = {
            'tipo': row['tipo'],
            'valor_texto': row['valor_texto'],
            'valor_data': row['valor_data'].strftime('%Y-%m-%d') if row['valor_data'] else None,
            'valor_numerico': row['valor_numerico']
        }
    return result


def salvar_valores_custom(project_id, tarefa_id, valores):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, tipo FROM projeto.planilha_campos_custom WHERE projeto_id = %s", (project_id,))
        campos = {str(row['id']): row['tipo'] for row in cur.fetchall()}
        for campo_id, tipo in campos.items():
            val = valores.get(campo_id)
            if val is None or val == '':
                cur.execute(
                    "DELETE FROM projeto.planilha_valores_custom WHERE tarefa_pk_id = %s AND campo_id = %s",
                    (tarefa_id, campo_id)
                )
            else:
                if tipo == 'texto' or tipo == 'texto_longo':
                    cur.execute(
                        """
                        INSERT INTO projeto.planilha_valores_custom (tarefa_pk_id, campo_id, valor_texto)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (tarefa_pk_id, campo_id) DO UPDATE SET valor_texto = EXCLUDED.valor_texto
                        """,
                        (tarefa_id, campo_id, val)
                    )
                elif tipo == 'data':
                    cur.execute(
                        """
                        INSERT INTO projeto.planilha_valores_custom (tarefa_pk_id, campo_id, valor_data)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (tarefa_pk_id, campo_id) DO UPDATE SET valor_data = EXCLUDED.valor_data
                        """,
                        (tarefa_id, campo_id, val)
                    )
                elif tipo == 'numerico':
                    try:
                        num = float(val)
                    except (ValueError, TypeError):
                        num = None
                    cur.execute(
                        """
                        INSERT INTO projeto.planilha_valores_custom (tarefa_pk_id, campo_id, valor_numerico)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (tarefa_pk_id, campo_id) DO UPDATE SET valor_numerico = EXCLUDED.valor_numerico
                        """,
                        (tarefa_id, campo_id, num)
                    )
    db.commit()


def carregar_tarefas_planilha(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND (tipo IS NULL OR tipo != 'epic') ORDER BY id", (project_id,))
        tarefas = [dict(row) for row in cur.fetchall()]
        if not tarefas:
            return tarefas
        ids = [t['id'] for t in tarefas]
        cur.execute(
            """
            SELECT vc.tarefa_pk_id, c.nome, c.tipo, vc.valor_texto, vc.valor_data, vc.valor_numerico
            FROM projeto.planilha_valores_custom vc
            JOIN projeto.planilha_campos_custom c ON c.id = vc.campo_id
            WHERE vc.tarefa_pk_id = ANY(%s)
            """,
            (ids,)
        )
        rows = [dict(row) for row in cur.fetchall()]
    valores_por_tarefa = {}
    for row in rows:
        tid = str(row['tarefa_pk_id'])
        if tid not in valores_por_tarefa:
            valores_por_tarefa[tid] = {}
        valores_por_tarefa[tid][row['nome']] = {
            'tipo': row['tipo'],
            'valor_texto': row['valor_texto'],
            'valor_data': row['valor_data'],
            'valor_numerico': row['valor_numerico']
        }
    for t in tarefas:
        t['valores_custom'] = valores_por_tarefa.get(str(t['id']), {})
    return tarefas


def salvar_tarefas(project_id, tarefas):
    # Valida a hierarquia de tipos (Épico → Feature → História → Tarefa → Subtarefa)
    _validar_hierarquia_tipos(tarefas)
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.tarefas WHERE projeto_id = %s", (project_id,))
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
                INSERT INTO projeto.tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, restricao_tipo, restricao_data, parent_id, tipo, criterios_aceite, sprint, planejado)
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
                "UPDATE projeto.tarefas SET baseline_inicio = %s, baseline_fim = %s, restricao_tipo = %s, restricao_data = %s WHERE projeto_id = %s AND id = %s",
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
# CONFIGURAÇÕES GLOBAIS E FERIADOS (schema config)
# =============================================================================
def carregar_settings():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT valor FROM config.configuracoes WHERE chave = 'block_weekends'")
        row = cur.fetchone()
        return {"block_weekends": row['valor'] == 'true'} if row else {"block_weekends": True}

def salvar_settings(settings):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE config.configuracoes SET valor = %s WHERE chave = 'block_weekends'", (str(settings['block_weekends']).lower(),))
    db.commit()

def carregar_feriados_custom():
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SELECT data FROM config.feriados_customizados")
        return {row[0].strftime('%Y-%m-%d') for row in cur.fetchall()}

def salvar_feriados_custom(lista_datas):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM config.feriados_customizados")
        for data in lista_datas:
            cur.execute("INSERT INTO config.feriados_customizados (data) VALUES (%s)", (data,))
    db.commit()

# =============================================================================
# CONFIGURAÇÕES POR PROJETO E KANBAN (schema projeto)
# =============================================================================
def carregar_config_projeto(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT chave, valor FROM projeto.projeto_configuracoes WHERE projeto_id = %s", (project_id,))
        rows = cur.fetchall()
        config = {}
        for row in rows:
            config[row['chave']] = row['valor']
        return config

def salvar_config_projeto(project_id, chave, valor):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO projeto.projeto_configuracoes (projeto_id, chave, valor) VALUES (%s, %s, %s) ON CONFLICT (projeto_id, chave) DO UPDATE SET valor = EXCLUDED.valor", (project_id, chave, str(valor)))
    db.commit()

def carregar_kanban_config(project_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT coluna_id, nome, tipo, progresso_padrao, allow_back FROM projeto.kanban_colunas WHERE projeto_id = %s ORDER BY ordem", (project_id,))
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
        cur.execute("DELETE FROM projeto.kanban_colunas WHERE projeto_id = %s", (project_id,))
        for i, col in enumerate(config_data.get('colunas', [])):
            # Garante que o progresso seja um inteiro ou nulo
            progresso = col.get('progresso_padrao')
            progresso = int(progresso) if progresso is not None and str(progresso).isdigit() else None
            allow_back = col.get('allow_back', True)
            if isinstance(allow_back, str):
                allow_back = allow_back.lower() == 'true'
            cur.execute(
                "INSERT INTO projeto.kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem, progresso_padrao, allow_back) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (project_id, col['coluna_id'], col['nome'], col['tipo'], i, progresso, allow_back)
            )
    db.commit()

# =============================================================================
# TIMES (schema rh)
# =============================================================================
def carregar_times():
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM rh.times ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def associar_time_projeto(project_id, time_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("UPDATE projeto.projetos SET time_id = %s WHERE id = %s", (time_id if time_id else None, project_id))
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
            "UPDATE projeto.tarefas SET conclusao = 0, kanban_coluna_id = 'backlog', inicio = NULL, fim = NULL WHERE projeto_id = %s AND id = %s",
            (project_id, card_id)
        )
    db.commit()
    # Recalcula o projeto
    tarefas_atuais = carregar_tarefas(project_id)
    tarefas_recalculadas = recalcular_datas_cascata(tarefas_atuais)
    salvar_tarefas_recalculadas(project_id, tarefas_recalculadas)
    return True


def planejar_tarefa(project_id, task_id, sprint=None, planejado=True):
    """Move uma tarefa entre Backlog e a entrada do Kanban conforme a sprint."""
    sprint = str(sprint or '').strip() or None
    planejado = bool(planejado) and sprint is not None
    coluna_kanban_id = 'iniciar' if planejado else 'backlog'

    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Tarefas de projetos com estrutura hierárquica têm UUID; a comparação
        # textual permite tratar os dois modelos sem converter o ID.
        cur.execute("""
            SELECT t.id
            FROM projeto.tarefas_hierarquicas t
            JOIN projeto.epicos e ON e.id = t.epico_id
            WHERE e.projeto_id = %s AND t.id::text = %s
        """, (project_id, str(task_id)))
        if cur.fetchone():
            cur.execute("""
                UPDATE projeto.tarefas_hierarquicas t
                SET planejado = %s, sprint = %s, kanban_coluna_id = %s
                FROM projeto.epicos e
                WHERE t.epico_id = e.id AND e.projeto_id = %s AND t.id::text = %s
            """, (planejado, sprint, coluna_kanban_id, project_id, str(task_id)))
        else:
            cur.execute("""
                UPDATE projeto.tarefas
                SET planejado = %s, sprint = %s, kanban_coluna_id = %s
                WHERE projeto_id = %s AND id = %s
            """, (planejado, sprint, coluna_kanban_id, project_id, task_id))
    db.commit()


def mover_card_kanban(project_id, card_id, coluna_destino_id, manter_data=False):
    db = database.get_db()
    from datetime import datetime
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Projetos com a estrutura hierárquica não usam a tabela legada de
        # tarefas. Localizamos primeiro esse tipo de card para persistir o
        # movimento no mesmo modelo que o Kanban está exibindo.
        cur.execute("""
            SELECT t.kanban_coluna_id, t.inicio
            FROM projeto.tarefas_hierarquicas t
            JOIN projeto.epicos e ON e.id = t.epico_id
            WHERE e.projeto_id = %s AND t.id::text = %s
        """, (project_id, str(card_id)))
        tarefa_atual = cur.fetchone()
        tarefa_hierarquica = tarefa_atual is not None

        if not tarefa_hierarquica:
            cur.execute(
                "SELECT kanban_coluna_id, inicio FROM projeto.tarefas WHERE projeto_id = %s AND id = %s",
                (project_id, card_id)
            )
            tarefa_atual = cur.fetchone()

        # Carrega a coluna de destino para obter seu tipo e progresso padrão
        cur.execute("SELECT tipo, progresso_padrao FROM projeto.kanban_colunas WHERE projeto_id = %s AND coluna_id = %s", (project_id, coluna_destino_id))
        col_dest = cur.fetchone()
        
        if not col_dest:
            # Se a coluna não for encontrada, apenas atualiza a coluna da tarefa sem outras ações.
            if tarefa_hierarquica:
                cur.execute("""
                    UPDATE projeto.tarefas_hierarquicas t
                    SET kanban_coluna_id = %s
                    FROM projeto.epicos e
                    WHERE t.epico_id = e.id AND e.projeto_id = %s AND t.id::text = %s
                """, (coluna_destino_id, project_id, str(card_id)))
            else:
                cur.execute("UPDATE projeto.tarefas SET kanban_coluna_id = %s WHERE projeto_id = %s AND id = %s", (coluna_destino_id, project_id, card_id))
            db.commit()
            return

        tipo_dest = col_dest['tipo']
        progresso_padrao = col_dest['progresso_padrao']

        # Carrega dados atuais da tarefa e da coluna de origem
        coluna_origem_id = tarefa_atual['kanban_coluna_id'] if tarefa_atual else None
        inicio_existente = tarefa_atual['inicio'] if tarefa_atual else None

        # Obtém o tipo da coluna de origem
        tipo_origem = None
        if coluna_origem_id:
            cur.execute("SELECT tipo FROM projeto.kanban_colunas WHERE projeto_id = %s AND coluna_id = %s", (project_id, coluna_origem_id))
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
        if tarefa_hierarquica:
            params = list(update_fields.values()) + [project_id, str(card_id)]
            cur.execute(f"""
                UPDATE projeto.tarefas_hierarquicas t
                SET {', '.join(set_clauses)}
                FROM projeto.epicos e
                WHERE t.epico_id = e.id AND e.projeto_id = %s AND t.id::text = %s
            """, params)
        else:
            params = list(update_fields.values()) + [int(card_id), project_id]
            cur.execute(f"UPDATE projeto.tarefas SET {', '.join(set_clauses)} WHERE id = %s AND projeto_id = %s", params)

        # RN016: Se a tarefa foi concluída, recalcular o projeto para adiantar sucessoras
        if tipo_dest == 'fim' and not tarefa_hierarquica:
            tarefas_atuais = carregar_tarefas(project_id)
            tarefas_recalculadas = recalcular_datas_cascata(tarefas_atuais)
            salvar_tarefas_recalculadas(project_id, tarefas_recalculadas)

    db.commit()

def adicionar_tarefa(project_id, dados):
    sprint = str(dados.get('sprint') or '').strip() or None
    planejado = bool(sprint)
    # A criação sempre começa no Backlog. Quando já há uma sprint informada,
    # o primeiro estágio operacional é a coluna "Iniciar" do Kanban.
    kanban_coluna_id = 'iniciar' if planejado else 'backlog'
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM projeto.tarefas WHERE projeto_id = %s", (project_id,))
        next_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO projeto.tarefas (id, projeto_id, fase, modulo, tarefa, subtarefa, descricao, dias, predecessora_id, conclusao, responsavel_id, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, parent_id, tipo, criterios_aceite, sprint, planejado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (next_id, project_id, dados.get('fase'), dados.get('modulo'), dados.get('tarefa'), dados.get('subtarefa'), dados.get('descricao'), dados.get('dias'), dados.get('predecessora_id'), dados.get('conclusao'), dados.get('responsavel_id'), dados.get('baseline_inicio'), dados.get('baseline_fim'), dados.get('inicio'), dados.get('fim'), kanban_coluna_id, dados.get('parent_id'), dados.get('tipo') or 'task', dados.get('criterios_aceite'), sprint, planejado)
        )
    db.commit()

def adicionar_log_atividade(cur, tarefa_pk_id, responsavel_id, detalhe):
    """Adiciona um log de atividade para uma tarefa."""
    cur.execute(
        "INSERT INTO projeto.tarefa_atividades (tarefa_pk_id, responsavel_id, tipo, detalhe) VALUES (%s, %s, 'log', %s)",
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
        # No modelo hierárquico o título da tarefa é armazenado como
        # ``titulo``. Atualizá-la aqui mantém a edição do card funcional sem
        # criar uma cópia na tabela legada.
        cur.execute("""
            SELECT t.*
            FROM projeto.tarefas_hierarquicas t
            JOIN projeto.epicos e ON e.id = t.epico_id
            WHERE e.projeto_id = %s AND t.id::text = %s
        """, (project_id, str(task_id)))
        tarefa_hierarquica = cur.fetchone()
        if tarefa_hierarquica:
            tarefa_antiga = dict(tarefa_hierarquica)
            campos = {
                'tarefa': 'titulo',
                'descricao': 'descricao',
                'responsavel_id': 'responsavel_id',
                'inicio': 'inicio',
                'fim': 'fim',
                'dias': 'dias',
                'conclusao': 'conclusao',
            }
            update_fields = {
                coluna: dados[chave]
                for chave, coluna in campos.items()
                if chave in dados and str(tarefa_antiga.get(coluna) or '') != str(dados[chave] or '')
            }
            if update_fields:
                set_clauses = [f"{key} = %s" for key in update_fields]
                params = list(update_fields.values()) + [project_id, str(task_id)]
                cur.execute(f"""
                    UPDATE projeto.tarefas_hierarquicas t
                    SET {', '.join(set_clauses)}
                    FROM projeto.epicos e
                    WHERE t.epico_id = e.id AND e.projeto_id = %s AND t.id::text = %s
                """, params)
            db.commit()
            return

        # Carrega a tarefa atual para comparar as mudanças
        cur.execute("SELECT * FROM projeto.tarefas WHERE projeto_id = %s AND id = %s", (project_id, task_id))
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
        cur.execute(f"UPDATE projeto.tarefas SET {', '.join(set_clauses)} WHERE projeto_id = %s AND id = %s", params)

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
            "INSERT INTO projeto.tarefa_atividades (tarefa_pk_id, responsavel_id, tipo, detalhe) VALUES (%s, %s, 'comentario', %s)",
            (tarefa_pk_id, responsavel_id, comentario)
        )
    db.commit()

def carregar_atividades_tarefa(tarefa_pk_id):
    """Carrega todos os comentários e logs de uma tarefa."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT a.*, r.nome as responsavel_nome
            FROM projeto.tarefa_atividades a
            LEFT JOIN rh.responsaveis r ON a.responsavel_id = r.id
            WHERE a.tarefa_pk_id = %s
            ORDER BY a.criado_em DESC
        """, (tarefa_pk_id,))
        return [dict(row) for row in cur.fetchall()]

def adicionar_time(dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("INSERT INTO rh.times (nome) VALUES (%s) RETURNING id", (dados['nome'],))
        time_id = cur.fetchone()[0]
        for membro_id in dados.get('membros', []):
            cur.execute("INSERT INTO rh.responsaveis_times (responsavel_id, time_id) VALUES (%s, %s)", (membro_id, time_id))
    db.commit()

def editar_time(id, dados):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE rh.times SET nome = %s WHERE id = %s", (dados['nome'], id))
        cur.execute("DELETE FROM rh.responsaveis_times WHERE time_id = %s", (id,))
        for membro_id in dados.get('membros', []):
            cur.execute("INSERT INTO rh.responsaveis_times (responsavel_id, time_id) VALUES (%s, %s)", (membro_id, id))
    db.commit()

def excluir_time(id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM rh.times WHERE id = %s", (id,))
    db.commit()

# =============================================================================
# EMPRESAS (TENANT) - SCHEMA core
# =============================================================================
def carregar_empresas():
    """Lista todas as empresas (tenants) cadastradas."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM core.empresas ORDER BY nome")
        return [dict(row) for row in cur.fetchall()]

def obter_empresa_por_id(empresa_id):
    """Retorna uma empresa pelo seu ID, ou None se não existir."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM core.empresas WHERE id = %s", (empresa_id,))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def adicionar_empresa(dados):
    """Cria uma nova empresa (tenant)."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO core.empresas (nome, cnpj, ativo) VALUES (%s, %s, %s) RETURNING id",
            (dados['nome'], dados.get('cnpj') or None, dados.get('ativo', True))
        )
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def editar_empresa(empresa_id, dados):
    """Atualiza os dados de uma empresa."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE core.empresas SET nome = %s, cnpj = %s, ativo = %s WHERE id = %s",
            (dados['nome'], dados.get('cnpj') or None, dados.get('ativo', True), empresa_id)
        )
    db.commit()

def excluir_empresa(empresa_id):
    """Exclui uma empresa e todos os dados vinculados (ON DELETE CASCADE)."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM core.empresas WHERE id = %s", (empresa_id,))
    db.commit()

def carregar_projetos_por_empresa(empresa_id):
    """Lista os projetos de uma empresa específica (isolamento por tenant)."""
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, nome, descricao FROM projeto.projetos WHERE empresa_id = %s ORDER BY nome", (empresa_id,))
        return [dict(row) for row in cur.fetchall()]

def criar_projeto_empresa(empresa_id, project_id, nome, descricao=''):
    """Cria um projeto vinculado a uma empresa."""
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO projeto.projetos (id, nome, descricao, empresa_id) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (project_id, nome, descricao, empresa_id)
        )
    db.commit()

# =============================================================================
# HIERARQUIA EM 5 TABELAS (Épico → Feature → História → Tarefa → Subtarefa)
# =============================================================================
def carregar_hierarquia_completa(empresa_id, projeto_id, apenas_backlog=False):
    """
    Carrega a hierarquia completa de um projeto em estrutura aninhada:
    Épicos → Features → Histórias → Tarefas → Subtarefas, respeitando o tenant.
    Retorna uma lista de épicos com seus descendentes.
    """
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT e.id AS epico_id, e.titulo AS epico_titulo, e.descricao AS epico_descricao,
                   e.status AS epico_status, e.projeto_id,
                   f.id AS feature_id, f.titulo AS feature_titulo, f.status AS feature_status,
                   h.id AS historia_id, h.titulo AS historia_titulo, h.pontos, h.status AS historia_status,
                   t.id AS tarefa_id, t.titulo AS tarefa_titulo, t.is_extraordinaria, t.status AS tarefa_status,
                   t.conclusao, t.responsavel_id, t.sprint, t.planejado,
                   s.id AS subtarefa_id, s.titulo AS subtarefa_titulo, s.concluida
            FROM projeto.epicos e
            LEFT JOIN projeto.features f ON f.epico_id = e.id
            LEFT JOIN projeto.historias h ON h.feature_id = f.id
            LEFT JOIN projeto.tarefas_hierarquicas t ON (
                t.historia_id = h.id
                OR (t.historia_id IS NULL AND t.is_extraordinaria = TRUE AND t.epico_id = e.id)
            )
            LEFT JOIN projeto.subtarefas s ON s.tarefa_id = t.id
            WHERE e.empresa_id = %s AND e.projeto_id = %s
              AND (%s = FALSE OR COALESCE(t.planejado, FALSE) = FALSE)
            ORDER BY e.titulo, f.titulo, h.titulo, t.titulo, s.titulo
        """, (empresa_id, projeto_id, apenas_backlog))
        rows = cur.fetchall()

    # Monta a árvore
    epicos_map = {}
    for r in rows:
        epico_id = r['epico_id']
        if epico_id not in epicos_map:
            epicos_map[epico_id] = {
                'id': epico_id, 'titulo': r['epico_titulo'], 'descricao': r['epico_descricao'],
                'status': r['epico_status'], 'projeto_id': r['projeto_id'],
                'features': [], 'tarefas_extraordinarias': []
            }
        epico = epicos_map[epico_id]
        is_extra = bool(r['is_extraordinaria'])
        if r['feature_id'] and not is_extra:
            feat = next((x for x in epico['features'] if x['id'] == r['feature_id']), None)
            if not feat:
                feat = {'id': r['feature_id'], 'titulo': r['feature_titulo'], 'status': r['feature_status'], 'historias': []}
                epico['features'].append(feat)
            if r['historia_id']:
                hist = next((x for x in feat['historias'] if x['id'] == r['historia_id']), None)
                if not hist:
                    hist = {'id': r['historia_id'], 'titulo': r['historia_titulo'], 'pontos': r['pontos'],
                            'status': r['historia_status'], 'tarefas': []}
                    feat['historias'].append(hist)
                if r['tarefa_id']:
                    tarefa = next((x for x in hist['tarefas'] if x['id'] == r['tarefa_id']), None)
                    if not tarefa:
                        tarefa = {'id': r['tarefa_id'], 'titulo': r['tarefa_titulo'], 'is_extraordinaria': r['is_extraordinaria'],
                                  'status': r['tarefa_status'], 'conclusao': r['conclusao'], 'responsavel_id': r['responsavel_id'],
                                  'sprint': r['sprint'], 'planejado': r['planejado'], 'subtarefas': []}
                        hist['tarefas'].append(tarefa)
                    if r['subtarefa_id']:
                        tarefa['subtarefas'].append({'id': r['subtarefa_id'], 'titulo': r['subtarefa_titulo'], 'concluida': r['concluida']})
        elif r['tarefa_id'] and is_extra:
            # Tarefa extraordinária direto no épico
            tarefa = next((x for x in epico['tarefas_extraordinarias'] if x['id'] == r['tarefa_id']), None)
            if not tarefa:
                tarefa = {'id': r['tarefa_id'], 'titulo': r['tarefa_titulo'], 'is_extraordinaria': True,
                          'status': r['tarefa_status'], 'conclusao': r['conclusao'], 'responsavel_id': r['responsavel_id'],
                          'sprint': r['sprint'], 'planejado': r['planejado'], 'subtarefas': []}
                epico['tarefas_extraordinarias'].append(tarefa)
            if r['subtarefa_id']:
                tarefa['subtarefas'].append({'id': r['subtarefa_id'], 'titulo': r['subtarefa_titulo'], 'concluida': r['concluida']})

    return list(epicos_map.values())


def carregar_tarefas_hierarquicas_plano(empresa_id, projeto_id):
    """
    Retorna uma lista PLANIFICADA (flat) de todas as tarefas de um projeto na
    nova hierarquia (5 tabelas), enriquecida com o contexto pai (épico, feature,
    história) e os blocos de sub-tarefas. Cada registro de 'tarefa' contém ainda
    os campos operacionais (datas, kanban, conclusão, responsável, etc.) usados
    pelas visualizações Kanban, Planilha e Cronograma.

    Estrutura de cada item retornado:
      {
        'id': tarefa.id (display), 'pk_id': None,
        'tipo': 'task', 'is_extraordinaria': bool,
        'titulo': tarefa.titulo, 'tarefa': titulo, 'subtarefa': None,
        'fase': None, 'modulo': None, 'descricao': ...,
        'dias', 'conclusao', 'responsavel_id', 'responsavel_nome',
        'baseline_inicio', 'baseline_fim', 'inicio', 'fim',
        'kanban_coluna_id', 'sprint', 'planejado', 'predecessora_id',
        'epico_id', 'epico_titulo', 'feature_id', 'feature_titulo',
        'historia_id', 'historia_titulo',
        'subtarefas': [ {'id','titulo','concluida'}, ... ]
      }
    """
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT e.id AS epico_id, e.titulo AS epico_titulo,
                   f.id AS feature_id, f.titulo AS feature_titulo,
                   h.id AS historia_id, h.titulo AS historia_titulo,
                   t.id AS tarefa_id, t.titulo AS tarefa_titulo,
                   t.is_extraordinaria, t.descricao, t.dias, t.conclusao,
                   t.responsavel_id, t.baseline_inicio, t.baseline_fim,
                   t.inicio, t.fim, t.kanban_coluna_id, t.sprint, t.planejado,
                   t.predecessora_id, t.status AS tarefa_status,
                   s.id AS subtarefa_id, s.titulo AS subtarefa_titulo, s.concluida
            FROM projeto.epicos e
            LEFT JOIN projeto.features f ON f.epico_id = e.id
            LEFT JOIN projeto.historias h ON h.feature_id = f.id
            LEFT JOIN projeto.tarefas_hierarquicas t ON (
                t.historia_id = h.id
                OR (t.historia_id IS NULL AND t.is_extraordinaria = TRUE AND t.epico_id = e.id)
            )
            LEFT JOIN projeto.subtarefas s ON s.tarefa_id = t.id
            WHERE e.empresa_id = %s AND e.projeto_id = %s
            ORDER BY e.titulo, f.titulo, h.titulo, t.titulo, s.titulo
        """, (empresa_id, projeto_id))
        rows = cur.fetchall()

    # Mapa responsáveis -> nome
    mapa_resp = {str(r['id']): r['nome'] for r in carregar_responsaveis()}

    tarefas_map = {}
    subtarefas_map = {}
    for r in rows:
        if not r['tarefa_id']:
            continue
        tid = str(r['tarefa_id'])
        coluna_kanban = r['kanban_coluna_id'] or 'backlog'
        if tid not in tarefas_map:
            tarefas_map[tid] = {
                'id': r['tarefa_id'],
                'tipo': 'task',
                'is_extraordinaria': r['is_extraordinaria'],
                'titulo': r['tarefa_titulo'],
                'tarefa': r['tarefa_titulo'],
                'subtarefa': None,
                'fase': None,
                'modulo': None,
                'descricao': r['descricao'],
                'dias': r['dias'] or 1,
                'conclusao': r['conclusao'] or 0,
                'responsavel_id': r['responsavel_id'],
                'responsavel_nome': mapa_resp.get(str(r['responsavel_id'])) if r['responsavel_id'] else None,
                'baseline_inicio': r['baseline_inicio'],
                'baseline_fim': r['baseline_fim'],
                'inicio': r['inicio'],
                'fim': r['fim'],
                # O fallback recupera itens existentes que foram criados antes
                # de a coluna inicial do Kanban ser definida.
                'kanban_coluna_id': coluna_kanban,
                'sprint': r['sprint'],
                'planejado': r['planejado'],
                'predecessora_id': r['predecessora_id'],
                'status': r['tarefa_status'],
                'epico_id': r['epico_id'],
                'epico_titulo': r['epico_titulo'],
                'feature_id': r['feature_id'],
                'feature_titulo': r['feature_titulo'],
                'historia_id': r['historia_id'],
                'historia_titulo': r['historia_titulo'],
                'subtarefas': [],
                'kanban_movel': True,
                'kanban_editavel': True,
            }
        if r['subtarefa_id']:
            tarefas_map[tid]['subtarefas'].append({
                'id': r['subtarefa_id'],
                'titulo': r['subtarefa_titulo'],
                'concluida': r['concluida'],
            })

            # Subtarefas também precisam de um card no Kanban. Elas acompanham
            # a coluna da tarefa pai até que tenham um fluxo independente.
            sid = str(r['subtarefa_id'])
            if sid not in subtarefas_map:
                subtarefas_map[sid] = {
                    'id': r['subtarefa_id'],
                    'tipo': 'subtask',
                    'titulo': r['subtarefa_titulo'],
                    'tarefa': None,
                    'subtarefa': r['subtarefa_titulo'],
                    'parent_id': r['tarefa_id'],
                    'parent_tarefa': r['tarefa_titulo'],
                    'fase': None,
                    'modulo': None,
                    'descricao': None,
                    'dias': 0,
                    'conclusao': 100 if r['concluida'] else 0,
                    'responsavel_id': r['responsavel_id'],
                    'responsavel_nome': mapa_resp.get(str(r['responsavel_id'])) if r['responsavel_id'] else None,
                    'baseline_inicio': None,
                    'baseline_fim': None,
                    'inicio': None,
                    'fim': None,
                    'kanban_coluna_id': coluna_kanban,
                    'sprint': r['sprint'],
                    'planejado': r['planejado'],
                    'predecessora_id': None,
                    'status': 'CONCLUIDA' if r['concluida'] else 'A_FAZER',
                    'kanban_movel': False,
                    'kanban_editavel': False,
                }

    return list(tarefas_map.values()) + list(subtarefas_map.values())


def adicionar_epico(empresa_id, projeto_id, titulo, descricao=None):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO projeto.epicos (empresa_id, projeto_id, titulo, descricao)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (empresa_id, projeto_id, titulo, descricao))
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def adicionar_feature(empresa_id, epico_id, titulo, descricao=None):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO projeto.features (empresa_id, epico_id, titulo, descricao)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (empresa_id, epico_id, titulo, descricao))
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def adicionar_historia(empresa_id, epico_id, feature_id, titulo, descricao=None, pontos=0):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO projeto.historias (empresa_id, epico_id, feature_id, titulo, descricao, pontos)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (empresa_id, epico_id, feature_id, titulo, descricao, pontos))
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def adicionar_tarefa_hierarquica(empresa_id, epico_id, historia_id, titulo, is_extraordinaria=False,
                                 descricao=None, responsavel_id=None, dias=1, sprint=None):
    """
    Adiciona uma tarefa na hierarquia.
    - Se historia_id for informado e is_extraordinaria=False -> tarefa normal.
    - Se historia_id for None e is_extraordinaria=True  -> tarefa extraordinária.
    """
    if is_extraordinaria:
        historia_id = None
    sprint = str(sprint or '').strip() or None
    planejado = bool(sprint)
    kanban_coluna_id = 'iniciar' if planejado else 'backlog'
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO projeto.tarefas_hierarquicas
                (empresa_id, epico_id, historia_id, is_extraordinaria, titulo, descricao,
                 responsavel_id, dias, sprint, planejado, kanban_coluna_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (empresa_id, epico_id, historia_id, is_extraordinaria, titulo, descricao,
              responsavel_id, dias, sprint, planejado, kanban_coluna_id))
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def adicionar_subtarefa(empresa_id, epico_id, tarefa_id, titulo):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO projeto.subtarefas (empresa_id, epico_id, tarefa_id, titulo)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (empresa_id, epico_id, tarefa_id, titulo))
        novo_id = cur.fetchone()[0]
    db.commit()
    return novo_id

def obter_epico_por_id(empresa_id, epico_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.epicos WHERE id = %s AND empresa_id = %s", (epico_id, empresa_id))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def obter_feature_por_id(empresa_id, feature_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.features WHERE id = %s AND empresa_id = %s", (feature_id, empresa_id))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def obter_historia_por_id(empresa_id, historia_id):
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projeto.historias WHERE id = %s AND empresa_id = %s", (historia_id, empresa_id))
        return dict(cur.fetchone()) if cur.rowcount > 0 else None

def excluir_epico(empresa_id, epico_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.epicos WHERE id = %s AND empresa_id = %s", (epico_id, empresa_id))
    db.commit()

def excluir_feature(empresa_id, feature_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.features WHERE id = %s AND empresa_id = %s", (feature_id, empresa_id))
    db.commit()

def excluir_historia(empresa_id, historia_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.historias WHERE id = %s AND empresa_id = %s", (historia_id, empresa_id))
    db.commit()

def excluir_tarefa_hierarquica(empresa_id, tarefa_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.tarefas_hierarquicas WHERE id = %s AND empresa_id = %s", (tarefa_id, empresa_id))
    db.commit()

def excluir_subtarefa(empresa_id, subtarefa_id):
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.subtarefas WHERE id = %s AND empresa_id = %s", (subtarefa_id, empresa_id))
    db.commit()


# Mapeamento reverso: tipo_label -> tabela + coluna_titulo
_TABELAS_HIERARQUIA = {
    'epico':    ('projeto.epicos',               'titulo'),
    'feature':  ('projeto.features',             'titulo'),
    'historia': ('projeto.historias',            'titulo'),
    'tarefa':   ('projeto.tarefas_hierarquicas', 'titulo'),
    'subtarefa':('projeto.subtarefas',           'titulo'),
}

# Níveis hierárquicos (menor = mais alto na árvore)
_NIVEL_TIPO = {
    'epico':    1,
    'feature':  2,
    'historia': 3,
    'tarefa':   4,
    'subtarefa':5,
}

# Tipos permitidos para cada nó (quais filhos podem ser criados diretamente sob ele)
_TIPOS_FILHO_PERMITIDOS = {
    'epico':    ['feature', 'tarefa'],   # feature OU tarefa extraordinária
    'feature':  ['historia'],
    'historia': ['tarefa'],
    'tarefa':   ['subtarefa'],
    'subtarefa': [],
}


def obter_item_hierarquico_por_id(empresa_id, tipo, item_id):
    """
    Busca um item hierárquico pelo tipo e id.
    Retorna dict com o item (inclui colunas relevantes como epico_id, feature_id,
    historia_id, tarefa_id) ou None.
    """
    if tipo not in _TABELAS_HIERARQUIA:
        return None
    tabela, _ = _TABELAS_HIERARQUIA[tipo]
    db = database.get_db()
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            f"SELECT * FROM {tabela} WHERE id = %s AND empresa_id = %s",
            (item_id, empresa_id)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def renomear_item(empresa_id, tipo, item_id, novo_titulo):
    """Atualiza o título de um item hierárquico de qualquer nível."""
    if tipo not in _TABELAS_HIERARQUIA:
        raise ValueError(f"Tipo hierárquico desconhecido: {tipo}")
    if not novo_titulo or not str(novo_titulo).strip():
        raise ValueError("Título não pode ser vazio.")
    tabela, col_titulo = _TABELAS_HIERARQUIA[tipo]
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute(
            f"UPDATE {tabela} SET {col_titulo} = %s WHERE id = %s AND empresa_id = %s RETURNING id",
            (str(novo_titulo).strip(), item_id, empresa_id)
        )
        ok = cur.rowcount > 0
    db.commit()
    return ok


def contar_filhos_afetados(empresa_id, tipo, item_id):
    """
    Conta recursivamente quantos itens filhos (sub-tree) serão afetados por
    uma exclusão ou promoção/mudança de tipo.

    Retorna dict: { feature:int, historia:int, tarefa:int, subtarefa:int, total:int }
    """
    item = obter_item_hierarquico_por_id(empresa_id, tipo, item_id)
    if not item:
        return None
    counts = {'epico': 0, 'feature': 0, 'historia': 0, 'tarefa': 0, 'subtarefa': 0, 'total': 0}
    db = database.get_db()
    with db.cursor() as cur:
        if tipo == 'epico':
            cur.execute("SELECT COUNT(*) FROM projeto.features WHERE epico_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['feature'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.historias WHERE epico_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['historia'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.tarefas_hierarquicas WHERE epico_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['tarefa'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.subtarefas WHERE epico_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['subtarefa'] = cur.fetchone()[0]
        elif tipo == 'feature':
            cur.execute("SELECT COUNT(*) FROM projeto.historias WHERE feature_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['historia'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.tarefas_hierarquicas th JOIN projeto.historias h ON th.historia_id = h.id WHERE h.feature_id = %s AND h.empresa_id = %s", (item['id'], empresa_id)); counts['tarefa'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.subtarefas s JOIN projeto.tarefas_hierarquicas th ON s.tarefa_id = th.id JOIN projeto.historias h ON th.historia_id = h.id WHERE h.feature_id = %s AND h.empresa_id = %s", (item['id'], empresa_id)); counts['subtarefa'] = cur.fetchone()[0]
        elif tipo == 'historia':
            cur.execute("SELECT COUNT(*) FROM projeto.tarefas_hierarquicas WHERE historia_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['tarefa'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projeto.subtarefas s JOIN projeto.tarefas_hierarquicas th ON s.tarefa_id = th.id WHERE th.historia_id = %s AND th.empresa_id = %s", (item['id'], empresa_id)); counts['subtarefa'] = cur.fetchone()[0]
        elif tipo == 'tarefa':
            cur.execute("SELECT COUNT(*) FROM projeto.subtarefas WHERE tarefa_id = %s AND empresa_id = %s", (item['id'], empresa_id)); counts['subtarefa'] = cur.fetchone()[0]
    counts['total'] = counts['epico'] + counts['feature'] + counts['historia'] + counts['tarefa'] + counts['subtarefa']
    return counts


def _validar_mudanca_de_tipo(empresa_id, tipo_atual, item_id, novo_tipo):
    """
    Valida se a mudança de tipo é permitida. Retorna (ok: bool, motivo: str|None,
    niveis_ok: bool). Uma mudança é válida se todos os filhos atuais caberão
    abaixo do novo tipo na hierarquia.
    """
    if tipo_atual == novo_tipo:
        return False, "O item já é deste tipo."
    if novo_tipo not in _NIVEL_TIPO or tipo_atual not in _NIVEL_TIPO:
        return False, "Tipo inválido."
    counts = contar_filhos_afetados(empresa_id, tipo_atual, item_id)
    if not counts:
        return False, "Item não encontrado."
    nivel_novo = _NIVEL_TIPO[novo_tipo]
    # Tipos possíveis de filhos imediatos permitidos no novo tipo:
    # novo epico     -> filhos diretos podiam ser feature/tarefa
    # novo feature   -> filhos diretos podiam ser historia
    # novo historia  -> filhos diretos podiam ser tarefa
    # novo tarefa    -> filhos diretos podiam ser subtarefa
    # novo subtarefa -> filhos diretos podiam ser []
    filhos_permitidos_nivel_max = {
        'epico':    2,  # feature
        'feature':  3,  # historia
        'historia': 4,  # tarefa
        'tarefa':   5,  # subtarefa
        'subtarefa':_NIVEL_TIPO[tipo_atual],  # subtarefa não tem filhos
    }
    max_nivel_filho_permitido = filhos_permitidos_nivel_max[novo_tipo]
    # Se o item for promovido para baixo (ex: epico->tarefa) mas tem filhos
    # que são features/historias, não pode.
    tem_incompativeis = False
    for tipo_f, qtd in counts.items():
        if tipo_f == 'total':
            continue
        if qtd > 0:
            nivel_filho = _NIVEL_TIPO.get(tipo_f, 0)
            if nivel_filho <= nivel_novo:
                # um filho de nível igual ou acima do novo pai não cabe
                tem_incompativeis = True
            elif nivel_filho > max_nivel_filho_permitido:
                # ex: virou feature e tem subtarefas diretas em cascata — proibido
                # (se forem tarefas -> ok, subtarefas -> ok desde que no máximo)
                pass
    if tem_incompativeis:
        return False, "O item possui sub-itens de nível incompatível com o novo tipo."
    return True, None, True


def alterar_tipo_item(empresa_id, tipo_atual, item_id, novo_tipo, novo_pai_id=None):
    """
    Altera o tipo hierárquico de um item com transação (BEGIN/COMMIT/ROLLBACK).

    Fluxo:
      1. Valida compatibilidade de filhos com o novo tipo.
      2. BEGIN
      3. Lê os dados do item da tabela atual.
      4. Insere na nova tabela (gera novo UUID ou preserva? → preserva id copiando).
         Ajusta flags:
           - Se virou 'tarefa extraordinária' (novo pai é epico):
             historia_id = NULL, is_extraordinaria = TRUE.
           - Se virou 'tarefa' e novo pai é historia:
             historia_id = pai.id, is_extraordinaria = FALSE.
      5. Atualiza FKs dos filhos imediatos para apontar para o novo id/lugar.
      6. DELETE do item na tabela antiga.
      7. COMMIT.

    Retorna dict { 'ok': bool, 'novo_id': str|None, 'novo_tipo': str, 'erro': str|None }
    """
    valido, motivo, *_ = _validar_mudanca_de_tipo(empresa_id, tipo_atual, item_id, novo_tipo)
    if not valido:
        return {'ok': False, 'novo_id': None, 'novo_tipo': novo_tipo, 'erro': motivo}

    item_velho = obter_item_hierarquico_por_id(empresa_id, tipo_atual, item_id)
    if not item_velho:
        return {'ok': False, 'novo_id': None, 'novo_tipo': novo_tipo, 'erro': 'Item não encontrado.'}

    db = database.get_db()
    try:
        db.autocommit = False
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # ----- Obtenção do contexto do novo pai (se fornecido) -----
            pai_info = None  # { tipo, epico_id, feature_id, historia_id, tarefa_id }
            if novo_pai_id and novo_tipo != 'epico':
                # tenta deduzir tipo do pai por buscas
                for t_tipo in ('tarefa', 'historia', 'feature', 'epico'):
                    tbl, _ = _TABELAS_HIERARQUIA[t_tipo]
                    cur.execute(f"SELECT * FROM {tbl} WHERE id = %s AND empresa_id = %s", (novo_pai_id, empresa_id))
                    r = cur.fetchone()
                    if r:
                        pai_info = {'tipo': t_tipo, **dict(r)}
                        break

            # ----- Calcula os novos campos epico/feature/historia/tarefa -----
            # Nível do novo tipo
            novo_nivel = _NIVEL_TIPO[novo_tipo]
            epico_id = item_velho.get('epico_id')
            feature_id = item_velho.get('feature_id')
            historia_id = item_velho.get('historia_id') if 'historia_id' in item_velho else None
            tarefa_id_ref = item_velho.get('tarefa_id') if 'tarefa_id' in item_velho else None

            if pai_info:
                # Garante epico_id/feature_id conforme o pai
                if pai_info['tipo'] == 'epico':
                    epico_id = pai_info['id']
                    feature_id = None
                    historia_id = None
                elif pai_info['tipo'] == 'feature':
                    epico_id = pai_info['epico_id']
                    feature_id = pai_info['id']
                    historia_id = None
                elif pai_info['tipo'] == 'historia':
                    epico_id = pai_info['epico_id']
                    feature_id = pai_info['feature_id']
                    historia_id = pai_info['id']
                elif pai_info['tipo'] == 'tarefa':
                    epico_id = pai_info['epico_id']
                    feature_id = None
                    # histórico: usaremos a historia da tarefa pai se houver
                    historia_id = pai_info.get('historia_id')

            # Ajustes de flags para tarefa
            is_extraordinaria = False
            if novo_tipo == 'tarefa':
                if novo_nivel == 4 and historia_id is None:
                    # Tarefa sem história -> extraordinária
                    is_extraordinaria = True
                if historia_id is not None:
                    is_extraordinaria = False

            titulo = item_velho.get('titulo') or item_velho.get('tarefa') or 'Sem título'
            descricao = item_velho.get('descricao')
            status = item_velho.get('status')
            responsavel_id = item_velho.get('responsavel_id')
            dias = item_velho.get('dias') or 1
            conclusao = item_velho.get('conclusao') or 0
            baseline_inicio = item_velho.get('baseline_inicio')
            baseline_fim = item_velho.get('baseline_fim')
            inicio_v = item_velho.get('inicio')
            fim_v = item_velho.get('fim')
            kanban_coluna_id = item_velho.get('kanban_coluna_id')
            sprint = item_velho.get('sprint')
            planejado = item_velho.get('planejado') or False
            prioridade = item_velho.get('prioridade') or 'MEDIA'

            novo_id = item_velho['id']  # preserva id

            # ----- Insere na nova tabela -----
            if novo_tipo == 'epico':
                # Para épico: precisa de projeto_id
                projeto_id = item_velho.get('projeto_id')
                if not projeto_id and 'epico_id' in item_velho and item_velho.get('epico_id'):
                    cur.execute("SELECT projeto_id FROM projeto.epicos WHERE id = %s AND empresa_id = %s", (item_velho['epico_id'], empresa_id))
                    r = cur.fetchone()
                    projeto_id = r[0] if r else None
                if not projeto_id:
                    raise ValueError("Não foi possível determinar projeto_id para o novo Épico.")
                cur.execute("""
                    INSERT INTO projeto.epicos (id, empresa_id, projeto_id, titulo, descricao, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (novo_id, empresa_id, projeto_id, titulo, descricao, status or 'PLANEJADO'))

            elif novo_tipo == 'feature':
                if not epico_id:
                    raise ValueError("Feature requer epico_id.")
                cur.execute("""
                    INSERT INTO projeto.features (id, empresa_id, epico_id, titulo, descricao, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (novo_id, empresa_id, epico_id, titulo, descricao, status or 'EM_ANDAMENTO'))

            elif novo_tipo == 'historia':
                if not epico_id:
                    raise ValueError("História requer epico_id.")
                if not feature_id:
                    raise ValueError("História requer feature_id.")
                pontos = item_velho.get('pontos') or 0
                cur.execute("""
                    INSERT INTO projeto.historias (id, empresa_id, epico_id, feature_id, titulo, descricao, pontos, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (novo_id, empresa_id, epico_id, feature_id, titulo, descricao, pontos, status or 'A_FAZER'))

            elif novo_tipo == 'tarefa':
                if not epico_id:
                    raise ValueError("Tarefa requer epico_id.")
                cur.execute("""
                    INSERT INTO projeto.tarefas_hierarquicas
                        (id, empresa_id, epico_id, historia_id, is_extraordinaria, titulo, descricao, status, prioridade,
                         responsavel_id, dias, conclusao, baseline_inicio, baseline_fim, inicio, fim, kanban_coluna_id, sprint, planejado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (novo_id, empresa_id, epico_id, (None if is_extraordinaria else historia_id),
                      is_extraordinaria, titulo, descricao, status or 'A_FAZER', prioridade,
                      responsavel_id, dias, conclusao, baseline_inicio, baseline_fim, inicio_v, fim_v,
                      kanban_coluna_id or 'backlog', sprint, planejado or bool(sprint)))

            elif novo_tipo == 'subtarefa':
                if not epico_id:
                    raise ValueError("Subtarefa requer epico_id.")
                if not tarefa_id_ref and not (pai_info and pai_info['tipo'] == 'tarefa'):
                    # Reusa uma tarefa existente se for possível; se não, cria uma extraordinária
                    cur.execute("""
                        INSERT INTO projeto.tarefas_hierarquicas
                            (empresa_id, epico_id, historia_id, is_extraordinaria, titulo, kanban_coluna_id)
                        VALUES (%s, %s, NULL, TRUE, %s, 'backlog') RETURNING id
                    """, (empresa_id, epico_id, f'Tarefa-Container-{titulo[:30]}'))
                    tarefa_id_ref = cur.fetchone()[0]
                elif pai_info and pai_info['tipo'] == 'tarefa':
                    tarefa_id_ref = pai_info['id']
                concluida = bool((conclusao or 0) >= 100) or item_velho.get('concluida') or False
                cur.execute("""
                    INSERT INTO projeto.subtarefas (id, empresa_id, epico_id, tarefa_id, titulo, concluida)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (novo_id, empresa_id, epico_id, tarefa_id_ref, titulo, concluida))

            # ----- Reatribuição de FKs dos filhos imediatos ao item movido -----
            # Se movemos um epico -> feature, todos os features antigos perdem o pai
            # então temos que migrar os filhos imediatos do nível antigo -> novo nível
            # Por simplicidade, movemos os filhos diretos baseados nas regras de pai.
            if tipo_atual == 'epico' and novo_tipo == 'feature':
                # features filhas -> devem ficar abaixo de uma feature? Não permitido.
                # Como a validação anterior bloqueou este caso com filhos, basta
                # garantir que historias/tarefas migraram seus epico_id e feature_id.
                cur.execute("UPDATE projeto.historias SET feature_id = %s WHERE epico_id = %s AND empresa_id = %s AND feature_id IS NULL", (novo_id, novo_id, empresa_id))
                cur.execute("UPDATE projeto.tarefas_hierarquicas SET epico_id = %s WHERE epico_id = %s AND empresa_id = %s", (epico_id, novo_id, empresa_id))

            if tipo_atual == 'feature' and novo_tipo == 'historia':
                cur.execute("UPDATE projeto.tarefas_hierarquicas SET historia_id = %s WHERE epico_id = %s AND historia_id IN (SELECT id FROM projeto.historias WHERE feature_id = %s AND empresa_id = %s)", (novo_id, epico_id, novo_id, empresa_id))

            # ----- DELETE do item na tabela antiga -----
            tabela_velha, _ = _TABELAS_HIERARQUIA[tipo_atual]
            cur.execute(f"DELETE FROM {tabela_velha} WHERE id = %s AND empresa_id = %s", (item_id, empresa_id))

            db.commit()
            return {'ok': True, 'novo_id': str(novo_id), 'novo_tipo': novo_tipo, 'erro': None}
    except Exception as e:
        try: db.rollback()
        except Exception: pass
        return {'ok': False, 'novo_id': None, 'novo_tipo': novo_tipo, 'erro': str(e)}
    finally:
        try: db.autocommit = True
        except Exception: pass


def criar_subitem_hierarquico(empresa_id, projeto_id, tipo_pai, pai_id, tipo_filho, titulo, **extras):
    """
    Cria um filho direto de um item hierárquico usando o botão + contextual.
    Valida que o tipo_filho é permitido sob o tipo_pai.
    Retorna novo_id ou None em caso de erro.
    """
    if tipo_filho not in _TIPOS_FILHO_PERMITIDOS.get(tipo_pai, []):
        raise ValueError(f"Não é possível criar '{tipo_filho}' diretamente sob '{tipo_pai}'.")
    titulo = (titulo or '').strip()
    if not titulo:
        raise ValueError("Título é obrigatório.")

    if tipo_filho == 'feature':
        return adicionar_feature(empresa_id, pai_id, titulo, extras.get('descricao'))

    if tipo_filho == 'historia':
        pai = obter_feature_por_id(empresa_id, pai_id)
        if not pai:
            raise ValueError("Feature pai não encontrada.")
        return adicionar_historia(empresa_id, pai['epico_id'], pai_id, titulo, extras.get('descricao'), extras.get('pontos') or 0)

    if tipo_filho == 'tarefa':
        # tarefa extraordinária (direto do epico) OU tarefa normal (sob historia)
        if tipo_pai == 'epico':
            return adicionar_tarefa_hierarquica(
                empresa_id, pai_id, None, titulo,
                is_extraordinaria=True, descricao=extras.get('descricao'),
                responsavel_id=extras.get('responsavel_id'), dias=extras.get('dias') or 1,
                sprint=extras.get('sprint')
            )
        if tipo_pai == 'historia':
            pai = obter_historia_por_id(empresa_id, pai_id)
            if not pai:
                raise ValueError("História pai não encontrada.")
            return adicionar_tarefa_hierarquica(
                empresa_id, pai['epico_id'], pai_id, titulo,
                is_extraordinaria=False, descricao=extras.get('descricao'),
                responsavel_id=extras.get('responsavel_id'), dias=extras.get('dias') or 1,
                sprint=extras.get('sprint')
            )

    if tipo_filho == 'subtarefa':
        # Descobre epico_id pela tarefa
        pai = obter_item_hierarquico_por_id(empresa_id, 'tarefa', pai_id)
        if not pai:
            raise ValueError("Tarefa pai não encontrada.")
        return adicionar_subtarefa(empresa_id, pai['epico_id'], pai_id, titulo)

    return None

