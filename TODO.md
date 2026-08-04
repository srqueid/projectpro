# TODO — Migração para Schemas por Domínio

Objetivo: separar o banco em schemas por domínio, sem utilizar o schema `public`.

## Schema Mapping

| Schema | Tabelas |
|--------|---------|
| `rh` | `responsaveis`, `ferias`, `times`, `responsaveis_times` |
| `projeto` | `projetos`, `tarefas`, `kanban_colunas`, `tarefa_atividades`, `projeto_configuracoes` |
| `config` | `configuracoes`, `feriados_customizados` |

## Steps

- [x] 1. `app/config.py` — Adicionar constantes de schemas (`SCHEMA_RH`, `SCHEMA_PROJETO`, `SCHEMA_CONFIG`).
- [x] 2. `app/database.py` — Configurar `search_path` após conectar.
- [x] 3. `schema.sql` — Criar schemas e qualificar todas as tabelas.
- [ ] 4. `app/migrations.py` — Filtrar por `table_schema` e qualificar `ALTER TABLE`.
- [ ] 5. `app/project_manager.py` — Qualificar todas as queries SQL.
- [ ] 6. `app/routes.py` — Qualificar query em `planejar_tarefa`.
- [ ] 7. `tests/test_project_manager.py` — Atualizar mocks para schemas qualificados.
- [ ] 8. `README.md` — Documentar a nova estrutura.
- [ ] 9. Teste final (executar testes unitários).

