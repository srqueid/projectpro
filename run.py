# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # use_reloader=False é útil para evitar problemas com recarregamento duplo
    # em alguns ambientes de desenvolvimento.
    app.run(debug=True, use_reloader=False, port=5051)
