// === KANBAN ===
const projectId = document.getElementById('kanban-config')?.textContent?.match(/projectId\s*=\s*"([^"]+)"/)?.[1];
let kanbanColumns = JSON.parse(document.getElementById('kanban-config')?.textContent?.match(/kanbanColumns\s*=\s*(\[.*\])/)?.[1] || '[]');
let allTasks = JSON.parse(document.getElementById('kanban-config')?.textContent?.match(/allTasks\s*=\s*(\[.*\])/)?.[1] || '[]');
const tasksMap = new Map(allTasks.map(task => [String(task.id), task]));

function getInitials(name) {
    if (!name) return '';
    const parts = name.trim().split(' ').filter(Boolean);
    if (parts.length === 0) return '';
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getColorForName(name) {
    if (!name) return '#cccccc'; // Cor padrão
    const colors = [
        '#f87171', '#fb923c', '#fbbf24', '#a3e635', '#4ade80', 
        '#34d399', '#2dd4bf', '#22d3ee', '#38bdf8', '#60a5fa', 
        '#818cf8', '#a78bfa', '#c084fc', '#e879f9', '#f472b6'
    ];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
        hash |= 0; // Converte para 32bit integer
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
}

function criarCardHtml(t) {
    const isBlocked = t.bloqueada_por;
    const isOverdue = t.em_atraso;

    const cardClasses = [
        isBlocked ? 'kanban-card-bloqueado' : 'cursor-pointer',
        isOverdue ? 'kanban-card-atrasado' : ''
    ].filter(Boolean).join(' ');

    const blockedTooltip = isBlocked ? `title="Aguardando conclusão de: #${t.bloqueada_por.id} - ${t.bloqueada_por.nome}"` : '';

    return `
        <div class="kanban-card ${cardClasses}" data-id="${t.id}" draggable="true" onclick="abrirModalEditarTarefa(event, '${t.id}')">
            ${isBlocked ? `<div class="card-lock-icon" ${blockedTooltip}>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" /></svg>
            </div>` : ''}
            ${isOverdue ? `<div class="card-overdue-badge" title="Tarefa em atraso por ${t.dias_atraso} dia(s)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 mr-1"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clip-rule="evenodd" /></svg>+${t.dias_atraso}d</div>` : ''}
            <span class="card-id">#${t.id}</span>
            <div class="card-title">${t.tarefa || t.subtarefa || 'Sem nome'}</div>
            ${(t.fase || t.modulo) ? `<div class="card-sub">${t.fase || ''}${t.fase && t.modulo ? ' / ' : ''}${t.modulo || ''}</div>` : ''}
            <div class="card-meta">
                ${t.responsavel_nome ? `<span class="resp">
                    <div class="avatar-initials" style="background-color: ${getColorForName(t.responsavel_nome)};">${getInitials(t.responsavel_nome)}</div>
                    ${t.responsavel_nome}
                </span>` : ''}
                <span class="fase-tag">${t.conclusao || 0}%</span>
            </div>
            ${(t.inicio || t.fim) ? `<div class="card-dates">
                ${t.inicio ? `<span>📅 ${t.inicio}</span>` : ''}
                ${t.fim ? `<span>🏁 ${t.fim}</span>` : ''}
            </div>` : ''}
            <div class="card-progress">
                <div class="card-progress-bar" style="width: ${t.conclusao || 0}%"></div>
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
    document.getElementById('form-editar-tarefa')?.addEventListener('submit', salvarEdicaoTarefa);
    document.getElementById('form-adicionar-comentario')?.addEventListener('submit', adicionarComentario);
    if (!board) return;

    const colunas = board.querySelectorAll('.kanban-column-body');
    if (colunas.length === 0) return;

    colunas.forEach(coluna => {
        new Sortable(coluna, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: async function(evt) {
                const cardEl = evt.item;
                const taskId = cardEl.dataset.id;
                const colunaDestino = evt.to.dataset.colId;
                const colunaOrigem = evt.from.dataset.colId;

                // RN023 - Bloqueio de dependência
                if (cardEl.classList.contains('kanban-card-bloqueado')) {
                    alert('Ação bloqueada (RN023): Esta tarefa depende da conclusão de uma tarefa anterior.');
                    // Reverte o movimento visualmente
                    evt.from.appendChild(cardEl);
                    return;
                }

                if (!taskId || !colunaDestino) return;

                // RN018 - Validação de entrada na coluna de Início
                const colunaDestinoInfo = kanbanColumns.find(c => c.coluna_id === colunaDestino);
                if (colunaDestinoInfo && colunaDestinoInfo.tipo === 'inicio') {
                    // Precisamos dos dados da tarefa para validar.
                    // Esta é uma simplificação. O ideal seria ter os dados da tarefa em um objeto JS.
                    // Por agora, vamos buscar o card no DOM e extrair o que pudermos.
                    const responsavelSpan = cardEl.querySelector('.resp');
                    const hasResponsavel = responsavelSpan && responsavelSpan.textContent.trim() !== '';

                    if (!hasResponsavel) {
                        alert('Para mover para "Iniciar", a tarefa precisa ter um Responsável atribuído.');
                        // Reverte o movimento visualmente
                        evt.from.appendChild(cardEl);
                        return; // Para a execução
                    }
                    // Outras validações (datas, etc.) podem ser adicionadas aqui.
                }

                // Se a coluna não mudou, não faz nada
                if (colunaDestino === colunaOrigem) return;

                // Envia a alteração para o backend
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

// --- MODAL DE EDIÇÃO DE TAREFA ---

function abrirModalEditarTarefa(event, taskId) {
    const card = event.currentTarget;
    // Não abre o modal se a tarefa estiver bloqueada
    if (card.classList.contains('kanban-card-bloqueado')) {
        return;
    }

    const task = tasksMap.get(String(taskId));
    if (!task) return;

    const modal = document.getElementById('modal-editar-tarefa');
    const form = document.getElementById('form-editar-tarefa');

    form.querySelector('#id-tarefa-edicao').value = task.id;
    form.querySelector('#nome-tarefa-edicao').value = task.tarefa || task.subtarefa || '';
    form.querySelector('#responsavel-tarefa-edicao').value = task.responsavel_id || '';
    form.querySelector('#inicio-tarefa-edicao').value = task.inicio || '';
    form.querySelector('#fim-tarefa-edicao').value = task.fim || '';
    form.querySelector('#dias-tarefa-edicao').value = task.dias || '';
    form.querySelector('#descricao-tarefa-edicao').value = task.descricao || '';
    form.querySelector('#conclusao-tarefa-edicao').value = task.conclusao || 0;
    form.dataset.pkId = task.pk_id; // Armazena o PK_ID para o form de comentário

    // Popula a lista de atividades/comentários
    const listaAtividades = document.getElementById('lista-atividades');
    listaAtividades.innerHTML = '';
    if (task.atividades && task.atividades.length > 0) {
        task.atividades.forEach(atividade => {
            listaAtividades.innerHTML += criarHtmlAtividade(atividade);
        });
    } else {
        listaAtividades.innerHTML = '<p class="text-xs text-gray-500 text-center p-4">Nenhuma atividade registrada.</p>';
    }

    modal.showModal();
}

function criarHtmlAtividade(atividade) {
    const nome = atividade.responsavel_nome || 'Sistema';
    const iniciais = getInitials(nome);
    const cor = getColorForName(nome);
    const dataFormatada = new Date(atividade.criado_em).toLocaleString('pt-BR');

    const conteudo = atividade.tipo === 'comentario'
        ? `<div class="text-sm text-gray-800">${atividade.detalhe.replace(/\n/g, '<br>')}</div>`
        : `<div class="text-xs text-gray-600 italic">${atividade.detalhe}</div>`;

    return `
        <div class="flex gap-3 py-3">
            <div class="avatar-initials flex-shrink-0" style="background-color: ${cor}; width: 32px; height: 32px; font-size: 12px;">${iniciais}</div>
            <div class="flex-1">
                <div class="flex justify-between items-baseline">
                    <span class="font-semibold text-sm">${nome}</span>
                    <span class="text-xs text-gray-400">${dataFormatada}</span>
                </div>
                ${conteudo}
            </div>
        </div>
    `;
}

async function salvarEdicaoTarefa(event) {
    event.preventDefault();
    const form = event.target;
    const taskId = form.querySelector('#id-tarefa-edicao').value;
    const modal = document.getElementById('modal-editar-tarefa');

    const dados = {
        tarefa: form.querySelector('#nome-tarefa-edicao').value,
        descricao: form.querySelector('#descricao-tarefa-edicao').value || null,
        responsavel_id: form.querySelector('#responsavel-tarefa-edicao').value || null,
        inicio: form.querySelector('#inicio-tarefa-edicao').value || null,
        fim: form.querySelector('#fim-tarefa-edicao').value || null,
        dias: form.querySelector('#dias-tarefa-edicao').value || null,
        conclusao: form.querySelector('#conclusao-tarefa-edicao').value || 0,
    };

    try {
        const response = await fetch(`/projeto/${projectId}/editar_tarefa/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });

        if (response.ok) {
            modal.close();
            location.reload(); // Recarrega para ver as mudanças
        } else {
            const error = await response.json();
            alert(`Erro ao salvar a tarefa: ${error.mensagem || 'Erro desconhecido'}`);
        }
    } catch (e) {
        console.error('Erro de conexão:', e);
        alert('Erro de conexão ao salvar a tarefa.');
    }
}

