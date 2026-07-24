# TODO

## Fix: Planilha page "tbody is null" error

### Root Cause
- `templates/planilha.html` had a placeholder comment `<!-- ... -->` instead of the actual table HTML (`<table>`, `<thead id="header-row">`, `<tbody id="tabela-corpo">`)
- `static/planilha.js` referenced `document.getElementById('tabela-corpo')` which returned `null`
- Missing `.progress-bar` CSS class

### Completed
- [x] `templates/planilha.html` - Replaced placeholder with complete table structure (thead with sortable columns, tbody with existing task rows)
- [x] `static/planilha.css` - Added `.progress-bar` style
- [x] `static/planilha.js` - Fixed `ordenar()` function to safely use `window.event` instead of implicit `event` parameter

