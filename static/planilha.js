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
    rebuildHierarchyUI();
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
    rebuildHierarchyUI();
    verificarConflitosDeFerias();
}

function updateUndoButton() {
    undoButton.classList.toggle('hidden', undoStack.length <= 1);
}

function detectarMudanca(forceRecalculate = false) {
    // Validar datas de fim >= inicio
    const datasValidas = validarTodasDatas();

    if (!datasValidas) {
        setStatus('Datas inválidas!', 'text-red-600');
        // Bloqueia o salvamento automático se houver datas inválidas
        if (saveTimeout) clearTimeout(saveTimeout);
        if (recalculateTimeout) clearTimeout(recalculateTimeout);
        return;
    }

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

// --- HIERARQUIA PAI-FILHO ---

/**
 * Rebuilds the visual hierarchy UI after table changes.
 * Adds proper CSS classes, expand/collapse buttons, and indentations.
 */
function rebuildHierarchyUI() {
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // First pass: identify parent-child relationships
    const childIds = new Set();
    rows.forEach(tr => {
        const parentId = tr.dataset.parentId;
        if (parentId && parentId.trim()) {
            childIds.add(tr.dataset.id);
        }
    });

    // Second pass: apply classes and buttons
    rows.forEach(tr => {
        const rowId = tr.dataset.id;
        const parentId = tr.dataset.parentId;

        // Remove previous hierarchy classes
        tr.classList.remove('task-child', 'has-children', 'children-hidden');

        // Check if this row has children
        const hasChildren = rows.some(r => r.dataset.parentId === rowId);
        if (hasChildren) {
            tr.classList.add('has-children');
        }

        // Check if this row is a child
        if (parentId && parentId.trim()) {
            tr.classList.add('task-child');
        }

        // Add expand/collapse button to parents
        const nameCell = tr.querySelector('.task-name-cell');
        if (nameCell) {
            const existingBtn = nameCell.querySelector('.btn-expand');
            if (existingBtn) existingBtn.remove();

            if (hasChildren) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn-expand expanded';
                btn.innerHTML = '▶';
                btn.title = 'Recolher tarefas filhas';
                btn.onclick = function(e) {
                    e.stopPropagation();
                    toggleChildrenVisibility(tr);
                };
                nameCell.insertBefore(btn, nameCell.firstChild);
            }
        }

        // Update child toggle button appearance
        const childBtn = tr.querySelector('.btn-child-toggle');
        if (childBtn) {
            if (parentId && parentId.trim()) {
                childBtn.classList.add('is-child');
                childBtn.title = 'Remover vínculo com tarefa pai';
            } else {
                childBtn.classList.remove('is-child');
                childBtn.title = 'Tornar filha da linha acima';
            }
        }
    });
}

/**
 * Toggle children visibility for a parent row.
 */
function toggleChildrenVisibility(parentTr) {
    const parentId = parentTr.dataset.id;
    const btn = parentTr.querySelector('.btn-expand');
    const isHidden = parentTr.classList.toggle('children-hidden');

    if (btn) {
        btn.classList.toggle('expanded', !isHidden);
        btn.title = isHidden ? 'Expandir tarefas filhas' : 'Recolher tarefas filhas';
    }

    // Hide/show direct children only (one level)
    let next = parentTr.nextElementSibling;
    while (next) {
        const nextParentId = next.dataset.parentId;
        if (nextParentId === parentId) {
            next.style.display = isHidden ? 'none' : '';
            next = next.nextElementSibling;
        } else {
            break;
        }
    }
}

/**
 * Set the current row as child of the row above it.
 * If already a child, remove the parent-child relationship.
 */
function setAsChildOfAbove(tr) {
    const prevTr = tr.previousElementSibling;
    const currentParentId = tr.dataset.parentId;

    // If already has a parent, remove the link (unlink)
    if (currentParentId && currentParentId.trim()) {
        tr.dataset.parentId = '';
        const hiddenInput = tr.querySelector('[name="parent_id"]');
        if (hiddenInput) hiddenInput.value = '';
        rebuildHierarchyUI();
        detectarMudanca(true);
        return;
    }

    // Need a previous row to be the parent
    if (!prevTr) {
        alert('Não há linha acima para ser a tarefa pai.');
        return;
    }

    const prevId = prevTr.dataset.id;
    if (!prevId) return;

    // Prevent circular reference: check if prev row is already a descendant of this row
    if (wouldCreateCycle(tr.dataset.id, prevId)) {
        alert('Não é possível criar esta relação pois geraria uma referência circular.');
        return;
    }

    // Set parent_id
    tr.dataset.parentId = prevId;
    const hiddenInput = tr.querySelector('[name="parent_id"]');
    if (hiddenInput) hiddenInput.value = prevId;

    rebuildHierarchyUI();
    detectarMudanca(true);
}

