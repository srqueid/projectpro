# app/__init__.py
import os
from flask import Flask
from . import config, database, migrations

def create_app():
    """
    Cria e configura uma instância da aplicação Flask.
    """
    app = Flask(__name__, static_folder='../static', template_folder='../templates')

    # --- CONFIGURAÇÕES ---
    app.config['SECRET_KEY'] = config.SECRET_KEY
    
    # --- INICIALIZAÇÃO DO BANCO DE DADOS ---
    database.init_app(app)

    # --- EXECUTAR MIGRAÇÕES DO BANCO DE DADOS ---
    with app.app_context():
        try:
            migrations.executar_migracoes()
        except Exception as e:
            print(f"[MIGRAÇÕES] Erro ao executar migrações: {e}")

    # --- GARANTIR QUE AS PASTAS EXISTAM ---
    os.makedirs(config.PROJECTS_FOLDER, exist_ok=True)
    os.makedirs(config.DATA_FOLDER, exist_ok=True)

    # --- REGISTRAR BLUEPRINTS ---
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
