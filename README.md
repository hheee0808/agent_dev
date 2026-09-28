# agent-dev — AI 에이전트 개발자용 통합 도구

이력용 개인 포트폴리오 프로젝트. AI 에이전트 개발자 이직 목표로 만들며, 5개 sub-agent를 framework-free supervisor로 오케스트레이션한다.

---

## 프로젝트 목적

- **직접 목적**: AI 에이전트 개발자 포지션 이직용 포트폴리오
- **타깃 회사군**: AI 응용 회사 (도메인 서비스에 AI 붙이는 조직). 인프라 회사(Anthropic·Cursor)는 첫 진입지로 제외
- **서사**: "AI 에이전트 개발자 이직 준비하며, AI 에이전트 개발자용 도구를 직접 만들었다" — 재귀적 스토리로 dogfooding 강조

---

## 도메인

- **주 도메인**: AI 에이전트 개발 (Anthropic·OpenAI·Gemini SDK, MCP, LangGraph, agent 아키텍처)
- **원칙**: 아키텍처는 도메인 독립. 나중에 다른 도메인(성형·게임·투자 등)으로 바꿔도 데이터·설정 파일만 교체하면 재사용 가능.

---

## 5개 에이전트

| 에이전트 | 트리거 | 뭐 함 | 재활용 여부 |
|---|---|---|:---:|
| RAG | 채팅형 (사용자 질문) | AI 에이전트 관련 문서 검색·답변·인용 | 기존 rag_chatbot 부분 재활용 |
| 웹 큐레이션 | 스케줄형 (매일 07:00 cron) | HN·Reddit·GitHub trending·arxiv 순회 → 개인화 다이제스트 → Slack 발송 | 신규 |
| Deep Research | 채팅형 (요청 시) | sub-question 분해 → 다단계 웹 검색·RAG → 인용 포함 리포트 | 완전 신규 |
| CI 트리아지 | 이벤트형 (GitHub Actions 실패 webhook) | 로그 분석 → 원인·재현·해결안 → PR 코멘트 | 기존 build_failure 참고 (Jenkins→GitHub 재작성) |
| QA 테스트 생성 | 수동 CLI (초기) → PR 이벤트 (자동화) | 함수 시그니처·사용처 → pytest 자동 생성 → 실패 자기 수정 | 완전 신규 |

**공통 원칙**: LLM = 판단·생성, 코드 = 실행·검증·IO. Tool은 그 사이 다리.

---

## 스택 (확정)

| 항목 | 선택 | 비고 |
|---|---|---|
| LLM | Google Gemini 2.5-flash (메인) + 2.5-pro (fallback) | Claude 대비 30배 저렴. dogfooding 월 $1 이하 |
| Framework | None (framework-free) | LangGraph·LangChain·CrewAI 등 미사용. supervisor 60~150줄 직접 구현 |
| Language | Python 3.12 | Backend |
| Backend | FastAPI + uvicorn | |
| 패키지 매니저 | uv | poetry 대체 표준 |
| UI (Phase 초반) | Streamlit | 하루면 완성 |
| UI (Phase 후반) | Next.js 14 App Router + TS + Tailwind + shadcn/ui | 나중 이관 |
| DB | Postgres 16 + pgvector | Docker 로컬 (포트 5433) |
| 스케줄러 | APScheduler | cron 표현식 |
| 관찰성 | Langfuse | 실행 trace·비용 대시보드 |
| Slack | Slack Bolt (Socket Mode) | |
| 웹 검색 | Exa or Tavily (Deep research용) | |
| 배포 | Fly.io or Railway (백엔드) + Vercel (프론트 나중) | |
| 저장소 | GitHub public repo | 이력용 |

---

## 아키텍처

```
┌──────────────────────────────────────────────┐
│  진입점                                        │
│  ├── Slack Bot (Bolt Socket Mode)             │
│  ├── FastAPI (/chat, /webhook/github, ...)    │
│  ├── APScheduler (매일 07:00 큐레이션)         │
│  └── CLI (QA 초기)                             │
└─────────────────────┬────────────────────────┘
                      ▼
┌──────────────────────────────────────────────┐
│  Supervisor (framework-free · 60~150줄)       │
│  - intent classifier (Gemini function_calling)│
│  - agent registry (dict)                      │
│  - result merger                              │
└─────────────────────┬────────────────────────┘
                      ▼
   ┌──────┬──────┬──────┬────────┬──────────┐
   ▼      ▼      ▼      ▼        ▼          ▼
 [RAG] [큐레]  [DR]  [CI-트]  [QA-테스트]
   │      │      │      │        │
   └──────┴──────┴──────┴────────┘
                      ▼
              공통 Tool Layer
   (LLM 래퍼 · GitHub · git · pytest · web fetch · vector)
                      ▼
              Postgres + pgvector
```

