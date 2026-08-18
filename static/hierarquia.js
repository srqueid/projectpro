/* =========================================================
   hierarquia.js — Componente recursivo HierarchicalNode
   Funcionalidades:
     - Criação contextual (+)
     - Duplo-clique renomear (edição inline)
     - Menu ⋮ com alteração de tipo
     - Confirmação cascata de exclusão
   ========================================================= */

(function () {
    'use strict';

    // Tipos disponíveis para cada nó, conforme regra:
    //   Épico > Feature > História > Tarefa > Subtarefa
    const TIPO_LABEL = {
        epico:    'Épico',
        feature:  'Feature',
        historia: 'História',
        tarefa:   'Tarefa',
        subtarefa:'Subtarefa',
    };

    // Tipos filhos permitidos como 'atalhos' no botão + de cada pai
    const FILHOS_PERMITIDOS = {
        epico:    [ { tipo: 'feature',  label: 'Feature' },
                    { tipo: 'tarefa',   label: 'Tarefa Extraordinária' } ],
        feature:  [ { tipo: 'historia', label: 'História' } ],
        historia: [ { tipo: 'tarefa',   label: 'Tarefa' } ],
        tarefa:   [ { tipo: 'subtarefa',label: 'Subtarefa' } ],
        subtarefa: [],
    };

    // Todos os tipos (para menu de "Alterar Tipo") — exceto o atual
    const TODOS_TIPOS = ['epico','feature','historia','tarefa','subtarefa'];

    // Elementos globais (injetados após o DOM carregar)
    let $modalCriar, $modalAlterarTipo, $modalConfirmar;
    let ctxCriar, ctxAlterar, ctxExcluir;   // contexto de cada ação pendente

    function init() {
        criarModais();
        ligarBindsDocumento();
    }

    // =========================================================
    //  Criação dos modais compartilhados no <body>
    // =========================================================
    function criarModais() {
        // 1. Modal: Criar sub-item (botão +)
        $modalCriar = document.createElement('dialog');
        $modalCriar.id = 'modal-criar-subitem';
        $modalCriar.className = 'modal-config';
        $modalCriar.innerHTML = `
            <form method="dialog" class="space-y-4">
                <div class="modal-header">
                    <h3 id="mc-titulo">Criar subitem</h3>
                </div>
                <div class="space-y-3">
                    <input type="hidden" id="mc-tipo-filho">
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-1">Título</label>
                        <input id="mc-nome" type="text" required class="input-field w-full" placeholder="Nome do novo item...">
                    </div>
                    <div id="mc-campos-extras" class="space-y-2"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('modal-criar-subitem').close()">Cancelar</button>
                    <button type="submit" class="btn-primary">Criar</button>
                </div>
            </form>`;
        $modalCriar.addEventListener('close', () => {
            if ($modalCriar.returnValue === 'ok') {
                const titulo = document.getElementById('mc-nome').value.trim();
                if (!titulo) return;
                executarCriarSubitem(titulo);
            }
        });
        document.body.appendChild($modalCriar);
        $modalCriar.querySelector('form').addEventListener('submit', e => {
            e.preventDefault();
            $modalCriar.close('ok');
        });

        // 2. Modal: Alterar tipo do item (menu ⋮)
        $modalAlterarTipo = document.createElement('dialog');
        $modalAlterarTipo.id = 'modal-alterar-tipo';
        $modalAlterarTipo.className = 'modal-config';
        $modalAlterarTipo.innerHTML = `
            <form method="dialog" class="space-y-4">
                <div class="modal-header">
                    <h3>Alterar tipo do item</h3>
                </div>
                <div class="space-y-2">
                    <p id="at-msg" class="text-sm text-slate-600 mb-3">Escolha o novo tipo:</p>
                    <div id="at-opcoes-tipo" class="grid grid-cols-2 gap-2"></div>
                    <div id="at-msg-incompatibilidade" class="hidden text-xs text-red-600 mt-2"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('modal-alterar-tipo').close()">Cancelar</button>
                    <button id="at-confirmar" type="submit" class="btn-primary" disabled>Confirmar alteração</button>
                </div>
            </form>`;
        $modalAlterarTipo.addEventListener('close', () => {
            if ($modalAlterarTipo.returnValue === 'ok') {
                const novoTipo = document.querySelector('input[name="at-novo-tipo"]:checked');
                if (!novoTipo) return;
                executarAlterarTipo(novoTipo.value);
            }
        });
        document.body.appendChild($modalAlterarTipo);
        $modalAlterarTipo.querySelector('form').addEventListener('submit', e => {
            e.preventDefault();
            $modalAlterarTipo.close('ok');
        });

        // 3. Modal: Confirmação de exclusão em cascata
        $modalConfirmar = document.createElement('dialog');
        $modalConfirmar.id = 'modal-confirmar-exclusao';
        $modalConfirmar.className = 'modal-config';
        $modalConfirmar.innerHTML = `
            <form method="dialog" class="space-y-4">
                <div class="modal-header">
                    <h3 class="text-red-700">⚠ Confirmar exclusão</h3>
                </div>
                <div class="space-y-3">
                    <p id="cx-msg" class="text-sm text-slate-700"></p>
                    <ul id="cx-lista" class="text-xs text-slate-600 space-y-1 border border-slate-200 rounded-lg p-3 bg-slate-50"></ul>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('modal-confirmar-exclusao').close()">Cancelar</button>
                    <button type="submit" class="btn-danger" style="background:#dc2626;color:#fff;padding:.5rem 1rem;border-radius:.5rem;font-weight:600;border:0;cursor:pointer;">Excluir definitivamente</button>
                </div>
            </form>`;
        $modalConfirmar.addEventListener('close', () => {
            if ($modalConfirmar.returnValue === 'ok') {
                executarExclusao();
            }
        });
        document.body.appendChild($modalConfirmar);
        $modalConfirmar.querySelector('form').addEventListener('submit', e => {
            e.preventDefault();
            $modalConfirmar.close('ok');
        });
    }

    // =========================================================
    //  Binds delegados de ações disparadas nos nós
    // =========================================================
    function ligarBindsDocumento() {
        // Duplo-clique no título → renomear
        document.addEventListener('dblclick', async e => {
            const t = e.target.closest('[data-hnode-titulo]');
            if (!t) return;
            const node = t.closest('[data-hnode]');
            const tipo = node.dataset.hnodeTipo;
            const id = node.dataset.hnodeId;
            const tituloAtual = t.textContent.trim();
            const novo = prompt(`Renomear ${TIPO_LABEL[tipo]}:`, tituloAtual);
            if (novo == null || novo.trim() === '' || novo.trim() === tituloAtual) return;
            try {
                const res = await api('renomear', { tipo, id, titulo: novo.trim() });
                if (res.status === 'sucesso') {
                    t.textContent = novo.trim();
                    toastr?.success?.('Renomeado.') || alert('Renomeado.');
                } else {
                    throw new Error(res.erro || 'Falha ao renomear.');
                }
            } catch (err) {
                alert('Erro: ' + err.message);
            }
        });

        // Clique no botão + contextual
        document.addEventListener('click', e => {
            const btn = e.target.closest('[data-action="adicionar-filho"]');
            if (!btn) return;
            const node = btn.closest('[data-hnode]');
            const tipoPai = node.dataset.hnodeTipo;
            const paiId = node.dataset.hnodeId;
            abrirModalCriar(tipoPai, paiId, e);
        });

        // Clique no menu ⋮ → abrir opções
        document.addEventListener('click', e => {
            const btn = e.target.closest('[data-action="abrir-menu"]');
            if (!btn) return;
            const node = btn.closest('[data-hnode]');
            const tipo = node.dataset.hnodeTipo;
            const id = node.dataset.hnodeId;
            const titulo = node.querySelector('[data-hnode-titulo]').textContent.trim();
            abrirMenuFlutuante(btn, tipo, id, titulo);
        });

        // Clique na lixeira → confirmar exclusão cascata
        document.addEventListener('click', async e => {
            const btn = e.target.closest('[data-action="excluir-item"]');
            if (!btn) return;
            const node = btn.closest('[data-hnode]');
            const tipo = node.dataset.hnodeTipo;
            const id = node.dataset.hnodeId;
            const titulo = node.querySelector('[data-hnode-titulo]').textContent.trim();
            await abrirConfirmacaoExclusao(tipo, id, titulo, node);
        });

        // Fechar menus flutuantes abertos ao clicar fora
        document.addEventListener('click', e => {
            if (!e.target.closest('[data-menu-flutuante]') && !e.target.closest('[data-action="abrir-menu"]')) {
                document.querySelectorAll('[data-menu-flutuante]').forEach(m => m.remove());
            }
        });
    }

    // =========================================================
    //  Botão + contextual
    // =========================================================
    function abrirModalCriar(tipoPai, paiId, ev) {
        const opcoes = FILHOS_PERMITIDOS[tipoPai] || [];
        if (opcoes.length === 0) {
            alert(`${TIPO_LABEL[tipoPai]} não aceita sub-itens.`);
            return;
        }
        // Se houver mais de uma opção (ex: Épico → Feature ou Tarefa Extra), pedir escolha rápida
        let tipoFilho = opcoes[0].tipo;
        if (opcoes.length > 1) {
            const labels = opcoes.map((o,i) => `${i+1}) ${o.label}`).join('\n');
            const escolha = prompt(`Criar qual tipo de sub-item?\n${labels}\n\nDigite o número:`, '1');
            const idx = parseInt(escolha, 10) - 1;
            if (isNaN(idx) || idx < 0 || idx >= opcoes.length) return;
            tipoFilho = opcoes[idx].tipo;
        }
        ctxCriar = { tipoPai, paiId, tipoFilho };
        document.getElementById('mc-titulo').textContent = `Criar ${labelTipo(tipoFilho)}`;
        document.getElementById('mc-tipo-filho').value = tipoFilho;
        document.getElementById('mc-nome').value = '';
        document.getElementById('mc-campos-extras').innerHTML = '';
        setTimeout(() => document.getElementById('mc-nome').focus(), 50);
        $modalCriar.showModal();
    }

    async function executarCriarSubitem(titulo) {
        if (!ctxCriar) return;
        try {
            const res = await api('criar_subitem', {
                tipo_pai: ctxCriar.tipoPai,
                pai_id:   ctxCriar.paiId,
                tipo_filho: ctxCriar.tipoFilho,
                titulo,
            });
            if (res.status !== 'sucesso') throw new Error(res.erro || 'Erro ao criar');
            // Feedback leve: recarrega a página para manter sincronismo
            window.location.reload();
        } catch (err) {
            alert('Erro ao criar: ' + err.message);
        } finally {
            ctxCriar = null;
        }
    }

    // =========================================================
    //  Menu ⋮ flutuante (Alterar Tipo + atalhos)
    // =========================================================
    function abrirMenuFlutuante(ancora, tipo, id, titulo) {
        document.querySelectorAll('[data-menu-flutuante]').forEach(m => m.remove());
        const menu = document.createElement('div');
        menu.setAttribute('data-menu-flutuante', '1');
        menu.className = 'fixed z-50 bg-white border border-slate-200 rounded-lg shadow-xl py-1 text-sm w-56';
        menu.innerHTML = `
            <button type="button" data-opt="alterar-tipo" class="w-full text-left px-4 py-2 hover:bg-slate-100">🔁 Alterar tipo...</button>
            <button type="button" data-opt="renomear" class="w-full text-left px-4 py-2 hover:bg-slate-100">✏️ Renomear</button>
            <div class="my-1 border-t border-slate-100"></div>
            <button type="button" data-opt="excluir" class="w-full text-left px-4 py-2 hover:bg-red-50 text-red-600">🗑 Excluir...</button>`;
        const rect = ancora.getBoundingClientRect();
        menu.style.left = (window.innerWidth - rect.right < 240 ? rect.right - 224 : rect.right - 4) + 'px';
        menu.style.top  = (rect.bottom + 4) + 'px';
        menu.addEventListener('click', async e => {
            const opt = e.target.closest('[data-opt]');
            if (!opt) return;
            menu.remove();
            if (opt.dataset.opt === 'alterar-tipo') abrirModalAlterarTipo(tipo, id, titulo);
            if (opt.dataset.opt === 'renomear') {
                const novo = prompt(`Renomear ${labelTipo(tipo)}:`, titulo);
                if (novo && novo.trim() !== titulo) {
                    const r = await api('renomear', { tipo, id, titulo: novo.trim() });
                    if (r.status === 'sucesso') window.location.reload();
                    else alert(r.erro || 'Falha');
                }
            }
            if (opt.dataset.opt === 'excluir') {
                const node = document.querySelector(`[data-hnode-id="${id}"][data-hnode-tipo="${tipo}"]`);
                await abrirConfirmacaoExclusao(tipo, id, titulo, node);
            }
        });
        document.body.appendChild(menu);
    }

    // =========================================================
    //  Modal: Alterar tipo
    // =========================================================
    async function abrirModalAlterarTipo(tipoAtual, id, titulo) {
        ctxAlterar = { tipoAtual, id, titulo };
        const grid = document.getElementById('at-opcoes-tipo');
        grid.innerHTML = '';
        let selecionado = null;
        const btnConf = document.getElementById('at-confirmar');
        const msgIncomp = document.getElementById('at-msg-incompatibilidade');
        msgIncomp.classList.add('hidden');

        TODOS_TIPOS.filter(t => t !== tipoAtual).forEach(t => {
            const radio = document.createElement('label');
            radio.className = 'flex items-center gap-2 p-2 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50';
            radio.innerHTML = `
                <input type="radio" name="at-novo-tipo" value="${t}">
                <span>${labelTipo(t)}</span>`;
            radio.querySelector('input').addEventListener('change', ev => {
                selecionado = t;
                btnConf.disabled = false;
            });
            grid.appendChild(radio);
        });
        btnConf.disabled = true;
        document.getElementById('at-msg').innerHTML = `Alterar "<strong>${escapeHtml(titulo)}</strong>" (${labelTipo(tipoAtual)}):`;
        $modalAlterarTipo.showModal();
    }

    async function executarAlterarTipo(novoTipo) {
        if (!ctxAlterar) return;
        try {
            const res = await api('alterar_tipo', {
                tipo_atual: ctxAlterar.tipoAtual,
                id: ctxAlterar.id,
                novo_tipo: novoTipo,
            });
            if (res.status !== 'sucesso') throw new Error(res.erro || 'Falha ao alterar tipo.');
            window.location.reload();
        } catch (err) {
            alert('Erro ao alterar tipo: ' + err.message);
        } finally {
            ctxAlterar = null;
        }
    }

    // =========================================================
    //  Confirmação de exclusão cascata
    // =========================================================
    async function abrirConfirmacaoExclusao(tipo, id, titulo, node) {
        const msg = document.getElementById('cx-msg');
        const lista = document.getElementById('cx-lista');
        ctxExcluir = { tipo, id, node };
        msg.innerHTML = `Deseja realmente excluir o <strong>${labelTipo(tipo)}</strong> "<strong>${escapeHtml(titulo)}</strong>"?`;
        lista.innerHTML = '<li class="text-slate-400">Carregando impactos...</li>';
        $modalConfirmar.showModal();
        try {
            const counts = await api('contar_filhos', { tipo, id });
            const itens = [];
            if (counts.feature)   itens.push(`<li>• <strong>${counts.feature}</strong> Feature(s)</li>`);
            if (counts.historia)  itens.push(`<li>• <strong>${counts.historia}</strong> História(s)</li>`);
            if (counts.tarefa)    itens.push(`<li>• <strong>${counts.tarefa}</strong> Tarefa(s)</li>`);
            if (counts.subtarefa) itens.push(`<li>• <strong>${counts.subtarefa}</strong> Subtarefa(s)</li>`);
            if (itens.length === 0) itens.push('<li class="text-slate-400">Nenhum item filho associado.</li>');
            itens.unshift(`<li class="font-semibold text-slate-700">Itens impactados (${counts.total || 0}):</li>`);
            lista.innerHTML = itens.join('');
        } catch (err) {
            lista.innerHTML = `<li class="text-red-600">Não foi possível calcular impactos (${err.message}).</li>`;
        }
    }

    function executarExclusao() {
        if (!ctxExcluir) return;
        const { tipo, id } = ctxExcluir;
        // Monta URL da rota de exclusão correspondente
        const mapaUrl = {
            epico:    'excluir_epico',
            feature:  'excluir_feature',
            historia: 'excluir_historia',
            tarefa:   'excluir_tarefa',
            subtarefa:'excluir_subtarefa',
        };
        const rota = mapaUrl[tipo];
        if (!rota) { alert('Tipo inválido.'); return; }
        // Usa o formulário POST existente via submit programático para CSRF/simplicidade
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = window.HIERARQUIA_URLS[rota].replace('__ITEM_ID__', id);
        document.body.appendChild(form);
        form.submit();
    }

    // =========================================================
    //  Helpers
    // =========================================================
    function labelTipo(t) { return TIPO_LABEL[t] || t; }

    function escapeHtml(texto) {
        return String(texto ?? '').replace(/[&<>"']/g, c => ({
            '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
        }[c]));
    }

    async function api(acao, body) {
        if (!window.HIERARQUIA_URLS) throw new Error('Configuração HIERARQUIA_URLS ausente.');
        const url = window.HIERARQUIA_URLS[acao];
        if (!url) throw new Error(`Ação "${acao}" não mapeada.`);
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(dados.erro || `HTTP ${resp.status}`);
        return dados;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