async function adicionarComentario(event) {
    event.preventDefault();
    const form = event.target;
    const textarea = form.querySelector('#texto-comentario');
    const comentario = textarea.value.trim();
    const formEdicao = document.getElementById('form-editar-tarefa');
    const taskPkId = formEdicao.dataset.pkId;

    if (!comentario || !taskPkId) return;

    // Em um sistema real, o ID do responsável viria da sessão.
    // Por agora, vamos pegar do seletor de responsável da tarefa.
    const responsavelId = formEdicao.querySelector('#responsavel-tarefa-edicao').value || null;

    try {
        const response = await fetch(`/projeto/${projectId}/tarefa/${taskPkId}/adicionar_comentario`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comentario, responsavel_id: responsavelId })
        });

        if (response.ok) {
            textarea.value = ''; // Limpa o campo
            // Atualiza a lista de atividades dinamicamente
            const novaAtividade = { responsavel_nome: 'Você', criado_em: new Date(), tipo: 'comentario', detalhe: comentario };
            const listaAtividades = document.getElementById('lista-atividades');
            listaAtividades.insertAdjacentHTML('afterbegin', criarHtmlAtividade(novaAtividade));
        } else {
            alert('Erro ao adicionar comentário.');
        }
    } catch (e) {
        console.error('Erro de conexão:', e);
        alert('Erro de conexão ao adicionar comentário.');
    }
}



