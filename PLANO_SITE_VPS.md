# 🏗️ Plano de Migração — HermesMed para Site Próprio na VPS

**Data:** 03/08/2026
**Autor:** Hermes (assistente Enzo)
**Status:** Proposta a validar

---

## 1. Objetivo

Transformar a plataforma atual (GitHub Pages, 100% estática) num **site próprio com backend**, hospedado na VPS de Enzo, habilitando funções que exigem servidor:

- Login real e progresso na nuvem
- Sincronização automática entre dispositivos
- Comentários por questão
- **IA que monta planos de estudo personalizados** (análise de erros → plano adaptativo)

---

## 2. Contexto atual (o que já existe)

| Item | Situação |
|---|---|
| Frontend | `index.html`, `questoes.html`, `sessao.html`, `desempenho.html`, `simulados.html`, `flashcard.html` — interface mobile-first |
| Banco de questões | **615 questões** em `data/*.json` (6+ áreas), 327 imagens corrigidas |
| Progresso | `localStorage` + sync manual via GitHub (`mooncake-stash`) |
| Autenticação | Senha única local (`login.html`, hash SHA-256) |
| Hosting | GitHub Pages (estático, grátis) |

**Infra da VPS (medida agora):**
- Ubuntu 24.04 LTS, x86_64
- **RAM: 954 MB** (usada ~541 MB — sobra ~400 MB!) ⚠️
- Disco: 45 GB (32 GB disponíveis)
- Node v22.23.1 ✓, Python 3.11 ✓
- Sem Nginx, sem Docker instalado

---

## 3. Arquitetura proposta

### 3.1 Stack recomendado (leve, cabe em 1GB de RAM)

| Camada | Escolha | Por quê |
|---|---|---|
| Backend | **Node.js v22 + Express** | Já instalado; em JSON; leve |
| Banco de dados | **SQLite** (via better-sqlite3) | Zero configuração, arquivo único, ~zero RAM — perfeito pra 1GB |
| Autenticação | **JWT** (access + refresh) | Stateless, simples, funciona em dispositivo móvel |
| Backup | **`sqlite3 .backup`** + cron diário → GitHub/Onedrive | Barato e seguro |
| Frontend | Reaproveita o HTML/JS atual, servido pelo backend | Menor esforço |
| HTTPS | **Caddy** (auto-TLS, mais leve que nginx) ou Nginx + Let's Encrypt | Certificado grátis |

### 3.2 Por que SQLite e não Postgres?
- **1GB de RAM é apertado** — Postgres + Node estoura fácil
- SQLite suporta a carga de 1 usuário sem problema (dezenas de milhares de operações/s)
- Backup = copiar 1 arquivo
- Migração futura p/ Postgres é possível se crescer

### 3.3 Diagrama (ascii)

```
            ┌───────────────┐
   Celular/PC│  Navegador     │
            └──────┬────────┘
                   │ HTTPS
            ┌──────▼────────┐        ┌──────────────┐
            │  Nginx/Caddy  │───────►│ Node/Express  │
            │ (TLS/Cert)    │        │   backend    │
            └───────────────┘        └──────┬───────┘
                                            │
                                     ┌──────▼───────┐
                                     │  SQLite DB   │  hermesmed.db
                                     │ + arquivos   │  (imgs/PDFs)
                                     └──────────────┘
```

---

## 4. Modelo de dados (SQLite)

```sql
-- Usuários
users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  senha_hash TEXT NOT NULL,        -- bcrypt/argon2
  nome TEXT,
  instituicoes_interesse TEXT,     -- JSON array
  criado_em TEXT
)

-- Progresso por questão (avulsas)
progresso (
  user_id INTEGER,
  questao_id TEXT,
  area TEXT,
  acertou INTEGER,                 -- 0/1
  selecao TEXT,
  timestamp TEXT,
  PRIMARY KEY (user_id, questao_id)
);

-- Log de atividades (p/ heatmap/streak)
atividade (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  questao_id TEXT,
  area TEXT NOT NULL,
  acertou INTEGER,
  fonte TEXT,
  ts TEXT,
  modo TEXT
);

-- Sessões personalizadas (em andamento/concluídas)
sessoes (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  nome TEXT,
  ids TEXT,            -- JSON array
  total INTEGER,
  status TEXT,         -- 'em_andamento'|'concluida'
  pct INTEGER,
  criada TEXT, concluida TEXT
);

-- Comentários por questão
comentarios (
  id INTEGER PRIMARY KEY,
  questao_id TEXT,
  user_id INTEGER,
  texto TEXT,
  created_at TEXT
);

-- Planos de estudo personalizados (gerados por IA)
planos (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  titulo TEXT,
  descricao TEXT,
  conteudo TEXT,          -- JSON: etapas/dias/tópicos
  fonte TEXT,             -- 'ia' | 'manual'
  criado_em TEXT,
  status TEXT             -- 'ativo' | 'concluido' | 'arquivado'
);

-- Dias/etapas do plano
plano_dias (
  id INTEGER PRIMARY KEY,
  plano_id INTEGER,
  dia INTEGER,            -- dia do plano
  foco TEXT,              -- ex: "Endocrinologia - Diabetes"
  qtd_questoes INTEGER,
  concluido INTEGER DEFAULT 0
);

-- Ranking semanal (adiado — tabela futura, não implementar agora)
-- decks/flashcards compartilhados (adiado — não implementar agora)
```

---

## 5. API (endpoints principais)

