# run_migrations.py
import os
import psycopg2
from app import config

def run_migrations():
    """
    Executa os scripts de migração do banco de dados em ordem,
    controlando as migrações já executadas.
    """
    conn = psycopg2.connect(config.DATABASE_URI)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Garante que a tabela de controle de migrações exista
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY
            );
        """)

        # Obtém a lista de migrações já executadas
        cur.execute("SELECT version FROM schema_migrations")
        executed_migrations = {row[0] for row in cur.fetchall()}

        migrations_dir = 'migrations/versions'
        for filename in sorted(os.listdir(migrations_dir)):
            if filename.endswith('.sql'):
                if filename not in executed_migrations:
                    with open(os.path.join(migrations_dir, filename), 'r', encoding='utf-8') as f:
                        cur.execute(f.read())
                        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (filename,))
                        print(f'Migração {filename} executada e registrada com sucesso.')
                else:
                    print(f'Migração {filename} já foi executada.')
    conn.close()

if __name__ == '__main__':
    run_migrations()
