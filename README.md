# agent-dev

**Framework-free multi-agent orchestrator** — 5개 AI 에이전트를 LangGraph/CrewAI 없이 순수 Python으로 오케스트레이션합니다.

## Why

AI 에이전트 프레임워크(LangGraph, CrewAI, AutoGen)는 빠른 프로토타이핑엔 좋지만, 프로덕션에서는 디버깅이 어렵고 프레임워크 업데이트에 종속됩니다. 이 프로젝트는 **supervisor 패턴을 60~150줄**로 직접 구현하여, LLM = 판단·생성, 코드 = 실행·검증·IO라는 원칙을 증명합니다.

## Architecture

```
┌──────────────────────────────────────────┐
│  Entry Points                            │
│  ├── FastAPI (/chat, /ingest, /webhook)  │
│  ├── Streamlit UI (Chat, Digest, Ingest) │
│  ├── APScheduler (Daily 07:00 curation)  │
│  └── CLI (eval, QA gen)                  │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│  Supervisor (framework-free)             │
│  Gemini function_calling → intent route  │
└──────────────────┬───────────────────────┘
                   ▼
  ┌────────┬───────┬────────┬──────────┐
  ▼        ▼       ▼        ▼          ▼
[RAG]  [Curator] [Research] [CI Triage] [QA Gen]
  │        │       │        │          │
  └────────┴───────┴────────┴──────────┘
                   ▼
           Common Tool Layer
  (LLM wrapper · GitHub · vector · web)
                   ▼
           Postgres + pgvector
```

## 5 Agents

| Agent | Trigger | What it does |
|---|---|---|
| **RAG** | Chat | 문서 검색 → 인용 포함 답변. pgvector 코사인 유사도 + 재검색 판정 |
| **Web Curation** | Cron (07:00) | HN · Reddit · GitHub Trending · arXiv → Gemini 랭킹 → Slack 다이제스트 |
| **Deep Research** | Chat | 질문 분해 → 병렬 웹/RAG 검색 → 인용 리포트 합성 → self-critique |
| **CI Triage** | GitHub Webhook | Actions 실패 로그 분석 → 원인·재현·해결안 → PR 코멘트 자동 작성 |
| **QA Test Gen** | CLI / API | AST 함수 추출 → pytest 자동 생성 → 실행 → 자기 수정 (max 3회) |

## Stack

| Component | Choice | Why |
|---|---|---|
| LLM | Gemini 2.5 Flash + Pro fallback | 30x cheaper than Claude, circuit breaker + fallback |
| Framework | None | Supervisor 직접 구현 (60~150 LOC) |
| Language | Python 3.12 | |
| Backend | FastAPI + uvicorn | |
| DB | Postgres 16 + pgvector | HNSW index, 768-dim embeddings |
| Embedding | gemini-embedding-001 | |
| Scheduler | APScheduler | Cron expressions |
| Observability | Langfuse | Trace · cost dashboard |
| UI | Streamlit | Chat · Digest · Ingest · Eval tabs |

## Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/hheee0808/agent_dev.git
cd agent_dev
uv venv && .venv/Scripts/activate  # Windows
uv sync

# 2. Environment
cp .env.example .env  # Edit with your API keys

# 3. Database
docker compose -f docker/docker-compose.dev.yml up -d

# 4. Run
# API server
uvicorn backend.web.app:app --reload

# Streamlit UI (separate terminal)
streamlit run app.py

# Run evaluations
python -m evals.run
```

## Project Structure

```
agent-dev/
├── app.py                      # Streamlit UI
├── backend/
│   ├── common/                 # Shared core modules
│   │   ├── llm.py              # Gemini wrapper (retry, circuit breaker, fallback)
│   │   ├── supervisor.py       # Framework-free intent classifier + dispatch
│   │   ├── agent_base.py       # Agent ABC
│   │   ├── tool.py             # Tool registry
│   │   └── trace.py            # Langfuse observability
│   ├── agents/
│   │   ├── rag/                # RAG agent (retriever + generator)
│   │   ├── curator/            # Web curation (sources, ranker, slack)
│   │   ├── research/           # Deep research (planner, searcher, synthesizer)
│   │   ├── ci_triage/          # CI failure analysis (github API, analyzer)
│   │   └── qa_gen/             # Test generation (AST extractor, runner)
│   ├── web/
│   │   ├── app.py              # FastAPI entry point
│   │   └── github_hook.py      # GitHub webhook handler
│   ├── ingest/                 # Document pipeline (loader, chunker, embedding)
│   └── scheduler.py            # APScheduler daily cron
├── docker/
│   └── docker-compose.dev.yml  # Postgres + pgvector
├── evals/
│   ├── harness.py              # Eval framework (LLM-as-judge)
│   ├── cases.json              # Test cases
│   └── run.py                  # CLI runner
└── pyproject.toml
```

## Key Design Decisions

1. **No framework** — Supervisor is ~100 lines of Gemini function_calling. No LangGraph state machines, no CrewAI role definitions. Just a dict of agents and an intent classifier.

2. **Circuit breaker + fallback** — Flash → Pro automatic failover. Per-model breaker with configurable thresholds. 503s are absorbed, not exposed to users.

3. **Self-healing patterns** — QA agent fixes its own failing tests (max 3 rounds). Deep Research agent critiques and revises its own reports.

4. **Domain-independent architecture** — Swap data files and configs to apply to any domain (healthcare, gaming, finance). The orchestration layer stays the same.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Status + registered agents |
| POST | `/chat` | Supervisor-routed chat |
| POST | `/ingest` | Document upload → chunk → embed |
| POST | `/curator/run` | Manual curation trigger |
| POST | `/webhook/github` | GitHub Actions failure webhook |

## License

MIT