// --- RN020: CONFIGURAÇÃO DE COLUNAS ---

function abrirModalConfigColunas() {
    const modal = document.getElementById('modal-config-colunas');
    const lista = document.getElementById('lista-colunas-config');
    lista.innerHTML = ''; // Limpa a lista

    // Popula a lista com as colunas atuais
    kanbanColumns.forEach(col => {
        lista.appendChild(criarItemColunaConfig(col));
    });

    // Inicializa o Sortable para reordenar
    new Sortable(lista, {
        handle: '.handle-col',
        animation: 150,
    });

    modal.showModal();
}

function criarItemColunaConfig(col) {
    const li = document.createElement('li');
    li.className = 'flex items-center gap-2 p-2 bg-gray-100 rounded-md';
    li.dataset.colId = col.coluna_id;
    li.dataset.colTipo = col.tipo;

    const isSystemColumn = ['backlog', 'inicio', 'fim'].includes(col.tipo);

    li.innerHTML = `
        <span class="handle-col cursor-grab text-gray-400">⋮⋮</span>
        <input type="text" value="${col.nome}" class="flex-1 p-1 border rounded" ${isSystemColumn ? 'disabled' : ''}>
        <input type="number" value="${col.progresso_padrao || 0}" class="w-20 p-1 border rounded" placeholder="% Progresso" ${isSystemColumn ? 'disabled' : ''}>
        <button onclick="${isSystemColumn ? '' : 'this.parentElement.remove()'}" class="text-gray-400 hover:text-red-500 ${isSystemColumn ? 'opacity-50 cursor-not-allowed' : ''}" ${isSystemColumn ? 'disabled' : ''}>✕</button>
    `;
    return li;
}

function adicionarColunaConfig() {
    const lista = document.getElementById('lista-colunas-config');
    const novaColuna = {
        coluna_id: 'col_' + new Date().getTime(), // ID único temporário
        nome: 'Nova Coluna',
        tipo: 'meio', // Todas as colunas novas são do tipo 'meio'
        progresso_padrao: 25
    };
    const novoItem = criarItemColunaConfig(novaColuna);
    // Insere antes do último item (Conclusão)
    lista.insertBefore(novoItem, lista.lastElementChild);
}

async function salvarConfiguracaoColunas() {
    const lista = document.getElementById('lista-colunas-config');
    const novaConfig = { colunas: [] };

    lista.querySelectorAll('li').forEach(li => {
        novaConfig.colunas.push({
            coluna_id: li.dataset.colId,
            nome: li.querySelector('input[type="text"]').value,
            tipo: li.dataset.colTipo,
            progresso_padrao: li.querySelector('input[type="number"]').value
        });
    });

    try {
        const response = await fetch(`/projeto/${projectId}/kanban/salvar_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(novaConfig)
        });
        if (response.ok) {
            location.reload(); // Recarrega a página para ver as mudanças
        } else {
            alert('Erro ao salvar a configuração das colunas.');
        }
    } catch (e) {
        alert('Erro de conexão ao salvar a configuração.');
    }
}
