import psycopg2
from app import config

# Mapeamento tabela -> schema de destino
MAP = {
    'responsaveis': 'rh',
    'ferias': 'rh',
    'times': 'rh',
    'responsaveis_times': 'rh',
    'projetos': 'projeto',
    'tarefas': 'projeto',
    'kanban_colunas': 'projeto',
    'tarefa_atividades': 'projeto',
    'projeto_configuracoes': 'projeto',
    'configuracoes': 'config',
    'feriados_customizados': 'config',
}

conn = psycopg2.connect(config.DATABASE_URI)
conn.autocommit = True
cur = conn.cursor()

for tabela, schema in MAP.items():
    # Obtém colunas da tabela de origem (public) na ordem definida do schema
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (tabela,)
    )
    colunas = [r[0] for r in cur.fetchall()]
    if not colunas:
        print(f"AVISO: tabela public.{tabela} sem colunas encontradas.")
        continue

    cols_sql = ", ".join(f'"{c}"' for c in colunas)
    cur.execute(
        f'INSERT INTO {schema}.{tabela} ({cols_sql}) SELECT {cols_sql} FROM public.{tabela} ON CONFLICT DO NOTHING;'
    )
    # Imprime quantas linhas foram inseridas
    cur.execute(f'SELECT COUNT(*) FROM {schema}.{tabela}')
    n = cur.fetchone()[0]
    print(f"Migrado public.{tabela} -> {schema}.{tabela} ({n} linhas)")

conn.close()
print("Migração de dados concluída.")

