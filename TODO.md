# ✅ TODAS AS MELHORIAS IMPLEMENTADAS

## Hierarquia: Épico > Feature > História > Tarefa > Subtarefa
- ✅ `app/routes.py` - Filtros `features`/`subtasks` em `detalhes_projeto`
- ✅ `templates/detalhes_projeto.html` - CSS badges, stats 6 colunas, seções, modal hierárquico
- ✅ `templates/backlog.html` - Badges e filtros expandidos

## Fluxo de Transição entre Colunas Kanban
- ✅ `app/migrations.py` - Coluna `allow_back` adicionada
- ✅ `app/project_manager.py` - `carregar_kanban_config()`/`salvar_kanban_config()` com `allow_back`
- ✅ `app/project_manager.py` - `replanejar_tarefa()` + `mover_card_kanban()` com validação de fluxo
- ✅ `app/routes.py` - Rota `/kanban_replanejar`
- ✅ `static/kanban.js` - Validação `allow_back` no drag-and-drop, checkbox na config
- ✅ `templates/kanban.html` - Botão config colunas, dialog replanejar