/**
 * Check if setting `parentId` as parent of `childId` would create a cycle.
 */
function wouldCreateCycle(childId, parentId) {
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const adj = {};
    rows.forEach(tr => {
        const id = tr.dataset.id;
        const pid = tr.dataset.parentId;
        if (pid && pid.trim() && id !== childId) {
            if (!adj[id]) adj[id] = [];
            adj[id].push(pid);
        }
    });

    // Also add the proposed relationship
    if (!adj[childId]) adj[childId] = [];
    adj[childId].push(parentId);

    // DFS to detect cycle starting from parentId
    const visited = new Set();
    const stack = [parentId];
    while (stack.length > 0) {
        const current = stack.pop();
        if (current === childId) return true; // Cycle detected
        if (visited.has(current)) continue;
        visited.add(current);
        for (const neighbor of (adj[current] || [])) {
            stack.push(neighbor);
        }
    }
    return false;
}

/**
 * Confirm before deleting a row that has children.
 */
function confirmDeleteRow(tr) {
    const parentId = tr.dataset.id;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const children = rows.filter(r => r.dataset.parentId === parentId);

    if (children.length > 0) {
        const taskName = tr.querySelector('[name="tarefa"]').value || `ID ${parentId}`;
        const msg = `A tarefa "${taskName}" possui ${children.length} tarefa(s) filha(s).\n\n` +
                    `[OK] - Manter as tarefas filhas (revinculadas ao pai da atual)\n` +
                    `[Cancelar] - Cancelar a exclusão`;

        if (!confirm(msg)) return;

        // Reassign children to the parent of the deleted row (grandparent)
        const grandparentId = tr.dataset.parentId || '';
        children.forEach(childTr => {
            childTr.dataset.parentId = grandparentId;
            const childInput = childTr.querySelector('[name="parent_id"]');
            if (childInput) childInput.value = grandparentId;
        });
    }

    tr.remove();
    rebuildHierarchyUI();
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


// --- VALIDAÇÃO: DATA FIM NÃO PODE SER MENOR QUE DATA INÍCIO ---

function validarDatasTarefa(tr) {
    // Validar Real Início / Real Fim
    const inicioInput = tr.querySelector('[name="inicio"]');
    const fimInput = tr.querySelector('[name="fim"]');
    const inicio = inicioInput?.value;
    const fim = fimInput?.value;

    [inicioInput, fimInput].forEach(input => {
        if (!input) return;
        if (inicio && fim && fim < inicio) {
            input.classList.add('date-invalid');
            input.title = 'Data final é anterior à data inicial!';
        } else {
            input.classList.remove('date-invalid');
            input.title = '';
        }
    });

    // Validar Planejado Início / Planejado Fim (baseline)
    const blInicioInput = tr.querySelector('[name="baseline_inicio"]');
    const blFimInput = tr.querySelector('[name="baseline_fim"]');
    const blInicio = blInicioInput?.value;
    const blFim = blFimInput?.value;

    [blInicioInput, blFimInput].forEach(input => {
        if (!input) return;
        if (blInicio && blFim && blFim < blInicio) {
            input.classList.add('date-invalid');
            input.title = 'Data final planejada é anterior à data inicial planejada!';
        } else {
            input.classList.remove('date-invalid');
            input.title = '';
        }
    });

    // Retorna true se ambos forem válidos
    const realValido = !(inicio && fim && fim < inicio);
    const planValido = !(blInicio && blFim && blFim < blInicio);
    return realValido && planValido;
}

function validarTodasDatas() {
    let todasValidas = true;
    tbody.querySelectorAll('tr').forEach(tr => {
        if (!validarDatasTarefa(tr)) {
            todasValidas = false;
        }
    });
    return todasValidas;
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

// --- MOVER PARA "EM ANDAMENTO" QUANDO DATA DE INÍCIO É PREENCHIDA ---

function handleInicioChange(input) {
    const tr = input.closest('tr');
    const kanbanColunaInput = tr.querySelector('[name="kanban_coluna_id"]');
    const novoValor = input.value;

    // Se preencheu uma data de início e existe o hidden field, move para andamento
    if (kanbanColunaInput && novoValor && colunaAndamentoId && (kanbanColunaInput.value === 'backlog' || kanbanColunaInput.value === 'iniciar')) {
        kanbanColunaInput.value = colunaAndamentoId;
    }

    // Sempre salva e recalcula quando a data de início mudar
    detectarMudanca(true);
}

// --- RN015: RESTRIÇÕES E CONFLITOS ---

function definirRestricaoManual(inputInicio) {
    const tr = inputInicio.closest('tr');
    const dataManual = inputInicio.value;
    tr.dataset.restricaoTipo = 'inicio_nao_antes_de';
    tr.dataset.restricaoData = dataManual;

    // Verificar conflito com predecessora
    const predecessoraId = tr.querySelector('[name="predecessora"]').value;
    if (!predecessoraId) return;

    const predTr = tbody.querySelector(`tr[data-id="${predecessoraId}"]`);
    if (!predTr) return;

    const fimPredecessora = predTr.querySelector('[name="fim"]').value;

    if (dataManual && fimPredecessora && dataManual < fimPredecessora) {
        const nomeTarefa = tr.querySelector('[name="tarefa"]').value || `ID ${tr.dataset.id}`;
        const nomePred = predTr.querySelector('[name="tarefa"]').value || `ID ${predecessoraId}`;
        
        const querManter = confirm(
            `ALERTA DE CONFLITO (RN015)\n\n` +
            `Você está tentando iniciar a tarefa "${nomeTarefa}" em ${dataManual}, antes da conclusão de sua predecessora "${nomePred}" (prevista para ${fimPredecessora}).\n\n` +
            `[OK] para MANTER sua data e quebrar o link com a predecessora.\n` +
            `[Cancelar] para REMOVER sua data manual e deixar o sistema agendar.`
        );

        if (querManter) {
            tr.querySelector('[name="predecessora"]').value = ''; // Quebra o link
        } else {
            tr.dataset.restricaoTipo = ''; // Remove a restrição
            tr.dataset.restricaoData = '';
        }
    }
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
            id: tr.dataset.id,
            tipo: get('tipo'),
            fase: get('fase'),
            modulo: get('modulo'),
            tarefa: get('tarefa'),
            subtarefa: get('subtarefa'),
            inicio: get('inicio'),
            dias: get('dias'),
            fim: get('fim'),
            predecessora: get('predecessora'),
            baseline_inicio: get('baseline_inicio'),
            baseline_fim: get('baseline_fim'),
            responsavel_id: get('responsavel'),
            conclusao: get('conclusao'),
            restricao_tipo: tr.dataset.restricaoTipo || null,
            restricao_data: tr.dataset.restricaoData || null,
            kanban_coluna_id: get('kanban_coluna_id'),
            parent_id: tr.dataset.parentId || null
        };
    });
}