---

## Phase 계획 (총 13주)

| Phase | 주 | 산출물 | 상태 |
|:---:|:---:|---|:---:|
| 0 | 0.5주 | 셋업 (uv, GitHub, API 키, Postgres Docker, Streamlit·Gemini hello world) | **← 여기부터** |
| 1 | 2주 | 백엔드 코어 (LLM 래퍼, supervisor, tool, trace, FastAPI 진입) | |
| 2 | 1주 | 웹 큐레이션 에이전트 (스케줄러·소스·필터·랭커·Slack 발송) | |
| 3 | 1.5주 | RAG 에이전트 (문서 크롤·청킹·임베딩·검색·재검색 판정) | |
| 4 | 1주 | Deep Research 에이전트 (planner·소스 오케스트레이션·인용·self-critique) | |
| 5 | 1주 | CI 트리아지 (GitHub webhook·로그 분석·PR 코멘트) | |
| 6 | 1주 | QA 테스트 생성 (AST·pytest runner·자기 수정 루프) | |
| 7 | 1주 | Eval harness + Langfuse 관찰성 통합 | |
| 8 | 0.5주 | 실패 모드 postmortem 5~8개 문서화 | |
| 9 | 0.5주 | React 이관 (Next.js) + Vercel·Fly.io 배포 | |
| 10 | 0.5주 | README 재작성 + demo gif + 기술 블로그 + 이력화 | |

---

## 폴더 구조 (목표)

```
agent-dev/
├── .env                     # 커밋 X
├── .gitignore
├── README.md
├── app.py                   # Streamlit UI (초기)
├── backend/
│   ├── core/
│   │   ├── llm.py           # Gemini 래퍼 (기존 이관 · 스크러빙)
│   │   ├── supervisor.py    # framework-free
│   │   ├── tool.py
│   │   ├── agent_base.py
│   │   └── trace.py
│   ├── agents/
│   │   ├── rag/
│   │   ├── curator/
│   │   ├── research/
│   │   ├── ci_triage/
│   │   └── qa_gen/
│   ├── web/
│   │   ├── app.py           # FastAPI
│   │   └── github_hook.py
│   ├── ingest/              # 크롤·청킹·임베딩
│   ├── scheduler.py
│   └── tests/
├── frontend/                # Next.js (Phase 9)
├── docker/
│   └── docker-compose.dev.yml
├── docs/
│   ├── architecture.md
│   ├── postmortems/
│   └── demo/
├── evals/
├── pyproject.toml
└── uv.lock
```

---

## Phase 0 셋업 스텝 (여기서 새 워크스페이스로 이어감)

### STEP 1 — 사전 확인
PowerShell:
```powershell
python --version   # 3.12+ 필요
git --version
docker --version   # Docker Desktop 실행 중이어야 함
```

### STEP 2 — 없는 도구 설치
```powershell
# Python 3.12 (없으면)
winget install python.python.3.12

# uv (Python 패키지 매니저 표준)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Docker Desktop (없으면)
winget install Docker.DockerDesktop
```

### STEP 3 — GitHub repo 생성
1. github.com → New repository
2. 이름: `agent-dev`
3. Public
4. `.gitignore`: Python 템플릿
5. License: MIT

### STEP 4 — 로컬 초기화
현재 `C:\agent-dev` 폴더 이미 생성됨. 진입 후:
```powershell
cd C:\agent-dev
uv init --python 3.12 --no-workspace
uv venv
.\.venv\Scripts\Activate.ps1
```

⚠️ PowerShell 실행 정책 에러 시:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### STEP 5 — 초기 의존성
```powershell
uv add fastapi uvicorn streamlit google-genai python-dotenv httpx psycopg pgvector tenacity
```

### STEP 6 — 폴더 구조
```powershell
mkdir backend, backend\core, backend\agents, backend\web, backend\ingest, backend\tests, docker, docs, docs\postmortems, evals
```

### STEP 7 — API 키 발급

#### Gemini API 키
1. https://aistudio.google.com/apikey
2. **개인 Google 계정**으로 로그인 (회사 계정 X)
3. Create API key → 새 프로젝트로

