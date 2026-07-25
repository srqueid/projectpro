# app/database.py
import psycopg2
import psycopg2.extras
from flask import g
from . import config

def get_db():
    """
    Abre uma nova conexão com o banco de dados se não houver uma para a requisição atual.
    A conexão é armazenada no objeto 'g' do Flask, que é único para cada requisição.
    """
    if 'db' not in g:
        g.db = psycopg2.connect(config.DATABASE_URI)
    return g.db

def close_db(e=None):
    """
    Fecha a conexão com o banco de dados ao final da requisição.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """
    Registra o comando 'init-db' e a função de fechamento do banco de dados com a aplicação Flask.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

from click import command

@command('init-db')
def init_db_command():
    """Cria as tabelas do banco de dados."""
    import psycopg2
    from . import config
    conn = psycopg2.connect(config.DATABASE_URI)
    conn.autocommit = True
    with conn.cursor() as cur:
        with open('schema.sql', 'r') as f:
            cur.execute(f.read())
    conn.close()
    print('Banco de dados inicializado.')