function renderTable(tasks) {
    tbody.innerHTML = '';
    tasks.forEach(task => {
        const row = document.createElement('tr');
        row.className = 'group transition-colors';
        row.dataset.id = task.id;
        row.dataset.parentId = task.parent_id || '';
        row.dataset.tipo = task.tipo || 'task';
        row.dataset.restricaoTipo = task.restricao_tipo || '';
        row.dataset.restricaoData = task.restricao_data || '';
        row.innerHTML = createTaskRowHtml(task);
        tbody.appendChild(row);
    });
    rebuildHierarchyUI();
    verificarConflitosDeFerias();
}

function adicionarLinhaVazia() {
    const ids = Array.from(tbody.querySelectorAll('tr')).map(tr => parseInt(tr.dataset.id));
    const novoId = (ids.length > 0 ? Math.max(...ids) : 0) + 1;
    const novaTarefa = { id: novoId, dias: 1, conclusao: 0, kanban_coluna_id: 'backlog', parent_id: null };
    const row = document.createElement('tr');
    row.className = 'group transition-colors';
    row.dataset.id = novoId;
    row.dataset.parentId = '';
    row.dataset.restricaoTipo = '';
    row.dataset.restricaoData = '';
    row.innerHTML = createTaskRowHtml(novaTarefa);
    tbody.appendChild(row);
    rebuildHierarchyUI();
    detectarMudanca(true);
    row.querySelector('[name="tarefa"]').focus();
    row.scrollIntoView({ behavior: 'smooth' });
}