#### Slack Workspace + Bot
1. slack.com/create → 개인용 workspace (예: `agent-dev-lab`)
2. 채널 생성: `#dev-digest`, `#test`
3. https://api.slack.com/apps → Create New App → From scratch
4. OAuth & Permissions → Bot Token Scopes 추가:
   - `chat:write`, `im:write`, `im:history`, `app_mentions:read`, `channels:read`
5. Install to Workspace → **Bot Token (xoxb-...)** 복사
6. Basic Information → App-Level Tokens → Generate:
   - Scope: `connections:write` → **App Token (xapp-...)** 복사
7. Socket Mode → Enable
8. Event Subscriptions → Enable:
   - Subscribe: `app_mention`, `message.im`
9. Incoming Webhooks → Activate → Add New → 채널 선택 → **Webhook URL** 복사

#### GitHub PAT
1. https://github.com/settings/personal-access-tokens/new (fine-grained)
2. Repository access: `agent-dev` only
3. Permissions:
   - Actions: Read
   - Contents: Read/write
   - Issues: Read/write
   - Pull requests: Read/write
   - Metadata: Read
4. Generate → 토큰 복사

### STEP 8 — `.env` 파일
`C:\agent-dev\.env` 생성:
```env
# LLM
GEMINI_API_KEY=AIza...
AI_MODEL=gemini-2.5-flash
LLM_FALLBACK_MODEL=gemini-2.5-pro

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_DIGEST_CHANNEL=#dev-digest

# GitHub
GITHUB_TOKEN=github_pat_...
GITHUB_REPO=YOUR_USERNAME/agent-dev

# DB
PG_HOST=localhost
PG_PORT=5433
PG_DB=agent_dev
PG_USER=postgres
PG_PASSWORD=devpass

APP_ENV=dev
```

`.gitignore` 에 `.env` 반드시 포함.

### STEP 9 — Postgres + pgvector Docker

`docker/docker-compose.dev.yml`:
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: agent-dev-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: agent_dev
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
volumes:
  pgdata:
```

실행:
```powershell
docker compose -f docker/docker-compose.dev.yml up -d
docker exec -it agent-dev-db psql -U postgres -d agent_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### STEP 10 — Gemini Hello World

`backend/core/hello_llm.py`:
```python
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model=os.getenv("AI_MODEL", "gemini-2.5-flash"),
    contents="안녕, 한 줄로 자기소개 해줘.",
)
print(response.text)
```

실행:
```powershell
python backend/core/hello_llm.py
```

### STEP 11 — Streamlit Hello World

루트 `app.py`:
```python
import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
st.set_page_config(page_title="agent-dev", page_icon="")
st.title("agent-dev")
st.caption("Framework-free multi-agent orchestrator · Phase 0")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if query := st.chat_input("질문 입력"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Gemini..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
            )
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
```

실행:
```powershell
streamlit run app.py
```

### STEP 12 — 초기 commit
```powershell
git init
git add .
git status                       # .env 없는지 확인
git commit -m "phase 0: streamlit + gemini hello world"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/agent-dev.git
git push -u origin main
```

---

## 검증 (Phase 0 완료 조건)

- [ ] `python backend/core/hello_llm.py` → Gemini 응답 뜸
- [ ] `streamlit run app.py` → 브라우저에서 챗 가능
- [ ] `docker ps` → agent-dev-db healthy
- [ ] pgvector extension 활성화됨
- [ ] GitHub repo push 완료
- [ ] Slack Bot·Webhook URL 확보 (다음 phase 대비)
- [ ] `.env` 절대 커밋 안 됨

---

## 기존 프로젝트(C:\AI_Project) 재활용 목록

### 재활용 가능 (framework-independent)
| 기존 위치 | 새 프로젝트 위치 | 개인화 필요 |
|---|---|---|
| `ai/agents/common/llm.py` (Gemini 래퍼, MAX_RETRY=15/240s) | `backend/core/llm.py` | 새 API 키로 |
| `ai/agents/rag_chatbot/retriever.py` | `backend/agents/rag/retriever.py` | 새 DB로 |
| RAG 문서 로더 (PDF·docx·xlsx·OCR) | `backend/ingest/` | 그대로 |
| Slack Bolt 봇 스켈레톤 | `backend/web/slack.py` | 새 봇 토큰 |
| `ai/app/langfuse_client.py` | `backend/core/observability.py` | 새 계정 |
| FastAPI 진입점 | `backend/web/app.py` | 그대로 |
| Postgres + pgvector 스키마 | 새 docker-compose | 그대로 |
| Manifest·router·agent 계약 개념 | 각 에이전트에 재구현 | 개념만 재활용 |

