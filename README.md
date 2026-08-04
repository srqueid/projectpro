# 📋 ProjectPro — Sistema de Gestão de Projetos e Cronogramas

**ProjectPro** é uma aplicação web completa para gestão de projetos, planejamento de cronogramas, acompanhamento de tarefas em **Kanban**, **Planilha** interativa e **Gantt** (Timeline). Construída com **Flask (Python)**, banco de dados **PostgreSQL** e interface moderna com **Tailwind CSS**.

---

## 🚀 Funcionalidades Principais

### 📂 Gestão de Projetos
- **Criar projeto** do zero (planilha em branco) ou **importar via CSV**
- **Listar projetos** em dashboard com estatísticas de progresso (média %, concluídas, em andamento)
- **Excluir projetos** com confirmação
- **Descrição do projeto** (objetivo macro) editável
- **Associação de time** ao projeto

### 🗂️ Hierarquia de Itens (Épico > Feature > História > Tarefa > Subtarefa)
- **Épico** — maior agrupamento de trabalho (nível mais alto)
- **Feature** — funcionalidade/módulo, filha de Épico
- **História (Story)** — requisito do ponto de vista do usuário, com **critérios de aceite**
- **Tarefa** — passo técnico para completar histórias
- **Subtarefa** — detalhamento da tarefa
- Criação de itens via modal com **regras de hierarquia** (cada tipo só pode ter pais permitidos)
- Visualização em **Detalhes do Projeto** com cards por tipo, badges coloridos e estatísticas
- **Validação de referência circular** na hierarquia pai-filho (backend e frontend)

### 📊 Planilha (Spreadsheet Interativa)
- Edição **inline** em tabela estilo Excel (Fase, Tarefa, Subtarefa, Datas, Dias, Predecessora, Responsável, %)
- **Salvamento automático** (autosave com debounce) com indicador de status
- **Desfazer (Undo)** — histórico de alterações
- **Recálculo automático de datas** em cascata ao alterar dias, predecessoras ou datas
- **Ordenação** por colunas (ID, Fase, Tarefa, Dias, Predecessora, Responsável, %)
- **Reordenação de linhas** e **colunas** via drag-and-drop
- **Hierarquia pai-filho visual**: indentação, expandir/recolher, vincular linha à linha acima (com proteção contra ciclos)
- **Validação de datas**: fim não pode ser anterior ao início (real e planejado)
- **Conflito de férias**: alerta visual ⚠️ quando a tarefa conflita com férias do responsável
- **Mover para "Em Andamento"** automaticamente ao preencher data de início
- **Definir restrição manual de início** (RN015) com alerta de conflito com predecessora
- **Excluir tarefas** com filhos (revincula filhos ao avô)
- **Alteração de tipo** inline (Épico/Feature/História/Tarefa/Subtarefa) com badge visual
- **Exportar para Excel** (.xlsx)
- **Imprimir / PDF**
- **Modelo de importação CSV** para download

### 📋 Backlog & Planejamento de Sprints
- Lista de **itens não planejados** (backlog) com filtro por tipo
- **Planejar item** para um Sprint (aparece no Kanban)
- **Desplanejar** item (volta ao backlog)
- Separação visual entre **Planejados** e **Backlog**

### 🗂️ Kanban Board
- **Drag-and-drop** de cards entre colunas (SortableJS)
- **4 colunas padrão**: 📋 Backlog → 🚀 Iniciar → ⚙️ Em Andamento → ✅ Concluído
- **Configuração de colunas** (RN020): criar, renomear, reordenar, definir % de progresso padrão
- **Atribuição automática de datas**: início ao entrar em "Iniciar"/"Em Andamento", fim ao concluir
- **RN019**: concluir tarefa na coluna final (conclusão = 100% e data de fim)
- **RN018**: exigir responsável para mover para coluna "Iniciar"
- **RN022**: preencher data de início ao mover para "Em Andamento"
- **RN023**: **bloqueio por dependência** — tarefa com predecessora não concluída fica bloqueada (🔒)
- **RN024**: **tarefas vencidas/em atraso** — destaque visual com badge de dias de atraso
- **Fluxo com allow_back**: configurar se a coluna permite movimento reverso (voltar)
- **Edição de tarefa** em modal com histórico de **atividades e comentários**
- **Avatar colorido** do responsável com iniciais
- **Nova tarefa** diretamente em qualquer coluna
- **Replanejar tarefa**: limpa datas e volta ao backlog