### Autenticação
| Método | Rota | Função |
|---|---|---|
| POST | `/api/auth/registrar` | cria conta |
| POST | `/api/auth/login` | retorna JWT |
| GET | `/api/auth/me` | dados do perfil |

### Progresso
| Método | Rota | Função |
|---|---|---|
| GET | `/api/progresso/:user` | sobre progresso |
| PUT | `/api/progresso/:questao` | salva 1 questão (acertou/selecao) |
| GET | `/api/log/:user` | log de atividades (heatmap) |

### Social / Extras
| Método | Rota | Função |
|---|---|---|
| GET | `/api/comentarios/:questao` | comentários de uma questão |
| POST | `/api/comentarios` | novo comentário |
| POST | `/api/sessoes` | salva sessão personalizada |
| GET | `/api/sessoes/:user` | lista sessões |

### IA — Planos de estudo personalizados
| Método | Rota | Função |
|---|---|---|
| POST | `/api/ia/plano` | gera plano de estudo (Gemini): analisa erros + metas → plano com dias/tópicos/qtd |
| GET | `/api/planos/:user` | lista planos do usuário |
| POST | `/api/planos/:id/dias/:dia/concluir` | marca dia do plano como feito |
| DELETE | `/api/planos/:id` | remove plano |

### Estático
- `/` → serve index.html
- `/data/*.json` → banco de questões (o mesmo de hoje)
- `/imgs/*` → imagens (cada simulado)

---

## 6. Migração dos dados atuais

1. **Backup** dos `*.json` e das 327 imagens → já estão no git/deploy
2. **Seed do banco**: na 1ª inicialização, imprimir as 615 questões + 327 imagens do `.json` p/ SQLite (ou manter em JSON e apontar o backend pra pasta)
3. **Migrar progresso do localStorage**:
   - O site atual permite **exportar JSON** (botão no painel de sync)
   - No login no site novo, oferecer "Importar progresso do GitHub Pages" (upload do JSON exportado)
4. **Identificar questões** pelo mesmo `id` (ex: `s1-007`) — já compatível

---

## 7. Etapas de implementação (fases)

### Fase 0 — Preparação (estimativa: poucas horas)
- [ ] Instalar Nginx ou Node (se precisar) na VPS
- [ ] Escolher domínio (ex: `hermesmed.com.br` ou subdomínio)
- [ ] Configurar backup automático inicial

### Fase 1 — Backend base (Núcleo) (alguns dias)
- [ ] Projeto Node/Express + SQLite (schema do item 4)
- [ ] Auth JWT (register/login)
- [ ] API de progresso + log (PUT/GET)
- [ ] Servir o frontend atual estaticamente
- [ ] **Meta**: site acessível na VPS, já salvando progresso online

### Fase 2 — Frontend conectado
- [ ] Substituir `login.html` por login real (JWT)
- [ ] Trocar `localStorage` por chamadas à API (incremental: progresso, streak, log)
- [ ] Autoconexao entre celular e PC (sincronizar)
- [ ] Dark/light já existe

### Fase 3 — Funcionalidades sociais (Medeor-like, sem ranking/compartilhamento)
- [ ] **Comentários/discussão** por questão
- [ ] **Calendário de estudos** + notificações leves

### Fase 4 — IA de planos de estudo (Gemini)
- [ ] Endpoint `/api/ia/plano`: recebe histórico de erros/acertos + metas do usuário
- [ ] Gemini gera plano personalizado: dias, tópicos prioritários (piores áreas primeiro), qtd de questões por dia, revisões espaçadas
- [ ] Página "Meu Plano": visualiza plano, marca dias concluídos, gera sessão personalizada automaticamente com as questões do dia
- [ ] Replanejamento automático quando o usuário erra muito num tópico
- [ ] Dashboard comparativo (acertos × média)

### Fase 5 — Infra robusta
- [ ] Backups automáticos (SQLite emitido pro Onedu/Drive diariamente)
- [ ] Certificado TLS (Let's Encrypt) + HTTPS forçado
- [ ] Monitoramento simples (uptime)

---

## 8. Custos e recursos

| Item | Custo |
|---|---|
| VPS (já paga) | R$ 0 extra |
| Domínio | R$ 20-40/ano (se quiser) |
| Certificado TLS | Grátis (Let's Encrypt) |
| API de IA do Google | Já disponível no plano Google One |

**RAM restante (~400MB)** dá para Node+SQLite+backups tranquilo. Não estoure com Postgres/Redis por agora.

---

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| 1GB RAM insuficiente | Usar SQLite + Node leve; evitar Redis/Postgres; monitorar uso |
| Perda de dados | Backup do `.db` diário p/ Onedrive/GitHub |
| Downtime da VPS | GitHub Pages continua como fallback (site atual não para) |
| Segurança (auth) | Argon2/bcrypt pra senha, JWT com expiração, rate limit |
| Migração do progresso | Importar via export atual funciona |

---

## 10. Próximo passo concreto

`hermes` (eu) posso **lançar a Fase 1** agora:
1. Criar a estrutura do backend Node/Express + SQLite na VPS (pasta `~/hermesmed-server`)
2. Fazer `auth` + API de progresso
3. Rodar um teste local e confirmar que a base de dados funciona
4. Mostrar você acessando `localhost`/HTTP

Quer que eu comece a **Fase 1** (montar o backend com login + progresso na VPS)? Ou prefere detalhar antes outra parte (domínio, custos, backend)?

Me diz e eu avanço. 🚀