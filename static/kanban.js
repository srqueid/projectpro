// === CONFIGURA SORTABLE EM CADA COLUNA ===
function initSortable() {
    document.querySelectorAll('.kanban-column-body').forEach(el => {
        if (el.sortableInstance) return;
        el.sortableInstance = new Sortable(el, {
            group: {
                name: 'kanban-cards',
                pull: true,
                put: true
            },
            animation: 200,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: function(evt) {
                const card = evt.item;
                const colDestinoId = evt.to.dataset.colId;
                const colOrigemId = evt.from.dataset.colId;

                if (colDestinoId && colOrigemId && colDestinoId !== colOrigemId) {
                    moverCard(card.dataset.id, colOrigemId, colDestinoId);
                }
                atualizarContadores();
            }
        });
    });
}

// === MOVER CARD (API) ===
async function moverCard(cardId, colOrigem, colDestino) {
    try {
        const response = await fetch(`/projeto/${projectId}/kanban_mover_card`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: parseInt(cardId),
                coluna_origem: colOrigem,
                coluna_destino: colDestino
            })
        });
        const result = await response.json();
        if (result.status === 'sucesso' && result.alterado) {
            // Recarrega a página para refletir as baselines atualizadas
            setTimeout(() => location.reload(), 300);
        }
    } catch (e) {
        console.error('Erro ao mover card:', e);
        alert('Erro ao mover card. Tente novamente.');
    }
}

// === ATUALIZAR CONTADORES ===
function atualizarContadores() {
    document.querySelectorAll('.kanban-column').forEach(col => {
        const cards = col.querySelectorAll('.kanban-card');
        const countEl = col.querySelector('.count');
        if (countEl) countEl.textContent = cards.length;
    });
}

// ============================================================
// MODAL CONFIGURAÇÃO DE COLUNAS
// ============================================================

let configSortable = null;
const colunasBloqueadas = ['backlog', 'inicio', 'fim'];

function abrirModalConfig() {
    const modal = document.getElementById('modal-config-colunas');
    const container = document.getElementById('lista-colunas-config');
    container.innerHTML = ''; // Limpa a lista

    // Popula a lista com as colunas atuais
    colunasData.forEach((col) => {
        container.appendChild(criarItemColunaConfig(col));
    });

    // Inicializa o Sortable.js na lista de configuração
    if (configSortable) {
        configSortable.destroy();
    }
    configSortable = new Sortable(container, {
        animation: 150,
        handle: '.drag-handle', // Define o elemento que pode ser usado para arrastar
        ghostClass: 'sortable-ghost-config',
        filter: '.bloqueado', // Impede que itens com a classe 'bloqueado' sejam arrastados
        onMove: function (evt) {
            // Impede que um item seja movido para a posição de um item bloqueado
            return !evt.related.classList.contains('bloqueado');
        }
    });

    modal.showModal();
}

function criarItemColunaConfig(col) {
    const isBlocked = colunasBloqueadas.includes(col.tipo);

    const tipos = [
        { value: 'backlog', label: '📋 Backlog' },
        { value: 'inicio', label: '🚀 Início' },
        { value: 'meio', label: '⚙️ Meio' },
        { value: 'fim', label: '✅ Fim' }
    ];
    const tipoOptions = tipos.map(t =>
        `<option value="${t.value}" ${col && t.value === col.tipo ? 'selected' : ''}>${t.label}</option>`
    ).join('');

    const div = document.createElement('div');
    div.className = `coluna-config-item ${isBlocked ? 'bloqueado' : ''}`;

    div.innerHTML = `
        <span class="drag-handle" ${isBlocked ? 'style="visibility: hidden;"' : 'title="Arraste para reordenar"'}>⠿</span>
        <input type="text" value="${col ? col.nome : 'Nova Coluna'}" data-field="nome" class="col-nome-input" placeholder="Nome da coluna" ${isBlocked ? 'disabled' : ''}>
        <select data-field="tipo" class="col-tipo-select" ${isBlocked ? 'disabled' : ''}>${tipoOptions}</select>
        <button class="btn-remove-col" onclick="removerColunaConfig(this)" title="Remover coluna" ${isBlocked ? 'style="display: none;"' : ''}>✕</button>
    `;
    return div;
}

function adicionarColunaConfig() {
    const container = document.getElementById('lista-colunas-config');
    // Adiciona uma nova coluna com valores padrão
    const novaColuna = { nome: 'Nova Coluna', tipo: 'meio' };
    container.appendChild(criarItemColunaConfig(novaColuna));
}

function removerColunaConfig(btn) {
    btn.closest('.coluna-config-item').remove();
}

async function salvarConfigColunas() {
    const items = document.querySelectorAll('#lista-colunas-config .coluna-config-item');
    const novasColunas = [];
    const tiposCount = { backlog: 0, inicio: 0, fim: 0 };

    items.forEach(item => {
        const nomeInput = item.querySelector('[data-field="nome"]');
        const tipoSelect = item.querySelector('[data-field="tipo"]');

        const nome = nomeInput.value.trim();
        const tipo = tipoSelect.value;

        if (!nome) return; // Ignora colunas sem nome

        if (tiposCount[tipo] !== undefined) {
            tiposCount[tipo]++;
        }

        novasColunas.push({
            id: nome.toLowerCase().replace(/[^a-z0-9_]/g, '').replace(/\s+/g, '_'),
            nome: nome,
            tipo: tipo
        });
    });

    // Validação dos tipos de coluna
    if (tiposCount.backlog !== 1) {
        alert('Deve haver exatamente 1 coluna do tipo "📋 Backlog".');
        return;
    }
    if (tiposCount.inicio !== 1) {
        alert('Deve haver exatamente 1 coluna do tipo "🚀 Início".');
        return;
    }
    if (tiposCount.fim !== 1) {
        alert('Deve haver exatamente 1 coluna do tipo "✅ Fim".');
        return;
    }

    try {
        const response = await fetch(`/projeto/${projectId}/kanban_salvar_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ colunas: novasColunas })
        });
        if (response.ok) {
            document.getElementById('modal-config-colunas').close();
            location.reload();
        } else {
            const error = await response.json();
            alert(`Erro ao salvar: ${error.mensagem || 'Tente novamente.'}`);
        }
    } catch (e) {
        console.error('Erro de conexão:', e);
        alert('Erro de conexão ao salvar a configuração.');
    }
}

// === INICIALIZAÇÃO ===
document.addEventListener('DOMContentLoaded', function() {
    initSortable();
    atualizarContadores();

    // Adiciona feedback visual de 'dragover' para as colunas
    document.querySelectorAll('.kanban-column-body').forEach(el => {
        el.addEventListener('dragover', () => el.closest('.kanban-column').classList.add('drag-over'));
        el.addEventListener('dragleave', () => el.closest('.kanban-column').classList.remove('drag-over'));
        el.addEventListener('drop', () => el.closest('.kanban-column').classList.remove('drag-over'));
    });
});
