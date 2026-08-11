# TODO — Tela de Cadastro de Empresas e Perfis

## Plano Aprovado

1. **Backend (`app/project_manager.py`)**
   - [x] Adicionar funções `adicionar_perfil`, `editar_perfil`, `excluir_perfil` para gerenciar perfis em `rh.perfis`.

2. **Rotas (`app/routes.py`)**
   - [x] Criar rotas `/perfis/adicionar`, `/perfis/editar/<id>`, `/perfis/excluir/<id>`.
   - [x] Passar `perfis` para a rota `empresas()`.

3. **Template (`templates/empresas.html`)**
   - [x] Adicionar cadastro/edição de empresas (nome, CNPJ, ativo) + listagem + exclusão.
   - [x] Adicionar seção "Perfis": cadastro (nome, descrição), listagem, edição e exclusão.

## Follow-up
- [ ] Rodar e validar a aplicação.
