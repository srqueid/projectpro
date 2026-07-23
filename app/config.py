# app/config.py
import os

# Obtém o diretório base do projeto (a pasta acima de 'app')
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# --- CAMINHOS DE PASTAS E ARQUIVOS ---
PROJECTS_FOLDER = os.path.join(BASE_DIR, 'projects')
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
CUSTOM_HOLIDAYS_FILE = os.path.join(DATA_FOLDER, 'feriados_customizados.json')
KANBAN_CONFIG_FILE_SUFFIX = 'kanban_config.json'

# --- CONFIGURAÇÃO DA APLICAÇÃO ---
SECRET_KEY = 'segredo_desenvolvimento'

# --- BANCO DE DADOS ---
# A string de conexão para o banco de dados PostgreSQL.
# Em um ambiente de produção, isso deve vir de uma variável de ambiente.
DATABASE_URI = "postgresql://neondb_owner:npg_pYhAFkeXC54Q@ep-odd-scene-an5fvex7-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# --- FERIADOS ---
# Lista de feriados usada como fallback se a biblioteca 'holidays' não estiver instalada
MANUAL_HOLIDAYS = {
    '2025-01-01', '2025-03-03', '2025-03-04', '2025-04-18', '2025-04-21',
    '2025-05-01', '2025-06-19', '2025-09-07', '2025-10-12', '2025-11-02',
    '2025-11-15', '2025-11-20', '2025-12-25',
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03', '2026-04-21',
    '2026-05-01', '2026-06-04', '2026-09-07', '2026-10-12', '2026-11-02',
    '2026-11-15', '2026-11-20', '2026-12-25'
}
