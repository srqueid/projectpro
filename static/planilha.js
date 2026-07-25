// ============================================================
//  PLANILHA (SPREADSHEET) - AUTOSAVE & UNDO
// ============================================================

// --- VARIÁVEIS GLOBAIS ---
const tbody = document.getElementById('tabela-corpo');
const theadRow = document.getElementById('header-row');
const statusDisplay = document.getElementById('save-status');
const undoButton = document.getElementById('btn-undo');

let undoStack = [];
let saveTimeout = null;
let recalculateTimeout = null;

// --- INICIALIZAÇÃO ---
document.addEventListener('DOMContentLoaded', () => {
    initSortable();
    pushToUndoStack(initialTasks);
    verificarConflitosDeFerias(); // Verificação inicial
});

function initSortable() {
    new Sortable(tbody, { handle: '.handle', animation: 150, onEnd: () => detectarMudanca(true) });
    new Sortable(theadRow, { animation: 150, filter: '.no-drag', ghostClass: 'column-ghost', onEnd: (evt) => {
        if (evt.oldIndex === evt.newIndex) return;
        tbody.querySelectorAll('tr').forEach(row => {
            const cells = Array.from(row.children);
            row.insertBefore(cells[evt.oldIndex], cells[evt.newIndex]);
        });
    }});
}

// --- LÓGICA DE SALVAMENTO E DESFAZER ---

function pushToUndoStack(tasks) {
    undoStack.push(JSON.parse(JSON.stringify(tasks)));
    updateUndoButton();
}

async function desfazer() {
    if (undoStack.length <= 1) return;
    undoStack.pop();
    const prevState = undoStack[undoStack.length - 1];
    renderTable(prevState);
    await salvarTudo(false);
    updateUndoButton();
    verificarConflitosDeFerias();
}

function updateUndoButton() {
    undoButton.classList.toggle('hidden', undoStack.length <= 1);
}

function detectarMudanca(forceRecalculate = false) {
    setStatus('Modificado...', 'text-amber-600');
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        salvarTudo(true);
        if (forceRecalculate) autoRecalcular();
    }, 1500);

    if (forceRecalculate) {
        if (recalculateTimeout) clearTimeout(recalculateTimeout);
        recalculateTimeout = setTimeout(autoRecalcular, 600);
    }
    verificarConflitosDeFerias();
}

async function salvarTudo(addToUndo = true) {
    setStatus('Salvando...', 'text-blue-600');
    const tasks = getTasksFromTable();
    if (addToUndo) pushToUndoStack(tasks);

    try {
        const response = await fetch(projectSalvarUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(tasks)
        });
        if (response.ok) setStatus('Salvo', 'text-emerald-600');
        else {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.mensagem || `Falha ao salvar (HTTP ${response.status})`);
        }
    } catch (e) {
        console.error("Erro ao salvar:", e);
        setStatus('Erro!', 'text-red-600');
        alert(e.message);
    }
}

function setStatus(text, colorClass) {
    statusDisplay.textContent = text;
    statusDisplay.className = `text-xs font-medium transition-all ${colorClass}`;
}

function handleConclusionChange(input) {
    const tr = input.closest('tr');
    const fimInput = tr.querySelector('[name="fim"]');
    if (input.value == 100 && !fimInput.value) {
        const hoje = new Date().toISOString().split('T')[0];
        fimInput.value = hoje;
    }
    detectarMudanca(true);
}

// --- VERIFICAÇÃO DE CONFLITO DE FÉRIAS ---

function verificarConflitosDeFerias() {
    const mapaResponsaveis = responsaveis.reduce((map, r) => {
        map[r.id] = r.ferias || [];
        return map;
    }, {});

    tbody.querySelectorAll('tr').forEach(tr => {
        const responsavelId = tr.querySelector('[name="responsavel"]').value;
        const ferias = mapaResponsaveis[responsavelId] || [];

        const inicioTarefa = new Date(tr.querySelector('[name="inicio"]').value);
        const fimTarefa = new Date(tr.querySelector('[name="fim"]').value);

        let conflito = false;
        if (responsavelId && !isNaN(inicioTarefa) && !isNaN(fimTarefa)) {
            for (const periodo of ferias) {
                const inicioFerias = new Date(periodo.inicio);
                const fimFerias = new Date(periodo.fim);
                if (!isNaN(inicioFerias) && !isNaN(fimFerias)) {
                    if (inicioTarefa <= fimFerias && fimTarefa >= inicioFerias) {
                        conflito = true;
                        break;
                    }
                }
            }
        }

        ['inicio', 'fim', 'baseline_inicio', 'baseline_fim'].forEach(name => {
            const input = tr.querySelector(`[name="${name}"]`);
            const alertIcon = input.nextElementSibling;
            if (conflito) {
                input.classList.add('date-conflict');
                if(alertIcon) alertIcon.classList.remove('hidden');
            } else {
                input.classList.remove('date-conflict');
                if(alertIcon) alertIcon.classList.add('hidden');
            }
        });
    });
}


// --- MANIPULAÇÃO DA TABELA ---

function getTasksFromTable() {
    return Array.from(tbody.querySelectorAll('tr')).map(tr => {
        const get = (name) => {
            const el = tr.querySelector(`[name="${name}"]`);
            if (!el) return null;
            const v = el.value;
            return v === '' ? null : v;
        };
        return {
            id: tr.dataset.id, fase: get('fase'), modulo: get('modulo'), tarefa: get('tarefa'),
            subtarefa: get('subtarefa'), inicio: get('inicio'), dias: get('dias'), fim: get('fim'),
            predecessora: get('predecessora'), baseline_inicio: get('baseline_inicio'),
            baseline_fim: get('baseline_fim'), responsavel_id: get('responsavel'), conclusao: get('conclusao'),
            kanban_coluna_id: get('kanban_coluna_id')
        };
    });
}

