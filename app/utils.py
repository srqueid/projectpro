# app/utils.py
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from . import config

# --- Feriados Nacionais ---
try:
    import holidays
    br_holidays = holidays.Brazil()
except ImportError:
    print("Aviso: Biblioteca 'holidays' não encontrada. Usando lista manual.")
    br_holidays = config.MANUAL_HOLIDAYS

# =============================================================================
# FUNÇÕES AUXILIARES - FERIADOS CUSTOMIZADOS
# =============================================================================

def carregar_feriados_custom():
    """Carrega a lista de feriados personalizados do arquivo JSON."""
    if os.path.exists(config.CUSTOM_HOLIDAYS_FILE):
        try:
            with open(config.CUSTOM_HOLIDAYS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def salvar_feriados_custom(lista_datas):
    """Salva a lista de feriados personalizados no arquivo JSON."""
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    with open(config.CUSTOM_HOLIDAYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(lista_datas)), f, indent=4)


# =============================================================================
# FUNÇÕES DE DATA E CÁLCULO
# =============================================================================

def str_to_date(data_str):
    """Converte string 'YYYY-MM-DD' para objeto datetime. Retorna None se inválido."""
    if not data_str or pd.isna(data_str) or str(data_str).strip() == "":
        return None
    try:
        return datetime.strptime(str(data_str)[:10], '%Y-%m-%d')
    except:
        return None


def date_to_str(data_obj):
    """Converte objeto datetime para string 'YYYY-MM-DD'. Retorna '' se None."""
    return data_obj.strftime('%Y-%m-%d') if data_obj else ""


def adicionar_dias_uteis(data_inicio, dias, feriados_extras=None, ferias_responsavel=None, block_weekends=True):
    """
    Soma dias a uma data, com opção de ignorar fins de semana, feriados e férias.
    """
    if not data_inicio:
        return None
    try:
        dias_para_adicionar = int(dias)
    except:
        dias_para_adicionar = 0

    if feriados_extras is None:
        feriados_extras = set()
    
    if ferias_responsavel is None:
        ferias_responsavel = []

    data_atual = data_inicio
    dias_adicionados = 0

    while dias_adicionados < dias_para_adicionar:
        data_atual += timedelta(days=1)
        data_str = data_atual.strftime('%Y-%m-%d')

        if block_weekends and data_atual.weekday() >= 5:
            continue
        
        if data_atual in br_holidays or data_str in br_holidays:
            continue
        
        if data_str in feriados_extras:
            continue
        
        em_ferias = False
        for periodo in ferias_responsavel:
            inicio_ferias = str_to_date(periodo['inicio'])
            fim_ferias = str_to_date(periodo['fim'])
            if inicio_ferias and fim_ferias and inicio_ferias <= data_atual <= fim_ferias:
                em_ferias = True
                break
        if em_ferias:
            continue

        dias_adicionados += 1

    return data_atual