### 📈 Cronograma (Gantt / Timeline)
- Gráfico de Gantt com **Frappe Gantt**
- **Barra de Planejamento (baseline)** e **barra de Execução Real** lado a lado
- **Cores de status**:
  - 🔵 Planejamento
  - 🟢 Execução (no prazo)
  - 🟠 Atraso leve (até o limite da tolerância)
  - 🔴 Atraso grave (acima da tolerância)
- **Dependências entre tarefas** (setas de predecessoras)
- **Zoom**: 6h, 12h, Dia, Semana, Mês (botões ou Ctrl + Scroll)
- **Tooltip** com detalhes (tipo, datas, progresso)
- **Tela cheia** (fullscreen) e **Imprimir PDF**
- **Tolerância de atraso configurável** por projeto (% sobre a duração planejada)

### 👥 Responsáveis (Recursos Humanos)
- Cadastro de **responsáveis** (nome, e-mail, modelo de trabalho, horas semanais)
- **Períodos de férias** múltiplos por responsável
- Modelos de trabalho: Home Office, Híbrido, Alocado
- **Cálculo de datas** ignora férias dos responsáveis e alerta conflitos
- Editar e excluir responsáveis

### 👥 Times (Equipes)
- Cadastro de **times** com membros (relação N:M com responsáveis)
- **Associação de time** ao projeto
- Editar e excluir times

### 📅 Feriados e Bloqueios
- **Feriados nacionais** do Brasil (biblioteca `holidays`, com fallback manual)
- **Feriados customizados** (adicionar manualmente ou **importar CSV**)
- **Bloquear fins de semana** (Sáb/Dom) no cálculo de datas (configurável)
- O cálculo de dias úteis considera feriados e fins de semana

### 📝 Atividades e Comentários
- **Log de alterações** automático (campo alterado, de X para Y)
- **Comentários** por tarefa com autor e data/hora
- Exibição no modal de edição do Kanban

### 🔄 Recálculo de Datas em Cascata
- Usa **baseline_inicio/baseline_fim** (planejado) e **inicio/fim** (real)
- Considera **predecessoras** (fim da predecessora define início da sucessora)
- Aplica **restrições manuais** (início não antes de)
- **Agrega datas dos filhos nos pais**: pai começa no início da primeira filha e termina no fim da última
- Ignora **feriados, fins de semana (opcional) e férias**

---

## ⚙️ Requisitos / Regras de Negócio (RN) Implantados

| Código | Requisito | Status |
|--------|-----------|--------|
| RN015 | Restrição manual de data de início com alerta de conflito com predecessora | ✅ |
| RN016 | Recalcular o projeto ao concluir tarefa (adiantar sucessoras) | ✅ |
| RN018 | Exigir responsável atribuído para mover tarefa para "Iniciar" | ✅ |
| RN019 | Concluir tarefa ao movê-la para coluna final (fim + 100%) | ✅ |
| RN020 | Configuração de colunas do Kanban (criar, renomear, reordenar) | ✅ |
| RN022 | Preencher data de início ao mover para coluna "Em Andamento" | ✅ |
| RN023 | Bloqueio de tarefa por dependência de predecessora não concluída | ✅ |
| RN024 | Identificação de tarefas vencidas/em atraso (dias de atraso) | ✅ |
| — | Hierarquia Épico > Feature > História > Tarefa > Subtarefa | ✅ |
| — | Validação de referência circular na hierarquia | ✅ |
| — | Fluxo de transição entre colunas com `allow_back` | ✅ |
| — | Recálculo automático de datas em cascata | ✅ |
| — | Salvamento automático com desfazer (undo) | ✅ |
| — | Conflito de férias do responsável no agendamento | ✅ |

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3** / **Flask**
- **psycopg2** — driver PostgreSQL
- **pandas** — importação/exportação de planilhas
- **openpyxl** — exportação Excel
- **holidays** — feriados nacionais brasileiros
- **gunicorn** — servidor WSGI (produção)

