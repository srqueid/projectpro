"""
seed_demo.py
===========

Popula o banco com dados mocados (idempotentes) para testar:
  - 1 Empresa DEMO
  - 1 Projeto ("GTI - Atividades (DEMO)")
  - 3 Épicos completos (com Features > Histórias > Tarefas > Subtarefas)
  - Tarefas Extraordinárias direto nos épicos
  - Responsáveis / Times / vínculados
  - Configurações de Kanban

Como usar:
  python seed_demo.py

Idempotente: se já existir empresa com CNPJ '00.000.000/0001-00' e projeto
'GTI_-_DEMO', apaga a árvore antiga e a recria (exclusão em cascata).
"""

from __future__ import annotations

import uuid
import sys
from dataclasses import dataclass, field
from typing import Iterable

from app import create_app, database, project_manager

CNPJ_DEMO = "00.000.000/0001-00"
PROJETO_ID_DEMO = "GTI_-_DEMO"
EMPRESA_NOME = "Empresa DEMO - ProjectPro"
NOME_PROJETO = "GTI - Atividades (DEMO)"


@dataclass
class Sub:
    titulo: str

@dataclass
class Tarefa:
    titulo: str
    descricao: str = ""
    responsavel: str | None = None
    sprint: str | None = None
    subtarefas: Iterable[Sub] = field(default_factory=tuple)
    extraordinaria: bool = False
    dias: int = 1

@dataclass
class Historia:
    titulo: str
    pontos: int = 0
    descricao: str = ""
    tarefas: Iterable[Tarefa] = field(default_factory=tuple)

@dataclass
class Feature:
    titulo: str
    descricao: str = ""
    historias: Iterable[Historia] = field(default_factory=tuple)

@dataclass
class Epico:
    titulo: str
    descricao: str = ""
    features: Iterable[Feature] = field(default_factory=tuple)
    tarefas_extra: Iterable[Tarefa] = field(default_factory=tuple)


ARVORE = [
    Epico(
        titulo="Modernizacao do Portal do Cliente",
        descricao="Migracao e reformulacao completa do legado para nova arquitetura SPA",
        features=[
            Feature(
                titulo="Autenticacao e SSO",
                descricao="Integracao AD + OAuth2",
                historias=[
                    Historia(
                        titulo="Tela de Login responsiva",
                        pontos=5,
                        tarefas=[
                            Tarefa("Wireframes mobile-first", sprint="Sprint 1", responsavel="ana", subtarefas=[
                                Sub("Pesquisa de referencias"),
                                Sub("Prototipo em Figma"),
                                Sub("Validacao PO"),
                            ]),
                            Tarefa("Aplicar Tailwind no HTML", sprint="Sprint 1", responsavel="carlos"),
                            Tarefa("Testes de acessibilidade WCAG", sprint="Sprint 2", responsavel="ana"),
                        ],
                    ),
                    Historia(
                        titulo="Integracao OAuth2 (Google / Microsoft)",
                        pontos=8,
                        descricao="Fluxo authorization code + PKCE",
                        tarefas=[
                            Tarefa("Configurar client_id e secrets no Keycloak", sprint="Sprint 1", responsavel="bruno", dias=2),
                            Tarefa("Implementar callback", sprint="Sprint 2", responsavel="bruno", subtarefas=[
                                Sub("Handler /auth/callback"),
                                Sub("Trocar code por access_token"),
                                Sub("Criar sessao JWT local"),
                            ]),
                        ],
                    ),
                ],
            ),
            Feature(
                titulo="Dashboard Analytics",
                historias=[
                    Historia(
                        titulo="Widgets de KPIs",
                        pontos=3,
                        tarefas=[
                            Tarefa("Card de Total de Projetos", sprint="Sprint 2", responsavel="carla"),
                            Tarefa("Grafico de Gantt resumido", sprint="Sprint 2", responsavel="carlos", subtarefas=[
                                Sub("Biblioteca de graficos"),
                                Sub("Datas baseline"),
                            ]),
                        ],
                    )
                ],
            ),
        ],
        tarefas_extra=[
            Tarefa("Reuniao kick-off com cliente", extraordinaria=True, sprint="Sprint 1"),
            Tarefa("Treinamento equipe em OAuth2", extraordinaria=True, responsavel="bruno"),
        ],
    ),
    Epico(
        titulo="Migracao para Nuvem",
        descricao="Onboarding de infraestrutura AWS + CI/CD",
        features=[
            Feature(
                titulo="Pipeline CI/CD",
                historias=[
                    Historia(
                        titulo="Build e testes automatizados",
                        pontos=5,
                        tarefas=[
                            Tarefa("Configurar GitHub Actions", sprint="Sprint 1", responsavel="bruno"),
                            Tarefa("SonarQube quality gate", sprint="Sprint 2", responsavel="bruno"),
                        ],
                    ),
                ],
            ),
            Feature(
                titulo="Terraform - VPC e RDS",
                historias=[
                    Historia(
                        titulo="Modulos compartilhados",
                        pontos=8,
                        tarefas=[
                            Tarefa("Sub-redes publicas/privadas", sprint="Sprint 1", responsavel="carla", subtarefas=[
                                Sub("Availability zones"),
                                Sub("Route tables"),
                                Sub("NAT gateway"),
                            ]),
                            Tarefa("Provisionar RDS PostgreSQL", sprint="Sprint 2", responsavel="carla"),
                            Tarefa("Backup automatico", sprint="Sprint 2", responsavel="carla"),
                        ],
                    ),
                ],
            ),
        ],
        tarefas_extra=[
            Tarefa("Planejar cutover", extraordinaria=True),
            Tarefa("Backout Plan", extraordinaria=True, sprint="Sprint 2"),
        ],
    ),
    Epico(
        titulo="App Mobile - MVP",
        descricao="Aplicativo React Native para visualizacao de tarefas",
        features=[
            Feature(
                titulo="Telas Basicas",
                historias=[
                    Historia(
                        titulo="Login e Tarefas",
                        pontos=8,
                        tarefas=[
                            Tarefa("Setup Expo / RN", sprint="Sprint 1", responsavel="carlos", subtarefas=[
                                Sub("Configurar EAS"),
                                Sub("Build Android"),
                            ]),
                            Tarefa("Lista de tarefas do usuario", sprint="Sprint 2", responsavel="ana"),
                        ],
                    )
                ],
            )
        ],
        tarefas_extra=[
            Tarefa("Publicar APK na Play Store (beta)", extraordinaria=True, sprint="Sprint 2"),
        ],
    ),
]