function createTaskRowHtml(t) {
    const responsaveisOptions = responsaveis.map(r =>
        `<option value="${r.id}" ${r.id === t.responsavel_id ? 'selected' : ''}>${r.nome}</option>`
    ).join('');
    const isChild = t.parent_id ? true : false;
    const tipoAtual = t.tipo || 'task';

    // Nomes dos tipos em português
    const tipoLabels = {
        epic: 'Épico',
        feature: 'Feature',
        story: 'História',
        task: 'Tarefa',
        subtask: 'Subtarefa'
    };

    // Define as opções do dropdown de tipo baseado na hierarquia correta
    const tipoOptions = `
        <option value="epic" ${tipoAtual === 'epic' ? 'selected' : ''}>Épico</option>
        <option value="feature" ${tipoAtual === 'feature' ? 'selected' : ''}>Feature</option>
        <option value="story" ${tipoAtual === 'story' ? 'selected' : ''}>História</option>
        <option value="task" ${tipoAtual === 'task' ? 'selected' : ''}>Tarefa</option>
        <option value="subtask" ${tipoAtual === 'subtask' ? 'selected' : ''}>Subtarefa</option>
    `;

    return `
        <td class="p-0 align-middle text-center handle border-r no-print"><div class="h-full flex items-center justify-center cursor-grab">⋮⋮</div></td>
        <td class="p-0 text-center text-xs font-mono border-r">${t.id}</td>
        <td class="p-0 text-center border-r no-print">
            <button type="button" class="btn-child-toggle ${isChild ? 'is-child' : ''}"
                    onclick="setAsChildOfAbove(this.closest('tr'))"
                    title="${isChild ? 'Remover vínculo com tarefa pai' : 'Tornar filha da linha acima'}">
                ↳
            </button>
        </td>
        <td class="p-0 border-r"><input name="fase" value="${t.fase || ''}" class="sheet-input" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r task-name-cell">
            <span class="tipo-badge-planilha tipo-${tipoAtual}">${tipoLabels[tipoAtual] || 'Tarefa'}</span>
            <input name="tarefa" value="${t.tarefa || 'Nova Tarefa'}" class="sheet-input" oninput="detectarMudanca()" style="display:inline;width:calc(100% - 70px);">
        </td>
        <td class="p-0 border-r"><input name="subtarefa" value="${t.subtarefa || ''}" class="sheet-input" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r bg-blue-50/30"><input type="date" name="baseline_inicio" value="${t.baseline_inicio || ''}" class="sheet-input text-center" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input type="number" name="dias" value="${t.dias || 1}" class="sheet-input text-center" oninput="detectarMudanca(true)"></td>
        <td class="p-0 border-r bg-blue-50/30"><input type="date" name="baseline_fim" value="${t.baseline_fim || ''}" class="sheet-input text-center" oninput="detectarMudanca()"></td>
        <td class="p-0 border-r"><input name="predecessora" value="${t.predecessora_id || t.predecessora || ''}" class="sheet-input text-center" oninput="detectarMudanca(true)"></td>
        <td class="p-0 border-r bg-amber-50/30 relative"><input type="date" name="inicio" value="${t.inicio || ''}" class="sheet-input text-center" oninput="handleInicioChange(this)"><span class="date-alert-icon hidden" title="Conflito com férias!">⚠️</span></td>
        <td class="p-0 border-r bg-amber-50/30 relative"><input type="date" name="fim" value="${t.fim || ''}" class="sheet-input text-center" oninput="detectarMudanca(true)"><span class="date-alert-icon hidden" title="Conflito com férias!">⚠️</span></td>
        <td class="p-0 border-r"><select name="responsavel" class="sheet-input" oninput="detectarMudanca(true)"><option value="">Nenhum</option>${responsaveisOptions}</select></td>
        <td class="p-0 border-r relative"><div class="progress-bar" style="width: ${t.conclusao || 0}%;"></div><input type="number" name="conclusao" value="${t.conclusao || 0}" class="sheet-input text-center" oninput="handleConclusionChange(this)"></td>
        <td class="p-0 text-center no-print">
            <div class="flex items-center gap-1 px-1">
                <select name="tipo" class="tipo-select" onchange="onTipoChange(this)" title="Alterar tipo do item">
                    ${tipoOptions}
                </select>
                <button onclick="confirmDeleteRow(this.closest('tr'))" class="w-6 h-6 flex items-center justify-center text-gray-300 hover:text-red-500 text-xs">✕</button>
            </div>
            <input type="hidden" name="modulo" value="${t.modulo || ''}">
            <input type="hidden" name="kanban_coluna_id" value="${t.kanban_coluna_id || 'backlog'}">
            <input type="hidden" name="parent_id" value="${t.parent_id || ''}">
        </td>
    `;
}

// Função chamada quando o tipo é alterado - atualiza o dataset e badge
function onTipoChange(select) {
    const tr = select.closest('tr');
    const novoValor = select.value;
    tr.dataset.tipo = novoValor;
    
    // Atualiza o badge visual
    const badge = tr.querySelector('.tipo-badge-planilha');
    if (badge) {
        const tipoLabels = {
            epic: 'Épico',
            feature: 'Feature',
            story: 'História',
            task: 'Tarefa',
            subtask: 'Subtarefa'
        };
        // Remove all tipo classes
        badge.className = badge.className.replace(/tipo-\w+/g, '');
        badge.classList.add('tipo-badge-planilha', `tipo-${novoValor}`);
        badge.textContent = tipoLabels[novoValor] || 'Tarefa';
    }
    
    detectarMudanca(true);
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
                        tr.querySelector('[name="baseline_inicio"]').value = item.baseline_inicio;
                        tr.querySelector('[name="baseline_fim"]').value = item.baseline_fim;
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

