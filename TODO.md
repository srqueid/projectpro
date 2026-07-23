# TODO: Separar CSS e JS em arquivos únicos por página

## Etapas

### 1. Criar arquivos CSS e JS em `static/`
- [x] `static/base.css` - Estilos da sidebar (transições)
- [x] `static/base.js` - Função toggleSidebar
- [x] `static/kanban.css` - Todos os estilos Kanban
- [x] `static/kanban.js` - JavaScript Kanban (Sortable, mover cards, config modal)
- [x] `static/cronograma.css` - Estilos do Gantt (cronograma)
- [x] `static/cronograma.js` - JavaScript do Gantt (renderização, zoom, fullscreen)
- [x] `static/planilha.css` - Estilos da planilha
- [x] `static/planilha.js` - JavaScript da planilha (Sortable, ordenação, recálculo, salvar)
- [x] `static/home.css` - Estilos da página inicial
- [x] `static/home.js` - JavaScript da página inicial (toggleUpload)
- [x] `static/feriados.css` - Estilos da página de feriados

### 2. Editar templates para usar os arquivos externos
- [x] `templates/base.html` - Substituir `<style>` e `<script>` inline por referências externas
- [x] `templates/kanban.html` - Mover CSS/JS inline para arquivos externos (manter variáveis Jinja inline)
- [x] `templates/cronograma.html` - Mover CSS/JS inline para arquivos externos
- [x] `templates/planilha.html` - Mover CSS/JS inline para arquivos externos
- [x] `templates/home.html` - Mover CSS/JS inline para arquivos externos
- [x] `templates/feriados.html` - Adicionar CSS externo

### 3. Verificar funcionamento
- [x] Executar a aplicação e testar as páginas
- [x] Verificar se não há erros no console