RESPONSAVEIS_DEMO = [
    {"matricula": "MAT-001", "nome": "Ana Silva",      "cargo": "UX Designer", "email": "ana@demo.local",     "cor": "#7c3aed"},
    {"matricula": "MAT-002", "nome": "Bruno Costa",    "cargo": "Backend Dev",  "email": "bruno@demo.local",   "cor": "#059669"},
    {"matricula": "MAT-003", "nome": "Carla Mendes",   "cargo": "DevOps",       "email": "carla@demo.local",   "cor": "#2563eb"},
    {"matricula": "MAT-004", "nome": "Carlos Eduardo", "cargo": "Frontend Dev", "email": "carlos@demo.local",  "cor": "#c2410c"},
]

TIMES_DEMO = ["Design", "Backend", "Frontend", "DevOps"]


# ---------------------------------------------------------------- helpers

def _limpar_dados_demo(db, empresa_id, projeto_id):
    with db.cursor() as cur:
        cur.execute("DELETE FROM projeto.work_items WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.subtarefas WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.tarefas_hierarquicas WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.historias WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.features WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.epicos WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM projeto.projetos WHERE id = %s AND empresa_id = %s", (projeto_id, empresa_id))
        cur.execute("DELETE FROM rh.responsaveis_times rt USING rh.responsaveis r WHERE r.id = rt.responsavel_id AND r.empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM rh.responsaveis WHERE empresa_id = %s", (empresa_id,))
        cur.execute("DELETE FROM rh.times WHERE empresa_id = %s", (empresa_id,))
    db.commit()


def _upsert_empresa(db):
    with db.cursor() as cur:
        cur.execute("SELECT id FROM core.empresas WHERE cnpj = %s", (CNPJ_DEMO,))
        row = cur.fetchone()
        if row:
            return str(row[0])
        empresa_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO core.empresas (id, nome, cnpj, ativo) VALUES (%s, %s, %s, TRUE) RETURNING id",
            (empresa_id, EMPRESA_NOME, CNPJ_DEMO),
        )
        db.commit()
        return str(cur.fetchone()[0])


def _criar_projeto(db, empresa_id):
    with db.cursor() as cur:
        cur.execute("SELECT id FROM projeto.projetos WHERE id = %s AND empresa_id = %s", (PROJETO_ID_DEMO, empresa_id))
        if cur.fetchone():
            return PROJETO_ID_DEMO
        cur.execute(
            "INSERT INTO projeto.projetos (id, empresa_id, nome, descricao) VALUES (%s, %s, %s, %s)",
            (PROJETO_ID_DEMO, empresa_id, NOME_PROJETO, "Projeto demonstrativo com dados mocados"),
        )
        db.commit()
        return PROJETO_ID_DEMO


