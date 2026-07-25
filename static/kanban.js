// === KANBAN ===
const projectId = document.getElementById('kanban-config')?.textContent?.match(/projectId\s*=\s*"([^"]+)"/)?.[1];

function criarCardHtml(t) {
    const progressClass = ['bar-0', 'bar-25', 'bar-50', 'bar-75', 'bar-100'][Math.min((t.conclusao || 0) // 25, 4)];
    return `
        <div class="kanban-card" data-id="${t.id}" draggable="true">
            <span class="card-id">#${t.id}</span>
            <div class="card-title">${t.tarefa || t.subtarefa || 'Sem nome'}</div>
            ${(t.fase || t.modulo) ? `<div class="card-sub">${t.fase || ''}${t.fase && t.modulo ? ' / ' : ''}${t.modulo || ''}</div>` : ''}
            <div class="card-meta">
                ${t.responsavel_id ? `<span class="resp">${t.responsavel_id}</span>` : ''}
                <span class="fase-tag">${t.conclusao || 0}%</span>
            </div>
            ${(t.inicio || t.fim) ? `<div class="card-dates">
                ${t.inicio ? `<span>📅 ${t.inicio}</span>` : ''}
                ${t.fim ? `<span>🏁 ${t.fim}</span>` : ''}
            </div>` : ''}
            <div class="card-progress">
                <div class="card-progress-bar ${progressClass}" style="width: ${t.conclusao || 0}%"></div>
            </div>
        </div>
    `;
}

function abrirModalNovaTarefa(colunaId) {
    const modal = document.getElementById('modal-nova-tarefa');
    document.getElementById('coluna-id-nova-tarefa').value = colunaId;
    modal.showModal();
}

document.getElementById('form-nova-tarefa').addEventListener('submit', async function(e) {
    e.preventDefault();
    const nome = document.getElementById('nome-nova-tarefa').value;
    const colunaId = document.getElementById('coluna-id-nova-tarefa').value;

    if (!nome.trim()) {
        alert('O nome da tarefa não pode ser vazio.');
        return;
    }

    try {
        const response = await fetch(`/projeto/${projectId}/adicionar_tarefa`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tarefa: nome,
                kanban_coluna_id: colunaId
            })
        });
        if (response.ok) {
            location.reload();
        } else {
            alert('Erro ao criar a tarefa.');
        }
    } catch (e) {
        console.error('Erro de conexão:', e);
        alert('Erro de conexão ao criar a tarefa.');
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const board = document.getElementById('kanban-board');
    if (!board) return;

    const colunas = board.querySelectorAll('.kanban-column-body');
    colunas.forEach(coluna => {
        new Sortable(coluna, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: async function(evt) {
                const card = evt.item;
                const taskId = card.dataset.id;
                const colunaDestino = evt.to.dataset.colId;

                if (!taskId || !colunaDestino) return;

                try {
                    const response = await fetch(`/projeto/${projectId}/kanban_mover_card`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ card_id: taskId, coluna_destino: colunaDestino })
                    });
                    if (!response.ok) {
                        alert('Erro ao mover tarefa.');
                        location.reload();
                    }
                } catch (e) {
                    console.error('Erro ao mover:', e);
                    alert('Erro de conexão ao mover tarefa.');
                    location.reload();
                }
            }
        });
    });
});