function renderTable(tasks) {
    tbody.innerHTML = '';
    tasks.forEach(task => {
        const row = document.createElement('tr');
        row.className = 'group transition-colors';
        row.dataset.id = task.id;
        row.innerHTML = createTaskRowHtml(task);
        tbody.appendChild(row);
    });
    verificarConflitosDeFerias();
}

function adicionarLinhaVazia() {
    const ids = Array.from(tbody.querySelectorAll('tr')).map(tr => parseInt(tr.dataset.id));
    const novoId = (ids.length > 0 ? Math.max(...ids) : 0) + 1;
    const novaTarefa = { id: novoId, dias: 1, conclusao: 0, kanban_coluna_id: 'backlog' };
    const row = document.createElement('tr');
    row.className = 'group transition-colors';
    row.dataset.id = novoId;
    row.innerHTML = createTaskRowHtml(novaTarefa);
    tbody.appendChild(row);
    detectarMudanca(true);
    row.querySelector('[name="tarefa"]').focus();
    row.scrollIntoView({ behavior: 'smooth' });
}

function createTaskRowHtml(t) {
    const responsaveisOptions = responsaveis.map(r =>
        `<option value="${r.id}" ${r.id === t.responsavel_id ? 'selected' : ''}>${r.nome}</option>`
    ).join('');

    return `
        <td class="p-0 align-middle text-center handle border-r no-print"><div class="h-full flex items-center justify-center cursor-grab">⋮⋮</div></td>
        <td class="p-0 text-center text-xs font-mono border-r">${t.id}</td>
        <td class="p-0 border-r"><input name="fase" value="${t.fase || ''}" class="sheet-input" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input name="tarefa" value="${t.tarefa || 'Nova Tarefa'}" class="sheet-input" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input name="subtarefa" value="${t.subtarefa || ''}" class="sheet-input" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r bg-blue-50/30"><input type="date" name="baseline_inicio" value="${t.baseline_inicio || ''}" class="sheet-input text-center" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input type="number" name="dias" value="${t.dias || 1}" class="sheet-input text-center" oninput="detectarMudanca(true)"></td>
        <td class="p-0 border-r bg-blue-50/30"><input type="date" name="baseline_fim" value="${t.baseline_fim || ''}" class="sheet-input text-center" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input name="predecessora" value="${t.predecessora || ''}" class="sheet-input text-center" oninput="detectarMudanca(true)"></td>
        <td class="p-0 border-r bg-amber-50/30 relative"><input type="date" name="inicio" value="${t.inicio || ''}" class="sheet-input text-center" oninput="detectarMudanca(true)"><span class="date-alert-icon hidden" title="Conflito com férias!">⚠️</span></td>
        <td class="p-0 border-r bg-amber-50/30 relative"><input type="date" name="fim" value="${t.fim || ''}" class="sheet-input text-center" oninput="detectarMudanca(true)"><span class="date-alert-icon hidden" title="Conflito com férias!">⚠️</span></td>
        <td class="p-0 border-r"><select name="responsavel" class="sheet-input" oninput="detectarMudanca(true)"><option value="">Nenhum</option>${responsaveisOptions}</select></td>
        <td class="p-0 border-r relative"><div class="progress-bar" style="width: ${t.conclusao || 0}%;"></div><input type="number" name="conclusao" value="${t.conclusao || 0}" class="sheet-input text-center" oninput="handleConclusionChange(this)"></td>
        <td class="p-0 text-center no-print"><button onclick="this.closest('tr').remove(); detectarMudanca(true)" class="w-full h-full text-gray-300 hover:text-red-500">✕</button><input type="hidden" name="modulo" value="${t.modulo || ''}"><input type="hidden" name="kanban_coluna_id" value="${t.kanban_coluna_id || 'backlog'}"></td>
    `;
}

// --- RECÁLCULO E ORDENAÇÃO ---
async function autoRecalcular() {
    tbody.classList.add('recalculando');
    try {
        const response = await fetch(projectRecalcularUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(getTasksFromTable())
        });
        if (response.ok) {
            const result = await response.json();
            if (result.status === 'sucesso' && result.dados) {
                result.dados.forEach(item => {
                    const tr = tbody.querySelector(`tr[data-id="${item.id}"]`);
                    if (tr) {
                        tr.querySelector('[name="inicio"]').value = item.inicio;
                        tr.querySelector('[name="fim"]').value = item.fim;
                    }
                });
                detectarMudanca(false);
            }
        }
    } catch (e) {
        console.error("Erro no recálculo:", e);
    } finally {
        tbody.classList.remove('recalculando');
    }
}

let ordemAtual = {};
function ordenar(campo, tipo) {
    const direcao = ordemAtual[campo] === 'asc' ? 'desc' : 'asc';
    ordemAtual = { [campo]: direcao };
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('active-sort');
        th.querySelector('.sort-icon').innerText = '⇅';
    });
    const evt = window.event;
    if (evt && evt.currentTarget) {
        evt.currentTarget.classList.add('active-sort');
        evt.currentTarget.querySelector('.sort-icon').innerText = direcao === 'asc' ? '⬆' : '⬇';
    }
    const tasks = getTasksFromTable();
    tasks.sort((a, b) => {
        const valA = a[campo] || '', valB = b[campo] || '';
        if (tipo === 'numero') return direcao === 'asc' ? valA - valB : valB - valA;
        if (tipo === 'data') return direcao === 'asc' ? new Date(valA) - new Date(valB) : new Date(valB) - new Date(valA);
        return direcao === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });
    renderTable(tasks);
    detectarMudanca(false);
}
