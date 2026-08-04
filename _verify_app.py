from app import create_app
from app import project_manager, database

app = create_app()
with app.app_context():
    db = database.get_db()
    with db.cursor() as cur:
        cur.execute("SHOW search_path")
        print("search_path:", cur.fetchone()[0])

    resp = project_manager.carregar_responsaveis()
    print("responsaveis:", len(resp))

    projs = project_manager.carregar_projetos()
    print("projetos:", len(projs))

    settings = project_manager.carregar_settings()
    print("settings:", settings)

    times = project_manager.carregar_times()
    print("times:", len(times))

    if projs:
        pid = projs[0]['id']
        tarefas = project_manager.carregar_tarefas(pid)
        print(f"tarefas do projeto {pid}:", len(tarefas))
