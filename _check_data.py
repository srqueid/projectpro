import psycopg2
from app import config

conn = psycopg2.connect(config.DATABASE_URI)
cur = conn.cursor()
tables = ['responsaveis', 'ferias', 'times', 'responsaveis_times', 'projetos', 'tarefas', 'kanban_colunas', 'tarefa_atividades', 'projeto_configuracoes', 'configuracoes', 'feriados_customizados']
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM public.{t}")
    pub_cnt = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM config.{t}") if False else None
    # map to schema
    schema = 'rh' if t in ('responsaveis','ferias','times','responsaveis_times') else ('config' if t in ('configuracoes','feriados_customizados') else 'projeto')
    cur.execute(f"SELECT COUNT(*) FROM {schema}.{t}")
    new_cnt = cur.fetchone()[0]
    print(f"{t}: public={pub_cnt}, {schema}={new_cnt}")
conn.close()