def _criar_times_e_responsaveis(db, empresa_id):
    mapa_times = {}
    nome_map = {}
    with db.cursor() as cur:
        for nome_time in TIMES_DEMO:
            tid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO rh.times (id, empresa_id, nome) VALUES (%s, %s, %s) RETURNING id",
                (tid, empresa_id, nome_time),
            )
            mapa_times[nome_time] = tid
        for r in RESPONSAVEIS_DEMO:
            rid = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO rh.responsaveis
                    (id, empresa_id, nome, email, perfil)
                VALUES (%s, %s, %s, %s, 'executor')
                RETURNING id, nome
                """,
                (rid, empresa_id, r["nome"], r["email"]),
            )
            primeiro = r["nome"].split()[0].lower()
            nome_map[primeiro] = str(rid)
        vinculos = [
            ("ana", "Design"), ("bruno", "Backend"),
            ("carla", "DevOps"), ("carlos", "Frontend"),
            ("bruno", "DevOps"),
        ]
        for primeiro_nome, nome_time in vinculos:
            rid = nome_map.get(primeiro_nome)
            tid = mapa_times.get(nome_time)
            if rid and tid:
                cur.execute(
                    "INSERT INTO rh.responsaveis_times (responsavel_id, time_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (rid, tid),
                )
    db.commit()
    return nome_map


def _montar_arvore(empresa_id, projeto_id, resp_por_nome):
    cont_ep = cont_ft = cont_hs = cont_tk = cont_sb = 0
    for ep in ARVORE:
        epico_id = project_manager.adicionar_epico(empresa_id, projeto_id, ep.titulo, ep.descricao)
        cont_ep += 1
        # Tarefas extraordinárias
        for tex in ep.tarefas_extra:
            rid = resp_por_nome.get(tex.responsavel) if tex.responsavel else None
            tid = project_manager.adicionar_tarefa_hierarquica(
                empresa_id, epico_id, None, tex.titulo,
                is_extraordinaria=True, descricao=tex.descricao,
                responsavel_id=rid, dias=tex.dias, sprint=tex.sprint,
            )
            cont_tk += 1
            for sub in tex.subtarefas:
                project_manager.adicionar_subtarefa(empresa_id, epico_id, tid, sub.titulo)
                cont_sb += 1
        # Features
        for ft in ep.features:
            ft_id = project_manager.adicionar_feature(empresa_id, epico_id, ft.titulo, ft.descricao)
            cont_ft += 1
            for hs in ft.historias:
                hs_id = project_manager.adicionar_historia(empresa_id, epico_id, ft_id, hs.titulo, hs.descricao, hs.pontos)
                cont_hs += 1
                for tk in hs.tarefas:
                    rid = resp_por_nome.get(tk.responsavel) if tk.responsavel else None
                    tk_id = project_manager.adicionar_tarefa_hierarquica(
                        empresa_id, epico_id, hs_id, tk.titulo,
                        is_extraordinaria=False, descricao=tk.descricao,
                        responsavel_id=rid, dias=tk.dias, sprint=tk.sprint,
                    )
                    cont_tk += 1
                    for sb in tk.subtarefas:
                        project_manager.adicionar_subtarefa(empresa_id, epico_id, tk_id, sb.titulo)
                        cont_sb += 1
    return cont_ep, cont_ft, cont_hs, cont_tk, cont_sb


# ---------------------------------------------------------------- main

def main() -> int:
    app = create_app()
    with app.app_context():
        db = database.get_db()
        with db.cursor() as cur:
            cur.execute("SELECT set_config('app.current_empresa_id', NULL, false)")

        empresa_id = _upsert_empresa(db)
        print("[SEED] Empresa DEMO id =", empresa_id)

        _limpar_dados_demo(db, empresa_id, PROJETO_ID_DEMO)
        print("[SEED] Dados anteriores limpos.")

        projeto_id = _criar_projeto(db, empresa_id)
        print("[SEED] Projeto id =", projeto_id)

        resp_por_nome = _criar_times_e_responsaveis(db, empresa_id)
        print("[SEED] Responsaveis criados:", list(resp_por_nome.keys()))

        cont_ep, cont_ft, cont_hs, cont_tk, cont_sb = _montar_arvore(empresa_id, projeto_id, resp_por_nome)
        print("[SEED] Arvore montada:")
        print(f"       - {cont_ep} epico(s)")
        print(f"       - {cont_ft} feature(s)")
        print(f"       - {cont_hs} historia(s)")
        print(f"       - {cont_tk} tarefa(s)")
        print(f"       - {cont_sb} subtarefa(s)")

        kanban_config = project_manager.carregar_kanban_config(projeto_id)
        print(f"[SEED] Kanban com {len(kanban_config.get('colunas', []))} colunas.")

        print("\n[SEED CONCLUIDO]")
        print(f" Acesse a hierarquia em:  /empresa/{empresa_id}/projeto/{projeto_id}/hierarquia")
        print(f" Equipe DEMO: " + ", ".join(r["nome"] for r in RESPONSAVEIS_DEMO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