### Frontend
- **Tailwind CSS** (via CDN/CLI)
- **SortableJS** — drag-and-drop
- **Frappe Gantt** — gráfico de Gantt
- **Inter font** (Google Fonts)

### Banco de Dados
- **PostgreSQL** (schema versionado em `schema.sql` com migrações idempotentes em `app/migrations.py`)
- **Schemas por domínio** (sem utilizar o schema `public`):
  - `rh` → Recursos Humanos: `responsaveis`, `ferias`, `times`, `responsaveis_times`
  - `projeto` → Projetos: `projetos`, `tarefas`, `kanban_colunas`, `tarefa_atividades`, `projeto_configuracoes`
  - `config` → Configurações: `configuracoes`, `feriados_customizados`
- O `search_path` da conexão é configurado em `app/config.py` (`SEARCH_PATH`) e aplicado em `app/database.py`.
- A extensão `uuid-ossp` permanece no schema `public`, que é incluído no `search_path` para manter a função `uuid_generate_v4()` acessível.

---

## 📁 Estrutura do Projeto

```
projectpro/
├── run.py                        # Entrada da aplicação (porta 5051 em dev)
├── schema.sql                    # Script de criação de tabelas (PostgreSQL)
├── requirements.txt              # Dependências Python
├── package.json                  # Dependências npm (Tailwind)
├── README.md                     # Este arquivo
├── TODO.md                       # Histórico de melhorias implantadas
├── app/
│   ├── __init__.py               # Factory da aplicação Flask
│   ├── config.py                 # Configurações (paths, banco, feriados)
│   ├── database.py               # Conexão com PostgreSQL
│   ├── migrations.py             # Migrações evolutivas idempotentes
│   ├── project_manager.py        # Regras de negócio (cálculos, kanban, etc.)
│   ├── routes.py                 # Rotas HTTP da aplicação
│   └── utils.py                  # Funções utilitárias (datas, feriados)
├── static/                       # CSS e JS
│   ├── tailwind.css              # CSS compilado do Tailwind
│   ├── theme.css                 # Tema e estilos globais
│   ├── base.js                   # Sidebar e utilitários
│   ├── kanban.js                 # Lógica do Kanban
│   ├── planilha.js               # Lógica da planilha (autosave, hierarquia)
│   └── cronograma.js             # Lógica do Gantt
├── templates/                    # Templates Jinja2
│   ├── base.html                 # Layout base (sidebar)
│   ├── home.html                 # Dashboard de projetos
│   ├── detalhes_projeto.html     # Detalhes e hierarquia
│   ├── backlog.html              # Backlog e planejamento
│   ├── planilha.html             # Planilha interativa
│   ├── kanban.html               # Kanban board
│   ├── cronograma.html           # Gantt/Timeline
│   ├── configuracoes.html        # Configurações gerais
│   └── configuracoes_projeto.html# Configurações do projeto
├── data/                         # Dados locais (se aplicável)
├── projects/                     # Pastas de projetos (se aplicável)
└── tests/                        # Testes unitários
```

---

## 🧪 Testes

Os testes unitários estão em `tests/test_project_manager.py` e cobrem a lógica do Kanban config:

```bash
python -m unittest discover tests
```

---

## 🚀 Como Executar Localmente

### 1. Pré-requisitos
- Python 3.10+
- Node.js (para Tailwind, opcional)
- PostgreSQL (ou usar a string de conexão existente no `app/config.py`)

### 2. Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 3. Instalar dependências Node (opcional — para recompilar Tailwind)
```bash
npm install
npm run build:css   # recompila o static/tailwind.css
```

### 4. Inicializar o banco de dados
```bash
flask --app run init-db
```
> A string de conexão está em `app/config.py` (`DATABASE_URI`). Para produção, use variável de ambiente.

### 5. Executar a aplicação
```bash
python run.py
```
Acesse: **http://localhost:5051**

---

## 📌 Observações

- O banco de dados usa **PostgreSQL na nuvem (Neon)** já configurado em `app/config.py`.
- As **migrações** são executadas automaticamente na inicialização da aplicação (`app/migrations.py`) e são **idempotentes** (seguras para rodar múltiplas vezes).
- Em produção, recomenda-se servir com **gunicorn** e configurar a `DATABASE_URI` e `SECRET_KEY` via **variáveis de ambiente**.

