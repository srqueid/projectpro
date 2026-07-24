// ... (código existente)

// ============================================================
// MODAL NOVA TAREFA
// ============================================================

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
                nome: nome,
                coluna_id: colunaId
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

// ... (restante do código)