### 재활용 불가 (LangGraph에 묶임)
- `ai/agents/supervisor/graph.py` — StateGraph 전면 재작성 (60~150줄)
- `guards.py`, `fast_path_rules.py` — LangGraph node 전제
- Checkpointer (LangGraph 것)

### 완전 신규 개발
- Framework-free supervisor
- Deep research 에이전트
- QA 테스트 생성 에이전트
- 웹 큐레이션 (스케줄러+다중 소스+개인화)
- GitHub CI 트리아지 (기존은 Jenkins·GitLab MR 대상)

### 스크러빙 필수 (이력 공개 전)
- 회사 이메일 (`sheonhui@evolvesoft.co.kr`) 제거
- GitLab 프로젝트 ID (`81979871,81979868,81979842`) 제거
- Jenkins IP (`52.79.126.78`) 제거
- 회사명 `evolvesoft` 검색·제거
- 기존 API 키·토큰 절대 재사용 X

---

## RAG 대상 문서 (Tier 1 첫 인덱싱)

1. **Anthropic Docs** (docs.anthropic.com) — Claude tool_use·MCP 등
2. **OpenAI Platform Docs** (platform.openai.com/docs) — Assistants·function calling
3. **Google Gemini API Docs** (ai.google.dev/gemini-api/docs)
4. **Model Context Protocol 스펙** (modelcontextprotocol.io)

Tier 2 (나중): LangGraph docs, arxiv agent 페이퍼(ReAct·SWE-agent·Voyager), Simon Willison 블로그, LangChain 블로그, Anthropic engineering blog, Lilian Weng 블로그.

**규모 목표**: 첫 실행 4개 문서 → 청킹 800토큰 → ~1500~2000 chunk → pgvector.

---

## 이력용 셀링 포인트 (완성 후)

- "5개 에이전트를 framework-free supervisor로 오케스트레이션 (LangGraph·CrewAI 미사용)"
- "Slack·GitHub·Cron·CLI 4중 트리거 대응"
- Metric: precision@10, RAG faithfulness, 요청당 비용, 매일 dogfood 실사용
- "MCP tool 서버로 tool 계층화" (Phase 5+)
- 실패 모드 5~8종 postmortem 문서화
- Live demo URL (Streamlit → Vercel)
- 기술 블로그 1편 (postmortem 심화)

---

## UI 진화

| 시점 | UI |
|---|---|
| Phase 0 | Streamlit (하루 완성, 챗 하나) |
| Phase 2~6 | Streamlit 확장 (다이제스트·리포트·trace 뷰어) |
| Phase 9 | Next.js 14 이관 (진짜 프로덕트 룩, Vercel 배포, 이력용 라이브 링크) |

**필요 페이지 (Next.js 이관 시)**:
- `/` 랜딩 (metric·demo gif·GitHub 링크)
- `/chat` 챗봇 (SSE streaming)
- `/digest` 최근 다이제스트
- `/reports/[id]` Deep research 리포트
- `/trace/[id]` Tool loop trace 시각화 (**이력 킬러**)
- `/metrics` 대시보드

---

## 결정 노드 (진행 중 각 phase에서 확정)

| Phase | 결정 |
|:---:|---|
| 0 | 관심 토픽 = "AI 에이전트 개발" 큰 카테고리 하나로 시작 |
| 1 | intent classifier: Gemini function_calling |
| 2 | Slack 발송 채널: `#dev-digest` |
| 3 | 임베딩 모델: Gemini text-embedding-004 or Cohere free |
| 4 | 웹 검색 API: Exa (권장) or Tavily |
| 5 | 로컬 webhook 수신: smee.io or ngrok |
| 6 | QA 자기 수정 상한: 3회 |
| 7 | Langfuse: self-host or cloud 무료 |

---

## 지금 상태

- [x] 폴더 `C:\agent-dev` 생성됨 (빈 상태)
- [x] 계획 확정 (이 README)
- [ ] Phase 0 STEP 1부터 실행 필요

## 다음 액션

새 워크스페이스(`C:\agent-dev`)에서 Claude Code 열고 이 README 참조하며 STEP 1부터 순서대로 진행.

첫 명령:
```powershell
cd C:\agent-dev
python --version
git --version
docker --version
```

셋 다 OK 나오면 STEP 2 스킵하고 STEP 3부터. 안 나오면 STEP 2 설치.
