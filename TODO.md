# TODO - Correções de Bugs e Melhorias (CONCLUÍDO)

## ✅ Passos Concluídos
- [x] **Bug 1 (Planilha):** Adicionar hidden field `kanban_coluna_id` no template Jinja2 `planilha.html` — estava faltando, causando `return` prematuro em `handleInicioChange()`
- [x] **Bug 1 (Planilha):** Corrigir `handleInicioChange()` em `planilha.js` — remover `if (!kanbanColunaInput) return;` e forçar `detectarMudanca(true)` sempre que data de início mudar
- [x] **Bug 2 (Kanban):** Expandir modal "Nova Tarefa" em `templates/kanban.html` com todos os campos: fase, subtarefa, responsável, dias, início, fim, conclusão, descrição
- [x] **Bug 2 (Kanban):** Atualizar `static/kanban.js` para enviar todos os novos campos no submit do formulário
- [x] **Migração Tailwind CDN → Build Local** (pacote anterior)
- [x] **Correção CSS `planilha.css`** (pacote anterior)

