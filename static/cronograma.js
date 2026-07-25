// === CRONOGRAMA (GANTT) ===
const view_modes = ['Quarter Day', 'Half Day', 'Day', 'Week', 'Month'];
let current_mode_index = 3;
let gantt_chart = null;

function renderGantt(mode, tarefasGantt) {
    const el = document.getElementById('gantt-chart');
    if (!el) {
        console.error('[Gantt] Elemento #gantt-chart não encontrado.');
        return;
    }

    if (tarefasGantt.length === 0) {
        el.innerHTML = '<div class="flex h-full items-center justify-center text-slate-400 py-10">Sem dados para exibir no cronograma.</div>';
        return;
    }

    try {
        el.innerHTML = '';
        gantt_chart = new Gantt("#gantt-chart", tarefasGantt, {
            header_height: 60, column_width: 30, step: 24, view_modes: view_modes, bar_height: 28, bar_corner_radius: 6, arrow_curve: 5, padding: 20, view_mode: mode, date_format: 'YYYY-MM-DD',
            custom_popup_html: function(task) {
                const isBaseline = task.custom_class === 'gantt-bar-baseline';
                const start = new Date(task.start).toLocaleDateString('pt-BR');
                const end = new Date(task.end).toLocaleDateString('pt-BR');
                let tipo = 'Execução Real';
                if (isBaseline) tipo = 'Planejamento';
                else if (task.custom_class === 'gantt-bar-atraso-grave') tipo = 'Execução (Atraso Grave)';
                else if (task.custom_class === 'gantt-bar-atraso-leve') tipo = 'Execução (Atraso Leve)';
                else if (task.custom_class === 'gantt-bar-execucao') tipo = 'Execução (No Prazo)';
                return `<div class="popup-wrapper"><div class="title">${task.name}</div><div class="subtitle"><strong>Tipo:</strong> ${tipo}</div><div class="subtitle"><strong>De:</strong> ${start} <strong>Até:</strong> ${end}</div><div class="subtitle"><strong>Progresso:</strong> ${task.progress}%</div></div>`;
            }
        });
        atualizarBotoes(mode);
    } catch (err) {
        console.error('[Gantt] Falha ao renderizar:', err);
        el.innerHTML = `<div class="flex h-full items-center justify-center text-red-600 py-10">Erro ao carregar o cronograma: ${err.message}</div>`;
    }
}

function mudarZoom(mode) { 
    current_mode_index = view_modes.indexOf(mode); 
    if(gantt_chart) { 
        gantt_chart.change_view_mode(mode); 
        atualizarBotoes(mode); 
    } 
}

function atualizarBotoes(activeMode) { 
    document.querySelectorAll('.zoom-btn').forEach(btn => btn.classList.remove('active')); 
    const btnId = 'btn-' + activeMode.replace(' ', '-'); 
    const btn = document.getElementById(btnId); 
    if(btn) btn.classList.add('active'); 
}

function toggleFullScreen() { 
    const elem = document.getElementById('gantt-mode-container'); 
    if (!document.fullscreenElement) { 
        elem.requestFullscreen().catch(err => { 
            alert(`Erro: ${err.message}`); 
        }); 
    } else { 
        document.exitFullscreen(); 
    } 
}

function imprimirCronograma() {
    const modoAnterior = view_modes[current_mode_index];
    mudarZoom('Month');
    setTimeout(() => { window.print(); }, 500);
    window.onafterprint = function() {
        mudarZoom(modoAnterior);
        window.onafterprint = null;
    };
}

// Inicialização: Scroll para zoom
document.addEventListener('DOMContentLoaded', function() {
    const wrapper = document.getElementById('gantt-wrapper');
    if (wrapper) {
        wrapper.addEventListener('wheel', function(e) { 
            if (e.ctrlKey) { 
                e.preventDefault(); 
                if (e.deltaY < 0) { 
                    if (current_mode_index > 0) mudarZoom(view_modes[current_mode_index - 1]); 
                } else { 
                    if (current_mode_index < view_modes.length - 1) mudarZoom(view_modes[current_mode_index + 1]); 
                } 
            } 
        });
    }
});
