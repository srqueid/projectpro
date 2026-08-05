# TODO: Ajustar todos os modais do sistema

## Passos a concluir

- [x] **1. base.css**: Criar sistema global de modais (.modal-config, .modal-header, .modal-body, .modal-footer, .modal-close, backdrop, animações, responsivo)
- [x] **2. kanban.css**: Remover bloco .modal-config antigo (agora global)
- [x] **3. base.js**: Adicionar helpers globais: fecharModal(id), fechar ao clicar no backdrop
- [x] **4. home.html**: Carregar base.css + reestruturar modal-novo com header/body/footer padronizados + aria-label
- [x] **5. kanban.html**: Reestruturar modal-nova-tarefa e modal-editar-tarefa + criar modal-config-colunas + botão Configurar
- [x] **6. detalhes_projeto.html**: Reestruturar modal-novo-item com header/body/footer padronizados
- [x] **7. backlog.html**: Reestruturar modal-planejar com header/body/footer padronizados
- [x] **8. kanban.js**: Ajustar fluxo do modal-config-colunas (usar helper global, fechar após salvar)
- [ ] **9. Testar todos os modais**
