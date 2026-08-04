import psycopg2
from app import config

conn = psycopg2.connect(config.DATABASE_URI)
cur = conn.cursor()
cur.execute(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
    "ORDER BY table_schema, table_name"
)
for r in cur.fetchall():
    print(r)
conn.close()

