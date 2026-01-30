# 아키텍처 문서: 3-Service 분리

## 📊 현재 구조 (Before)

```
┌─────────────────────────────────────────┐
│         Railway Container (단일)         │
│                                         │
│  ┌──────────────┐                       │
│  │  Next.js     │                       │
│  │  (Port 3000) │                       │
│  └──────┬───────┘                       │
│         │                               │
│         │ spawn('python3', main.py)     │
│         ▼                               │
│  ┌──────────────┐                       │
│  │ Python       │                       │
│  │ CrewAI 실행   │                       │
│  │              │                       │
│  │ - status.json 파일 쓰기                │
│  │ - MongoDB에 업로드                     │
│  └──────────────┘                       │
│                                         │
│  문제점:                                  │
│  - Next.js와 Python이 같은 컨테이너          │
│  - 리소스 경쟁 (CPU/메모리)                  │
│  - 확장 불가능 (둘 다 함께 스케일)             │
│  - 장애 격리 불가 (하나 죽으면 전체)           │
└─────────────────────────────────────────┘
```

### 현재 흐름:
1. 사용자가 "Generate" 클릭
2. Next.js `/api/generate` → `spawn('python3', main.py)` 실행
3. Python이 백그라운드에서 CrewAI 실행
4. Python이 `status.json` 파일에 진행상황 기록
5. Next.js가 `/api/status`로 폴링 (2초마다)
6. 완료되면 `/api/article`로 MongoDB에서 파일 가져옴

---

## 🎯 목표 구조 (After)

### 시스템 아키텍처

```mermaid
graph TB
    Web[Web<br/>Next.js] -->|HTTP| API[API<br/>FastAPI]
    API -->|RPUSH| Redis[(Redis<br/>Queue + Status)]
    Redis -->|BLPOP| Worker[Worker<br/>Python]
    Worker -->|Execute| CrewAI[CrewAI]
    Worker -->|Save| MongoDB[(MongoDB<br/>Article + Vocabulary)]
    
    API -.->|SET/GET| Redis
    Worker -.->|SET| Redis
    
    API -.->|utils/llm.py<br/>utils/prompts.py| OpenAI
    
    Web -->|HTTP<br/>Proxy| API
    API -->|Save/Query| MongoDB
    
    style Web fill:#2196F3
    style API fill:#2196F3
    style Worker fill:#2196F3
    style CrewAI fill:#10a37f
    style Redis fill:#dc382d
    style MongoDB fill:#13aa52
    style OpenAI fill:#10a37f
    
    linkStyle 0 stroke:#4a90e2,stroke-width:2px,color:#4a90e2
    linkStyle 1 stroke:#4a90e2,stroke-width:2px,color:#4a90e2
    linkStyle 2 stroke:#4a90e2,stroke-width:2px,color:#4a90e2
    linkStyle 5 stroke:#ff9500,stroke-width:2px,color:#ff9500
    linkStyle 6 stroke:#13aa52,stroke-width:2px,color:#13aa52
    linkStyle 7 stroke:#9c27b0,stroke-width:2px,color:#9c27b0
    linkStyle 8 stroke:#9c27b0,stroke-width:2px,color:#9c27b0
```

### Article Generation 흐름

```mermaid
sequenceDiagram
    participant Web
    participant API
    participant Redis
    participant Worker
    participant CrewAI
    participant MongoDB
    
    Web->>API: POST /articles/generate
    API->>MongoDB: Check duplicates
    API->>MongoDB: Save article metadata
    API->>Redis: RPUSH job
    API-->>Web: Return job_id + article_id
    
    Worker->>Redis: BLPOP
    Redis-->>Worker: job_data
    
    Worker->>CrewAI: Execute crew.kickoff()
    CrewAI-->>Worker: Return article
    
    Worker->>MongoDB: Save article content
    Worker->>Redis: Update status (completed)
```

**특징:**
- **실시간 응답**: 사용자가 단어를 클릭하면 즉시 정의 반환 (비동기 큐 사용 안 함)
- **프록시 패턴**: Next.js API route가 FastAPI로 요청을 프록시
- **공통 유틸 사용**: `utils/llm.py`와 `utils/prompts.py`로 재사용 가능한 구조
- **에러 처리**: `get_llm_error_response()`로 일관된 에러 응답

### 서비스 간 통신

| From | To | Method | Purpose |
|------|-----|--------|---------|
| **Web** | **API** | HTTP | Article 생성, Job enqueue, Token usage 조회 |
| **Web** | **Next.js API** | HTTP | Dictionary API 요청 (프록시), Vocabulary CRUD 요청 (프록시), Dictionary Stats 요청 (프록시) |
| **Next.js API** | **API** | HTTP | Dictionary API 프록시 요청, Vocabulary CRUD 프록시 요청, Dictionary Stats 프록시 요청 |
| **API** | **MongoDB** | (via utils.mongodb) | 중복 체크, Article metadata 저장/조회, Vocabulary 저장/조회, Token usage 저장/조회 |
| **API** | **Redis** | `RPUSH` | Job을 큐에 추가 |
| **API** | **Redis** | `SET/GET` | Job 상태 저장/조회 (공통 모듈 `api.job_queue` 사용) |
| **API** | **LLM** | HTTP (via utils.llm) | Dictionary API용 LLM 호출 (lemma, definition, related_words) + Token tracking |
| **API** | **API** | Internal | Token usage endpoints (`/usage/me`, `/usage/articles/{id}`) |
| **Worker** | **Redis** | `BLPOP` | Job을 큐에서 꺼냄 (blocking) |
| **Worker** | **Redis** | `SET` | Job 상태 업데이트 (공통 모듈 `api.job_queue` 사용) |
| **Worker** | **CrewAI** | Function Call | Article 생성 |
| **Worker** | **MongoDB** | (via utils.mongodb) | Article content 저장, Token usage 저장 |

**참고**: API와 Worker 모두 `api.job_queue` 모듈을 통해 Redis에 접근합니다. MongoDB 접근은 `utils.mongodb` 모듈을 통해 합니다.

### Redis 데이터 구조

#### 1. Job Queue (List) - `opad:jobs`

**용도**: Worker가 처리할 job들을 FIFO 순서로 저장

```
Queue: opad:jobs (List)
┌─────────────────────────────────┐
│ [oldest] ← ... ← [newest]       │
│    ↑                    ↑       │
│  BLPOP              RPUSH       │
│ (Worker)             (API)      │
└─────────────────────────────────┘
```

**데이터 형식**:
```json
{
  "job_id": "uuid",
  "article_id": "uuid",
  "inputs": {
    "language": "Korean",
    "level": "B1",
    "length": "300",
    "topic": "Climate Change"
  },
  "created_at": "2025-01-08T12:34:56.789Z"
}
```

#### 2. Job Status (String) - `opad:job:{job_id}`

**용도**: 각 job의 현재 상태와 진행률 추적

**TTL**: 24시간 (자동 삭제)

**데이터 형식**:
```json
{
  "id": "job-uuid",
  "article_id": "article-uuid",
  "status": "running",
  "progress": 45,
  "message": "Adapting article...",
  "error": null,
  "created_at": "2025-01-08T12:34:56.789Z",
  "updated_at": "2025-01-08T12:35:12.345Z"
}
```

**접근 패턴**:
- **API**: 상태 초기화 (queued), 조회 (GET)
- **Worker**: 상태 업데이트 (running, completed, failed)
- **Progress Listener**: 진행률 업데이트 (0-100%) - CrewAI 이벤트 리스너를 통해 실시간 업데이트

---

## 🔑 핵심 개념

### 1. **비동기 작업 처리 (Async Job Processing)**
- **문제**: CrewAI 실행은 2-5분 걸림 → HTTP 요청이 타임아웃
- **해결**: Job Queue 패턴
  - 요청 즉시 `jobId` 반환
  - 실제 작업은 백그라운드에서 처리
  - 클라이언트는 job 상태를 폴링

### 2. **서비스 분리 (Service Separation)**
- **원칙**: "한 컨테이너 = 한 역할"
- **장점**:
  - 독립적 스케일링 (worker만 늘리면 됨)
  - 장애 격리 (worker 죽어도 web/api는 정상)
  - 배포 분리 (api만 수정해도 worker 영향 없음)

### 3. **Job Queue (Redis)**
- **역할**: 작업 요청을 큐에 넣고, worker가 순차적으로 처리
- **상태**: `queued` → `running` → `completed` / `failed`
- **장점**: 부하 분산, 재시도 가능, 우선순위 설정 가능

### 4. **데이터 저장소**

#### MongoDB: Article Storage
- **Article metadata 및 content 저장** (`articles` 컬렉션)
  - 중복 체크 (24시간 내 동일 입력 파라미터)
  - Article 조회 및 리스트

- **Vocabulary 저장** (`vocabularies` 컬렉션)
  - 단어, lemma, 정의, 문장 컨텍스트 저장
  - `related_words` 배열 포함 (분리 동사 등 복잡한 언어 구조 지원)
  - Article별로 그룹화하여 관리

- **Token Usage 추적** (`token_usage` 컬렉션)
  - LLM API 호출 시 토큰 사용량 및 비용 추적
  - 사용자별, 작업별 (dictionary_search, article_generation) 집계
  - 일별 사용량 통계 및 비용 분석
  
**Article Status** (MongoDB, 영구 저장):
- `running`: Article 생성 시 초기 상태 (처리 중)
- `completed`: Article 생성 완료
- `failed`: Article 생성 실패
- `deleted`: Article 삭제 (soft delete)

**Status Flow:**
```
생성 시: running
   ↓
완료: completed
실패: failed
```

#### Redis: Job Queue & Status
- **Queue**: `opad:jobs` (List) - Worker가 처리할 job들을 FIFO 순서로 저장
- **Status**: `opad:job:{job_id}` (String, 24h TTL) - Job의 실시간 상태 추적

**Job Status** (Redis, 24시간 TTL):
- `queued`: Job이 큐에 추가됨 (Worker가 아직 처리하지 않음)
- `running`: Worker가 Job을 처리 중
- `completed`: Job 처리 완료
- `failed`: Job 처리 실패

**Status Flow:**
```
queued → running → completed / failed
```

**Article Status vs Job Status:**
- **Article Status (MongoDB)**: Article의 최종 상태 (영구 저장)
- **Job Status (Redis)**: Job 처리의 실시간 상태 (24시간 후 자동 삭제)
- Article은 `running` 상태로 생성되고, Job이 완료되면 `completed` 또는 `failed`로 업데이트됨

---

## 💰 Token Usage Tracking

### Overview
The system tracks LLM API token usage and costs for all API calls, enabling cost monitoring, user billing, and usage analytics.

### Architecture

#### 1. LLM Utility Module (`utils/llm.py`)
Provider-agnostic LLM API calls using LiteLLM with automatic token tracking.

**Functions**:
- `call_llm_with_tracking()`: Makes LLM API calls and returns content + token statistics
- `parse_json_from_content()`: Parses JSON from LLM responses (handles markdown code blocks)
- `get_llm_error_response()`: Converts LLM exceptions to HTTP status codes

**TokenUsageStats Dataclass**:
```python
@dataclass
class TokenUsageStats:
    model: str              # Model name (e.g., "gpt-4.1-mini")
    prompt_tokens: int      # Input tokens
    completion_tokens: int  # Output tokens
    total_tokens: int       # Total tokens used
    estimated_cost: float   # Cost in USD (calculated by LiteLLM)
    provider: str | None    # Provider name (openai, anthropic, google)
```

**Supported Providers** (via LiteLLM):
- OpenAI: `"gpt-4.1-mini"`, `"gpt-4.1"`
- Anthropic: `"anthropic/claude-4.5-sonnet"`
- Google: `"gemini/gemini-2.0-flash"`

**Example Usage**:
```python
from utils.llm import call_llm_with_tracking, TokenUsageStats

content, stats = await call_llm_with_tracking(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4.1-mini",
    max_tokens=200
)

# stats.model = "gpt-4.1-mini"
# stats.prompt_tokens = 8
# stats.completion_tokens = 12
# stats.estimated_cost = 0.000015
```

#### 2. MongoDB Storage (`utils/mongodb.py`)

**save_token_usage()**: Save token usage record
```python
def save_token_usage(
    user_id: str,
    operation: str,  # "dictionary_search" | "article_generation"
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
    article_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Optional[str]:
    """Save token usage record to MongoDB."""
```

**get_user_token_summary()**: Get user's token usage summary
```python
def get_user_token_summary(user_id: str, days: int = 30) -> dict:
    """
    Returns:
    {
        'total_tokens': int,
        'total_cost': float,
        'by_operation': {
            'operation_type': {'tokens': int, 'cost': float, 'count': int}
        },
        'daily_usage': [
            {'date': 'YYYY-MM-DD', 'tokens': int, 'cost': float}
        ]
    }
    """
```

**get_article_token_usage()**: Get token usage for specific article
```python
def get_article_token_usage(article_id: str) -> list[dict]:
    """Returns all token usage records for an article."""
```

#### 3. Token Usage Collection Schema (MongoDB)

```json
{
  "_id": "uuid",
  "user_id": "uuid",
  "operation": "dictionary_search | article_generation",
  "model": "string",
  "prompt_tokens": 100,
  "completion_tokens": 50,
  "total_tokens": 150,
  "estimated_cost": 0.00025,
  "article_id": "uuid (optional)",
  "metadata": {
    "query": "...",
    "language": "..."
  },
  "created_at": "datetime"
}
```

**Indexes**:
- `(user_id, created_at)`: User usage queries (descending)
- `article_id`: Article-specific queries (sparse)
- `created_at`: Time-based queries (descending)
- `(operation, created_at)`: Operation-type queries

### Integration

#### Dictionary API (`src/api/routes/dictionary.py`)

```python
@router.post("/search", response_model=SearchResponse)
async def search_word(request: SearchRequest, current_user: User = Depends(get_current_user_required)):
    # Build prompt
    prompt = build_word_definition_prompt(
        language=request.language,
        sentence=request.sentence,
        word=request.word
    )

    # Call LLM with tracking
    content, stats = await call_llm_with_tracking(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4.1-mini",
        max_tokens=200
    )

    # Log token usage
    logger.info("Token usage for dictionary search", extra=stats.to_dict())

    # Save to database (Phase 2)
    save_token_usage(
        user_id=current_user.id,
        operation="dictionary_search",
        model=stats.model,
        prompt_tokens=stats.prompt_tokens,
        completion_tokens=stats.completion_tokens,
        estimated_cost=stats.estimated_cost,
        metadata={"query": request.word, "language": request.language}
    )

    # Parse and return response
    result = parse_json_from_content(content)
    return SearchResponse(**result)
```

#### Token Usage API Endpoints (`src/api/routes/usage.py`)

**GET /usage/me**: Get current user's token usage summary
```python
@router.get("/me", response_model=TokenUsageSummary)
async def get_my_usage(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user_required)
):
    # Get aggregated summary from MongoDB
    summary = get_user_token_summary(user_id=current_user.id, days=days)

    # Convert to response models
    by_operation = {
        op_name: OperationUsage(**op_data)
        for op_name, op_data in summary.get('by_operation', {}).items()
    }
    daily_usage = [
        DailyUsage(**day) for day in summary.get('daily_usage', [])
    ]

    return TokenUsageSummary(
        total_tokens=summary.get('total_tokens', 0),
        total_cost=summary.get('total_cost', 0.0),
        by_operation=by_operation,
        daily_usage=daily_usage
    )
```

**GET /usage/articles/{article_id}**: Get token usage for specific article
```python
@router.get("/articles/{article_id}", response_model=list[TokenUsageRecord])
async def get_article_usage(
    article_id: str,
    current_user: User = Depends(get_current_user_required)
):
    # Verify article ownership
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission")

    # Get all usage records for article
    usage_records = get_article_token_usage(article_id)

    return [TokenUsageRecord(**record) for record in usage_records]
```

### Token Usage Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant WebUI as Web UI
    participant API as FastAPI
    participant Redis
    participant Worker
    participant CrewAI
    participant LiteLLM
    participant MongoDB
    participant LLM as LLM Provider

    Note over User,LLM: Dictionary Search with Token Tracking
    User->>WebUI: Click word
    WebUI->>API: POST /dictionary/search
    API->>LLM: Call LLM API (via utils/llm.py)
    LLM-->>API: Response + usage stats
    API->>MongoDB: save_token_usage()
    API-->>WebUI: Definition response

    Note over User,MongoDB: Article Generation with Token Tracking
    User->>WebUI: Generate article
    WebUI->>API: POST /articles/generate
    API->>Redis: Enqueue job
    Redis-->>Worker: Dequeue job
    Worker->>Worker: Set litellm.callbacks = [ArticleGenerationTokenTracker]
    Worker->>CrewAI: run_crew()
    CrewAI->>LiteLLM: LLM API calls
    LiteLLM->>LLM: Multiple API calls
    LLM-->>LiteLLM: Responses
    LiteLLM->>Worker: Callback: log_success_event()
    Worker->>MongoDB: save_token_usage() (per LLM call)
    CrewAI-->>Worker: Article result
    Worker->>MongoDB: Save article
    Worker->>Worker: litellm.callbacks = [] (cleanup)

    Note over User,MongoDB: Usage Summary Retrieval
    User->>WebUI: View usage page
    WebUI->>API: GET /usage/me?days=30
    API->>MongoDB: get_user_token_summary()
    MongoDB-->>API: Aggregated summary
    API-->>WebUI: TokenUsageSummary
    WebUI-->>User: Display usage charts

    Note over User,MongoDB: Article Usage Details
    User->>WebUI: View article usage
    WebUI->>API: GET /usage/articles/{id}
    API->>MongoDB: get_article_token_usage()
    MongoDB-->>API: Usage records (all LLM calls)
    API-->>WebUI: List of TokenUsageRecord
    WebUI-->>User: Display usage details
```

### Future Enhancements

**Phase 1** (Completed):
- ✅ LiteLLM integration with token tracking
- ✅ TokenUsageStats dataclass
- ✅ MongoDB storage functions
- ✅ Dictionary API integration with logging

**Phase 2** (Completed):
- ✅ Database storage of token usage records
- ✅ User token summary endpoint
- ✅ Article token usage tracking

**Phase 3** (Completed):
- ✅ API endpoints for token usage (`/usage/me`, `/usage/articles/{id}`)
- ✅ Authentication and authorization for usage endpoints
- ✅ Usage summary with daily breakdown and operation filtering

**Phase 4** (Completed):
- ✅ CrewAI article generation token tracking via LiteLLM callbacks
- ✅ ArticleGenerationTokenTracker class for worker integration
- ✅ Automatic token tracking for authenticated users during article generation

**Phase 5** (Completed):
- ✅ JobTracker coordinator pattern for unified tracking
- ✅ Context manager protocol for automatic setup/cleanup
- ✅ Proper LiteLLM callback lifecycle management
- ✅ Nested context support with callback state preservation

**Phase 6** (Planned):
- Usage analytics dashboard (Frontend)
- Cost alerts and limits
- Per-user billing reports

---

## 🎯 JobTracker Architecture (Phase 5)

### Overview

JobTracker is a coordinator pattern that unifies two parallel tracking systems during article generation:
1. **JobProgressListener** - Tracks CrewAI task progress (task-level events)
2. **ArticleGenerationTokenTracker** - Tracks LLM token usage (API-level callbacks)

### Architecture Diagram

```mermaid
graph TB
    subgraph Worker["Worker Process"]
        ProcessJob[process_job]
        JobTracker[JobTracker Context Manager]

        subgraph Trackers["Tracking Components"]
            ProgressListener[JobProgressListener<br/>CrewAI Events]
            TokenTracker[ArticleGenerationTokenTracker<br/>LiteLLM Callbacks]
        end

        CrewAI[run_crew<br/>Article Generation]
    end

    subgraph Storage["Data Storage"]
        Redis[(Redis<br/>Job Status)]
        MongoDB[(MongoDB<br/>Token Usage)]
    end

    subgraph Events["Event Sources"]
        CrewAIEvents[CrewAI Event Bus<br/>Task Start/Complete]
        LiteLLMCallbacks[LiteLLM Callbacks<br/>API Success/Failure]
    end

    ProcessJob -->|with JobTracker| JobTracker
    JobTracker -->|__enter__<br/>creates| ProgressListener
    JobTracker -->|__enter__<br/>creates| TokenTracker
    JobTracker -->|runs| CrewAI

    CrewAI -->|emits events| CrewAIEvents
    CrewAI -->|makes LLM calls| LiteLLMCallbacks

    CrewAIEvents -->|triggers| ProgressListener
    LiteLLMCallbacks -->|triggers| TokenTracker

    ProgressListener -->|update_job_status| Redis
    TokenTracker -->|save_token_usage| MongoDB

    JobTracker -->|__exit__<br/>cleanup| ProgressListener
    JobTracker -->|__exit__<br/>restore callbacks| TokenTracker

    style JobTracker fill:#4a90e2,stroke:#2563eb,color:#fff
    style ProgressListener fill:#10a37f,stroke:#0d8a6a,color:#fff
    style TokenTracker fill:#10a37f,stroke:#0d8a6a,color:#fff
    style Redis fill:#dc382d,stroke:#a12822,color:#fff
    style MongoDB fill:#13aa52,stroke:#0f8a43,color:#fff
```

### Context Manager Lifecycle

```python
# Worker code
with crewai_event_bus.scoped_handlers():
    with JobTracker(job_id, user_id, article_id) as tracker:
        # 1. __enter__() runs automatically
        #    - Creates JobProgressListener
        #    - Creates ArticleGenerationTokenTracker (if user_id)
        #    - Saves litellm.callbacks to _original_callbacks
        #    - Sets litellm.callbacks = [token_tracker]

        result = run_crew(inputs)

        # 2. During execution
        #    - CrewAI emits task events → JobProgressListener → Redis
        #    - CrewAI makes LLM calls → LiteLLM → TokenTracker → MongoDB

        # 3. Check for failures
        if tracker.listener.task_failed:
            return False

    # 4. __exit__() runs automatically (even on exception)
    #    - Restores litellm.callbacks = _original_callbacks
    #    - Prevents callback leakage between jobs
```

### Key Design Decisions

**Why Context Manager?**
- Automatic setup and cleanup (no manual litellm.callbacks management)
- Exception-safe (cleanup always runs via `__exit__`)
- Pythonic and readable (`with` statement)

**Why Save/Restore Callbacks Instead of Clearing?**
- Supports nested JobTracker contexts (future-proof)
- Prevents accidentally clearing callbacks from outer scope
- More defensive for long-running worker processes

**Why Two Separate Trackers?**
- Different abstraction levels (task-level vs API-level)
- Different storage backends (Redis vs MongoDB)
- Different lifetimes (ephemeral vs permanent)
- Independent failure modes (one can fail without affecting other)

**Why Coordinate Them?**
- Shared lifecycle (both track same job)
- Shared context (job_id, user_id, article_id)
- Single entry point for worker code
- Consistent error handling

### Data Flow Comparison

| Aspect | JobProgressListener | ArticleGenerationTokenTracker |
|--------|---------------------|-------------------------------|
| **Trigger** | CrewAI task events | LLM API calls |
| **Frequency** | ~4-5 times per job | ~5-10 times per job |
| **Granularity** | Coarse (task start/end) | Fine (per API call) |
| **Data** | Task name, progress % | Model, tokens, cost |
| **Storage** | Redis (job status) | MongoDB (usage records) |
| **TTL** | 24 hours (auto-expire) | Permanent |
| **Consumer** | Frontend polling | Analytics/billing |

### Error Handling

**Non-Fatal Tracking**:
- Both trackers catch all exceptions internally
- Failures logged as warnings but never crash worker
- Article generation continues even if tracking fails
- Rationale: Tracking is observability, not critical path

**Cleanup Guarantees**:
```python
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    """Always runs, even on exception."""
    if self.token_tracker is not None:
        litellm.callbacks = self._original_callbacks  # Always restore
```

### Testing Considerations

**Unit Tests Should Cover**:
- `JobTracker.__enter__()` creates both trackers
- `JobTracker.__exit__()` restores callbacks
- Anonymous users skip token tracking
- Callback state preserved across nested contexts
- Cleanup runs even on exceptions

**Integration Tests Should Cover**:
- Full article generation with both trackers active
- Progress updates appear in Redis
- Token usage records appear in MongoDB
- Multiple jobs don't interfere with each other

---

## 🔧 Worker Token Tracking (Phase 4-5)

### Overview

The Worker service tracks token usage during CrewAI article generation using LiteLLM's callback system. Phase 5 introduced the **JobTracker coordinator pattern** that unifies job progress tracking and token usage tracking into a single context manager with proper lifecycle management.

### Architecture

**Data Flow:**
```
Worker → process_job() → JobTracker.__enter__() → Set litellm.callbacks → run_crew() → CrewAI agents
                                ↓                                                            ↓
                    JobProgressListener (task events)                            Multiple LLM calls
                    ArticleGenerationTokenTracker (token tracking)                         ↓
                                                                            LiteLLM intercepts each call
                                                                                        ↓
                                                            ArticleGenerationTokenTracker.log_success_event()
                                                                                        ↓
                                                                            save_token_usage() → MongoDB
                                                                                        ↓
                                                                    JobTracker.__exit__() → Cleanup
```

### JobTracker Coordinator (Phase 5)

**File**: `src/worker/job_tracker.py`

**Purpose**: Unified coordinator that manages both job progress tracking (CrewAI events) and token usage tracking (LiteLLM callbacks) with proper lifecycle management.

**Architecture**:
```python
class JobTracker:
    """Coordinator for job progress and token tracking during article generation.

    Unifies:
    1. JobProgressListener - Real-time task progress updates via CrewAI events
    2. ArticleGenerationTokenTracker - LLM token usage tracking via LiteLLM callbacks
    """
```

**Key Features**:
- **Context Manager Protocol**: Automatic setup (`__enter__`) and cleanup (`__exit__`)
- **Callback Lifecycle Management**: Saves and restores LiteLLM callbacks for nested contexts
- **Conditional Tracking**: Only tracks tokens for authenticated users (user_id exists)
- **Memory Leak Prevention**: Always clears callbacks in `__exit__`, even on exceptions

**Usage Pattern** (`src/worker/processor.py`):

```python
def process_job(job_data: dict) -> bool:
    ctx = JobContext.from_dict(job_data)

    try:
        from crewai.events.event_bus import crewai_event_bus

        with crewai_event_bus.scoped_handlers():
            with JobTracker(ctx.job_id, ctx.user_id, ctx.article_id) as tracker:
                # Fetch vocabulary for personalized generation
                if ctx.user_id and ctx.inputs.get('language'):
                    vocab = get_user_vocabulary_for_generation(ctx.user_id, ctx.inputs['language'], 50)
                    if vocab:
                        ctx.inputs['vocabulary_list'] = vocab

                # Execute CrewAI (all LLM calls automatically tracked)
                result = run_crew(inputs=ctx.inputs)

                # Check for task failures
                if tracker.listener.task_failed:
                    logger.warning("Task failed during execution")
                    if ctx.article_id:
                        update_article_status(ctx.article_id, 'failed')
                    return False

        # Save to MongoDB
        save_article(ctx.article_id, result.raw, ctx.started_at)
        ctx.update_status('completed', 100, 'Article generated successfully!')
        return True

    except Exception as e:
        logger.error(f"Job failed: {e}")
        ctx.mark_failed(translate_error(e), f"{type(e).__name__}: {str(e)[:200]}")
        return False
```

**Lifecycle**:

1. **`__enter__()`** (lines 80-121):
   - Creates `JobProgressListener` for CrewAI task progress events
   - Creates `ArticleGenerationTokenTracker` for token tracking (if user_id exists)
   - Saves original `litellm.callbacks` to `_original_callbacks`
   - Sets `litellm.callbacks = [tracker]` to enable token tracking
   - Returns self for use in context manager

2. **`__exit__()`** (lines 123-150):
   - Restores original `litellm.callbacks` from `_original_callbacks`
   - Prevents callback interference between jobs
   - Always executes, even on exceptions (cleanup guaranteed)

**Benefits**:
- **Single Responsibility**: Each tracker handles one concern (progress vs tokens)
- **Proper Cleanup**: Context manager ensures callbacks never leak between jobs
- **Nested Context Support**: Saves/restores callbacks for nested JobTracker usage
- **Fail-Safe**: Cleanup happens even on exceptions

### ArticleGenerationTokenTracker Class

**File**: `src/worker/token_tracker.py`

**Purpose**: LiteLLM callback handler that intercepts all LLM API calls during article generation and records token usage to MongoDB.

**Key Methods**:

1. `log_success_event(kwargs, response_obj, start_time, end_time)` (lines 67-157)
   - Called by LiteLLM after each successful LLM API call
   - Extracts model name, prompt_tokens, completion_tokens from response
   - Calculates estimated cost using `litellm.completion_cost()`
   - Saves token usage to MongoDB via `save_token_usage()`
   - Never crashes worker on tracking failures (catch-all exception handler)

2. `log_failure_event(kwargs, response_obj, start_time, end_time)` (lines 179-216)
   - Called when LLM API call fails
   - Logs failure for observability (does not save to MongoDB)
   - Truncates error messages to 200 chars to prevent log bloat

**Integration**: Now managed by `JobTracker` coordinator (see above)

### How LiteLLM Callbacks Work

**LiteLLM Integration**:
- LiteLLM provides a `CustomLogger` base class for callback handlers
- When `litellm.callbacks = [tracker]` is set, all LLM API calls are intercepted
- CrewAI agents use LiteLLM internally, so all agent LLM calls are tracked
- Callbacks are invoked automatically:
  - `log_success_event()` on successful API call
  - `log_failure_event()` on failed API call

**Per-Call Tracking**:
- Each LLM API call during article generation generates a separate token usage record
- An article generation may involve 5-10 LLM calls (research, writing, editing, etc.)
- Total article cost = sum of all individual call costs
- All records share the same `article_id` for aggregation

**Callback Lifecycle with JobTracker**:
```
1. Worker starts job
2. JobTracker.__enter__():
   - Save original callbacks: _original_callbacks = litellm.callbacks.copy()
   - Register new callback: litellm.callbacks = [tracker]
3. CrewAI agent 1 makes LLM call → tracker.log_success_event() → save to MongoDB
4. CrewAI agent 2 makes LLM call → tracker.log_success_event() → save to MongoDB
5. ... (multiple calls)
6. CrewAI completes
7. JobTracker.__exit__():
   - Restore callbacks: litellm.callbacks = _original_callbacks
   - Prevents interference with next job or nested JobTracker
```

**Why Save/Restore Callbacks?**
- Supports nested JobTracker contexts (if needed in future)
- Prevents accidentally clearing callbacks set by outer scope
- More robust than simply setting to empty list
- Defensive programming for long-running worker processes

### Token Usage Record Structure

**Saved to MongoDB** (via `save_token_usage()`):
```json
{
  "_id": "usage-uuid",
  "user_id": "user-uuid",
  "operation": "article_generation",
  "model": "gpt-4.1-mini",
  "prompt_tokens": 2000,
  "completion_tokens": 1500,
  "total_tokens": 3500,
  "estimated_cost": 0.0525,
  "article_id": "article-uuid",
  "metadata": {
    "job_id": "job-uuid"
  },
  "created_at": "2026-01-30T10:00:00Z"
}
```

**Multiple Records Per Article**:
- Each LLM call during generation creates a separate record
- Aggregation query sums all records with same `article_id`
- Example: Research agent (500 tokens) + Writing agent (3000 tokens) + Editing agent (800 tokens) = 4300 total tokens

### Error Handling

**Non-Fatal Failures**:
- Token tracking failures never crash the worker
- All exceptions caught and logged as warnings
- Article generation continues even if tracking fails
- Rationale: Tracking is observability, not critical functionality

**Cost Calculation Fallback**:
- If `litellm.completion_cost()` fails, cost is set to 0.0
- Tokens are still tracked (tokens always available in response)
- Allows cost calculation to be updated retroactively from token counts

### Anonymous User Handling

**Conditional Tracking** (`src/worker/processor.py:54-63`):
```python
if ctx.user_id:
    token_tracker = ArticleGenerationTokenTracker(...)
    litellm.callbacks = [token_tracker]
```

- Only tracks for authenticated users (user_id exists)
- Anonymous users (no user_id) skip token tracking entirely
- Prevents null user_id records in MongoDB
- Aligns with dictionary API behavior (requires authentication)

### Security Considerations

**User ID Validation**:
- `user_id` passed from job queue (validated during job creation in API)
- Worker trusts job queue data (internal system boundary)
- No additional validation needed in worker

**Memory Leaks Prevention**:
- `finally` block always clears `litellm.callbacks = []`
- Prevents callbacks from affecting subsequent jobs
- Critical in long-running worker processes

### Testing

**Test File**: `src/worker/tests/test_token_tracker.py`

**Coverage**:
- Callback registration and cleanup
- Successful LLM call tracking
- Failed LLM call handling
- Cost calculation fallback
- MongoDB save failures (non-fatal)

### Retrieval API

**Get Article Usage**:
```python
# API endpoint: GET /usage/articles/{article_id}
records = get_article_token_usage(article_id)
total_cost = sum(r['estimated_cost'] for r in records)
```

**Returns**:
- All token usage records for article (multiple LLM calls)
- Sorted by `created_at` ascending (chronological order)
- Includes metadata with `job_id` for traceability

---

## 📚 Vocabulary-Aware Article Generation

### Overview
The system now supports vocabulary-aware article generation, where CrewAI adjusts content difficulty based on words the user has already learned.

### Vocabulary Features

#### 1. Dictionary API - Word Definition
- **POST /dictionary/search**: Get word definition and lemma using OpenAI API
- **Returns**: lemma, definition, and related_words (for complex structures like separable verbs)
- **Auth**: Required (JWT) to prevent API abuse

#### 2. Vocabulary Storage
- **POST /dictionary/vocabulary**: Add a word to user's vocabulary
- **GET /dictionary/vocabularies**: Get aggregated vocabulary grouped by lemma with counts
- **DELETE /dictionary/vocabularies/{id}**: Delete a vocabulary word
- **Auth**: All vocabulary operations require authentication and are user-specific

#### 3. Article-Specific Vocabularies
- **GET /articles/{article_id}/vocabularies**: Get all vocabularies for a specific article
- **Response**: List of VocabularyResponse objects with word, lemma, definition, context, and metadata
- **Auth**: Users can only access vocabularies from their own articles

### Data Model

#### Vocabulary Collection (MongoDB)
```json
{
  "_id": "ObjectId",
  "article_id": "uuid",
  "user_id": "uuid",
  "word": "string",              // Original word clicked
  "lemma": "string",             // Dictionary form
  "definition": "string",        // Word definition
  "sentence": "string",          // Sentence context
  "language": "string",
  "related_words": ["string"],   // All forms in sentence (e.g., verbs with particles)
  "span_id": "string",           // Span ID from markdown for linking
  "created_at": "datetime",
  "pos": "string",               // Part of speech (noun, verb, adjective, etc.)
  "gender": "string",            // Grammatical gender (der/die/das for German, le/la for French, etc.)
  "conjugations": {              // Verb conjugations (null for non-verbs)
    "present": "string",
    "past": "string",
    "perfect": "string"
  },
  "level": "string"              // CEFR level (A1, A2, B1, B2, C1, C2)
}
```

**New Grammatical Metadata Fields:**
- `pos`: Part of speech classification (noun, verb, adjective, adverb, preposition, etc.)
- `gender`: Grammatical gender for nouns in gendered languages (German: der/die/das, French: le/la, Spanish: el/la). Null for non-gendered languages.
- `conjugations`: Verb conjugation forms across tenses (present, past, perfect). Null for non-verbs.
- `level`: CEFR difficulty level (A1-C2) for vocabulary tracking and adaptive learning.

#### VocabularyCount Model (Aggregated Response)
- Groups vocabularies by lemma
- Returns count of how many times a lemma appears across articles
- Includes most recent definition and example sentence
- Lists all article_ids where lemma appears
- Includes grammatical metadata (pos, gender, conjugations, level) from most recent entry

#### API Model Enhancements

**Conjugations.__bool__()** (`src/api/models.py:18-20`):
- Enables truthiness checking: `if conjugations:` returns False when all fields (present, past, perfect) are None
- Simplifies validation logic by treating empty Conjugations as falsy
- Backend can check conjugation presence without explicit null checks

**VocabularyRequest.field_validator** (`src/api/models.py:106-116`):
- Automatic conversion from Conjugations model to dict before database storage
- Returns None if conjugations object is empty (using `__bool__` check)
- Handles both dict and Conjugations input types
- Prevents storing empty conjugation objects in MongoDB

### Vocabulary-Aware Generation Flow
1. User saves vocabulary words from articles (POST /dictionary/vocabulary)
2. Words stored with article context (sentence, span_id)
3. When generating new article, worker retrieves user's vocabulary list
4. CrewAI receives vocabulary list as constraint for content difficulty
5. Generated article uses different words/complexity for learned vocabulary
6. User can access article-specific vocabularies (GET /articles/{id}/vocabularies)

### Authentication
All vocabulary endpoints require JWT authentication. Users can only:
- Add/delete their own vocabulary
- View their own vocabulary lists
- Access vocabularies from their own articles

---

## 📁 디렉토리 구조

```
opad/
├── src/
│   ├── api/              # API 서비스 (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py       # FastAPI 앱 진입점
│   │   ├── models.py     # Pydantic 모델 (Article, Job)
│   │   ├── routes/       # API 엔드포인트
│   │   │   ├── articles.py
│   │   │   ├── jobs.py
│   │   │   ├── health.py
│   │   │   ├── endpoints.py
│   │   │   ├── stats.py
│   │   │   └── dictionary.py  # Dictionary API (word definition)
│   │   └── job_queue.py  # Redis 큐 관리
│   │
│   ├── worker/           # Worker 서비스 (Python)
│   │   ├── __init__.py
│   │   ├── main.py       # Worker 진입점
│   │   ├── processor.py  # Job 처리 로직
│   │   ├── job_tracker.py      # JobTracker coordinator (Phase 5)
│   │   ├── token_tracker.py    # ArticleGenerationTokenTracker
│   │   └── context.py    # JobContext helper
│   │
│   ├── web/              # Web 서비스 (Next.js)
│   │   ├── app/          # Next.js App Router
│   │   │   ├── api/      # API Routes (프록시)
│   │   │   ├── articles/ # Article pages
│   │   │   ├── vocabulary/ # Vocabulary pages
│   │   │   └── page.tsx  # 메인 페이지
│   │   ├── components/   # React 컴포넌트
│   │   │   ├── ArticleCard.tsx
│   │   │   ├── EmptyState.tsx      # Reusable empty state
│   │   │   ├── ErrorAlert.tsx      # Reusable error alert
│   │   │   ├── MarkdownViewer.tsx
│   │   │   └── VocabularyList.tsx
│   │   ├── hooks/        # Custom React hooks
│   │   │   ├── useAsyncFetch.ts    # Generic fetch with loading/error
│   │   │   ├── usePagination.ts    # Pagination calculations
│   │   │   ├── useStatusPolling.ts # Job status polling
│   │   │   └── useVocabularyDelete.ts # Vocabulary deletion
│   │   ├── lib/          # Frontend utilities
│   │   │   ├── api.ts           # fetchWithAuth, parseErrorResponse
│   │   │   ├── auth.ts          # Auth utilities
│   │   │   ├── formatters.ts    # Date formatting utilities
│   │   │   └── styleHelpers.ts  # CEFR color/label helpers
│   │   ├── types/        # TypeScript type definitions
│   │   ├── tailwind.config.ts # Tailwind config with safelist
│   │   └── package.json
│   │
│   ├── opad/             # CrewAI 로직 (공유)
│   │   ├── crew.py
│   │   └── main.py
│   │
│   └── utils/            # 공통 유틸리티 (공유)
│       ├── mongodb.py    # MongoDB 연결 및 작업
│       ├── logging.py    # Structured logging 설정
│       ├── llm.py        # OpenAI API 공통 함수
│       └── prompts.py    # LLM 프롬프트 템플릿
│
└── Dockerfile.*          # 서비스별 Dockerfile (이슈 #9)
```

### 서비스 구분
| 폴더 | 역할 | 런타임 | 포트 |
|------|------|--------|------|
| `src/api/` | CRUD + Job enqueue + Dictionary API | Python (FastAPI) | 8001 (default) |
| `src/worker/` | CrewAI 실행 + Job/Token Tracking | Python | - |
| `src/web/` | UI | Node.js (Next.js) | 3000 |
| `src/crew/` | CrewAI 로직 (공유) | - | - |
| `src/utils/` | 공통 유틸 (공유) | - | - |

### Worker 모듈 구성 (Phase 5)
| 파일 | 역할 | 의존성 |
|------|------|--------|
| `worker/main.py` | Worker 진입점 (infinite loop) | `processor.py` |
| `worker/processor.py` | Job 처리 로직 (process_job) | `job_tracker.py`, `crew/main.py` |
| `worker/job_tracker.py` | JobTracker coordinator (context manager) | `token_tracker.py`, `crew/progress_listener.py` |
| `worker/token_tracker.py` | ArticleGenerationTokenTracker (LiteLLM callback) | `utils/mongodb.py` |
| `worker/context.py` | JobContext helper (job data validation) | `api/job_queue.py` |
| `crew/progress_listener.py` | JobProgressListener (CrewAI event listener) | `api/job_queue.py` |

---

## 🔑 공통 유틸리티 모듈

### LLM 유틸리티 (`utils/llm.py`)
Provider-agnostic LLM API 호출 및 토큰 추적을 위한 공통 함수들 (LiteLLM 기반):

- **`call_llm_with_tracking()`**: LLM API 호출 + 토큰 사용량 추적 (범용 함수)
  - 반환값: `(content: str, stats: TokenUsageStats)`
  - OpenAI, Anthropic, Google 등 다양한 프로바이더 지원
  - 자동 비용 계산 (LiteLLM 내장 가격 데이터베이스 사용)
- **`TokenUsageStats`**: 토큰 사용량 통계 dataclass
  - 필드: `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost`, `provider`
- **`parse_json_from_content()`**: LLM 응답에서 JSON 파싱 (다양한 형식 지원)
  - 일반 JSON, 마크다운 코드 블록 (```json), 텍스트 내 JSON 추출 지원
- **`get_llm_error_response()`**: LLM 관련 예외를 HTTP 상태 코드로 변환

**사용 예시:**
```python
from utils.llm import call_llm_with_tracking, parse_json_from_content

# LLM 호출 + 토큰 추적
content, stats = await call_llm_with_tracking(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4.1-mini",
    max_tokens=200
)

# 토큰 사용량 로깅
logger.info("Token usage", extra=stats.to_dict())

# JSON 파싱
result = parse_json_from_content(content)
```

**지원 프로바이더** (LiteLLM):
- OpenAI: `"gpt-4.1-mini"`, `"gpt-4.1"`
- Anthropic: `"anthropic/claude-4.5-sonnet"`
- Google: `"gemini/gemini-2.0-flash"`

### 프롬프트 템플릿 (`utils/prompts.py`)
재사용 가능한 LLM 프롬프트 빌더 함수들:

- **`build_word_definition_prompt()`**: Dictionary API용 프롬프트 생성 (lemma 및 definition 추출)

**사용 예시:**
```python
from utils.prompts import build_word_definition_prompt

prompt = build_word_definition_prompt(
    language="German",
    sentence="Diese große Spanne hängt von mehreren Faktoren ab.",
    word="hängt"
)
```

---

## 📡 Dynamic Endpoint Discovery

### Tag-Based Endpoint Grouping

The `/endpoints` endpoint dynamically generates an HTML page listing all registered API routes, grouped by their tags. This system requires no code changes when new routes are added—they automatically appear in the listing.

**Endpoint**: `GET /endpoints`

**File**: `src/api/routes/endpoints.py`

**How It Works**:

1. **Route Introspection**: Scans `app.routes` to collect all routes with methods and paths
2. **Tag Extraction**: Reads tags from route definitions (e.g., `tags=["articles"]`, `tags=["usage"]`)
3. **Dynamic Grouping**: Groups endpoints by tag using `group_endpoints_by_tag()`
4. **HTML Generation**: Renders grouped endpoints as styled HTML page

**Helper Functions**:

- **`group_endpoints_by_tag(endpoints)`**: Groups endpoints by tag (first tag if multiple), returns `dict[tag, list[endpoints]]`
  - Uses `defaultdict(list)` to avoid KeyError
  - Filters out `EXCLUDED_TAGS` (e.g., "meta")
  - Sorts endpoints within each group by `(path, method)`
  - Assigns "other" tag if endpoint has no tags

- **`get_sorted_tags(grouped)`**: Returns alphabetically sorted tag list with "other" at end

- **`format_endpoint(ep)`**: Formats single endpoint as HTML with method badge, path, and summary

- **`format_tag_title(tag)`**: Converts tag name to display title (e.g., "articles" → "Articles Endpoints")

**Configuration**:

```python
# src/api/routes/endpoints.py:13-14
EXCLUDED_TAGS = {"meta"}  # Tags to hide from listing
EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc"}  # Paths to skip
```

**Example Route Definition**:

```python
# src/api/routes/usage.py
router = APIRouter(tags=["usage"])  # Tag used for grouping

@router.get("/me", summary="Get current user's token usage summary")
async def get_my_usage(...):
    """Detailed description..."""
```

**Benefits**:

- **Zero-maintenance**: New routes automatically appear in listing
- **Tag-based organization**: Routes grouped by domain (articles, usage, dictionary)
- **Clean HTML output**: Color-coded HTTP methods (GET=blue, POST=green, DELETE=red)
- **No hardcoding**: Eliminates manual endpoint lists

**Usage**:
Visit `/endpoints` in browser to see all available API routes grouped by tag.

---

## 📡 Dictionary API

### Word Definition Endpoint

**Endpoint**: `POST /dictionary/search`

**목적**: 문장 컨텍스트에서 단어의 lemma, 정의 및 문법적 메타데이터를 추출

**요청:**
```json
{
  "word": "hängt",
  "sentence": "Diese große Spanne hängt von mehreren Faktoren ab.",
  "language": "German"
}
```

**응답:**
```json
{
  "lemma": "abhängen",
  "definition": "의존하다, ~에 달려있다",
  "related_words": ["hängt", "ab"],
  "pos": "verb",
  "gender": null,
  "conjugations": {
    "present": "hängt ab",
    "past": "hing ab",
    "perfect": "hat abgehangen"
  },
  "level": "B1"
}
```

**특징:**
- **분리동사 처리**: 독일어 등에서 동사가 분리된 경우 전체 lemma 반환 (예: `hängt ... ab` → `abhängen`)
- **복합어 처리**: 단어가 복합어의 일부인 경우 전체 형태 반환
- **related_words**: 문장에서 같은 lemma에 속하는 모든 단어들을 배열로 반환 (예: 분리 동사의 경우 모든 부분 포함)
- **문법적 메타데이터**: 품사(pos), 성(gender), 동사 활용형(conjugations), CEFR 레벨(level) 자동 추출
- **공통 유틸 사용**: `utils/llm.py`의 `call_openai_chat()` 함수 활용
- **프롬프트 분리**: `utils/prompts.py`의 `build_word_definition_prompt()` 사용
- **보안**: Regex injection 방지를 위한 `re.escape()` 적용

**흐름:**

```mermaid
sequenceDiagram
    participant Frontend as Frontend<br/>(MarkdownViewer)
    participant NextAPI as Next.js API<br/>(/api/dictionary/search)
    participant FastAPI as FastAPI<br/>(/dictionary/search)
    participant Utils as Utils<br/>(prompts.py + llm.py)
    participant OpenAI as OpenAI API

    Frontend->>NextAPI: POST /api/dictionary/search<br/>{word, sentence, language}
    NextAPI->>FastAPI: POST /dictionary/search<br/>{word, sentence, language}

    FastAPI->>Utils: build_word_definition_prompt()
    Utils-->>FastAPI: prompt string

    FastAPI->>Utils: call_openai_chat(prompt)
    Utils->>OpenAI: POST /v1/chat/completions
    OpenAI-->>Utils: {lemma, definition, related_words, pos, gender, conjugations, level}
    Utils->>Utils: parse_json_from_content()
    Utils-->>FastAPI: {lemma, definition, related_words, pos, gender, conjugations, level}

    FastAPI-->>NextAPI: SearchResponse<br/>{lemma, definition, related_words, pos, gender, conjugations, level}
    NextAPI-->>Frontend: {lemma, definition, related_words, pos, gender, conjugations, level}
```

---

## 🎨 Frontend Architecture

### Code Organization

The frontend follows a modular architecture with clear separation of concerns:

```
src/web/
├── app/              # Next.js App Router (pages)
├── components/       # Reusable React components
├── hooks/            # Custom React hooks
├── lib/              # Utility functions
└── types/            # TypeScript type definitions
```

### Utility Modules

#### API Client (`lib/api.ts`)
Centralized API client utilities for consistent request handling:
- `fetchWithAuth()`: Automatic JWT token injection
- `parseErrorResponse()`: Consistent error message extraction

**Benefits**:
- DRY principle: Authentication logic in one place
- Consistent error handling across all API calls
- Easy to add global request interceptors

#### Date Formatters (`lib/formatters.ts`)
Reusable date formatting functions using Intl.DateTimeFormat:
- `formatDate()`: Customizable date formatting
- `formatDateShort()`: Short date format
- `formatDateTime()`: Date with time

**Benefits**:
- Consistent date display across UI
- Locale-aware formatting
- Single source of truth for date formats

#### Style Helpers (`lib/styleHelpers.ts`)
CEFR level badge styling utilities:
- `getLevelColor()`: Tailwind classes for level badges
- `getLevelLabel()`: Human-readable level labels

**Benefits**:
- Consistent color scheme across UI
- Dynamic class generation for Tailwind
- Easy to update color scheme globally

**Important**: CEFR level colors are safelisted in `tailwind.config.ts` to prevent Tailwind's tree-shaking from removing dynamically-generated classes.

### Custom Hooks

#### useAsyncFetch
Generic hook for async data fetching with automatic state management:
- Loading state
- Error handling
- Automatic 401 redirect
- Type-safe data state

**Use Cases**:
- Fetching article lists
- Loading article details
- Any API data fetching

#### usePagination
Pagination calculations and state management:
- Current page calculation
- Total pages calculation
- Next/previous page navigation
- Skip value computation

**Use Cases**:
- Article list pagination
- Vocabulary list pagination

#### useStatusPolling
Job status polling with automatic interval management:
- Configurable polling interval
- Automatic cleanup on completion/error
- Progress state management
- Callbacks for status changes

**Use Cases**:
- Article generation progress tracking
- Any long-running job monitoring

#### useVocabularyDelete
Vocabulary deletion with error handling:
- DELETE request to API
- Detailed error messages
- Throws errors for caller to handle

**Use Cases**:
- Deleting vocabulary entries from vocabulary list

### Reusable Components

#### ErrorAlert (`src/web/components/ErrorAlert.tsx`)
Consistent error message display:
- Red background with border (`bg-red-50 border-red-200`)
- Optional retry button with hover effect
- Automatic hiding when error is null
- Accessible error messaging

**Props**:
- `error` (string | null): Error message to display
- `onRetry` (optional): Callback function for retry button
- `className` (optional): Additional CSS classes

#### EmptyState (`src/web/components/EmptyState.tsx`)
Consistent empty state display:
- Centered layout with white card background
- Optional icon (emoji or Unicode character)
- Optional action button with blue styling
- Title and description text with gray tones

**Props**:
- `title` (string): Main heading text
- `description` (string): Descriptive subtitle
- `icon` (optional): Emoji or icon character
- `action` (optional): Object with `label` and `onClick` for action button
- `className` (optional): Additional CSS classes

**Benefits**:
- Consistent UX across all pages
- Reduces code duplication
- Easy to update design globally
- Improves maintainability with single source of truth

### Refactoring Impact

**Before Refactoring**:
- Duplicate fetch logic in every page
- Inconsistent error handling
- Duplicate date formatting code
- Duplicate pagination calculations
- Duplicate empty state styling

**After Refactoring**:
- Single source of truth for common operations
- Consistent error handling with `useAsyncFetch`
- Reusable date formatters
- Reusable pagination hook
- Reusable UI components (`ErrorAlert`, `EmptyState`)

**Code Reduction**:
- Article detail page: 166 lines reduced
- Articles list page: 27 lines reduced
- Vocabulary page: 43 lines reduced
- Total: 236 lines of code removed through refactoring

### Security Improvements

#### XSS Prevention in MarkdownViewer (`src/web/components/MarkdownViewer.tsx`)

**Issue**: Previous implementation used `innerHTML` to inject vocabulary buttons, creating XSS vulnerability.

**Security Measures Implemented**:

1. **HTML Escaping** (lines 92-96):
   - `escapeHtml()` utility converts text to DOM text node then reads innerHTML
   - Prevents script injection in user-provided content (word, lemma, definition, sentence)
   - Applied to all vocabulary data before rendering

2. **DOM API Methods** (lines 663-713):
   - Replaced `innerHTML` with DOM manipulation (`createElement`, `textContent`)
   - Creates definition spans using `document.createElement()` instead of string templates
   - Uses `textContent` for user data instead of `innerHTML`
   - Parses button HTML in temporary container, then extracts element reference

3. **Event Delegation** (lines 514-534):
   - Single event listener on container instead of per-word listeners
   - Prevents stale closure issues with dynamic content
   - Ref-based callback storage (`handleWordClickRef`) avoids outdated state

4. **Data Attribute Escaping** (lines 112-131):
   - All data attributes escaped before setting: `data-word="${wordEscaped}"`
   - JSON strings escaped with `.replace(/"/g, '&quot;')` for attribute safety
   - Prevents attribute injection attacks

**Before (Vulnerable)**:
```typescript
// Direct innerHTML injection - XSS risk
defSpan.innerHTML = `<strong>${lemma}</strong>: ${meaning} <button>...</button>`
```

**After (Secure)**:
```typescript
// DOM API - XSS safe
const strong = document.createElement('strong')
strong.textContent = displayLemma
defSpan.appendChild(strong)
defSpan.appendChild(document.createTextNode(': ' + meaning))
```

**Impact**: Prevents malicious script execution from vocabulary data, protects against DOM-based XSS attacks.

#### React Component Remounting Pattern

**Purpose**: Prevent React hydration mismatches when article content changes.

**Implementation** (`src/web/app/articles/[id]/page.tsx:266`):
```typescript
<MarkdownViewer
  key={`${articleId}-${content.length}`}
  content={content}
  language={article?.language}
  articleId={articleId}
  vocabularies={vocabularies}
  onAddVocabulary={handleAddVocabulary}
/>
```

**Key Prop Strategy**:
- Pattern: `${articleId}-${content.length}`
- Forces complete component remount when content changes
- Triggers reset of `data-processed` attribute (line 456)
- Clears all previous DOM state and event listeners

**Processing State Check** (`src/web/components/MarkdownViewer.tsx:456-458`):
```typescript
// Skip if already processed (component remounts on content change via key prop)
if (containerRef.current.getAttribute('data-processed') === 'true') {
  return
}
```

**Why This Pattern**:
- Without key: React reuses DOM nodes, causing hydration mismatches
- Manual cleanup: Error-prone and complex to maintain
- useEffect on content: Risk of double-processing
- Remounting: Clean state guaranteed, simple lifecycle

**Benefits**:
- Eliminates React DOM mismatch errors
- Prevents stale event listeners
- Simplifies component update logic
- Ensures consistent behavior across content changes

### Bug Fixes

#### 1. Conjugations Type Conversion
**Issue**: Frontend expected conjugations as object, but backend returned null for non-verbs, causing type mismatches.

**Fix**: Ensure conjugations field is properly typed and handled as nullable in TypeScript types.

#### 2. Tailwind Safelist for Dynamic Classes
**Issue**: CEFR level color classes (generated dynamically by `getLevelColor()`) were being purged by Tailwind's tree-shaking.

**Fix**: Added safelist to `tailwind.config.ts` to preserve dynamic color classes:
```typescript
safelist: [
  'bg-gray-100', 'text-gray-600',   // Unknown level
  'bg-green-100', 'text-green-700', // A1-A2
  'bg-yellow-100', 'text-yellow-700', // B1-B2
  'bg-red-100', 'text-red-700',     // C1-C2
]
```

**Impact**: CEFR level badges now display correctly with proper colors

### Vocabulary Management Endpoints

**Endpoints:**
- `POST /dictionary/vocabularies` - Add vocabulary
- `GET /dictionary/vocabularies` - Get vocabulary list (optionally filtered by article_id)
- `DELETE /dictionary/vocabularies/{id}` - Delete vocabulary
- `GET /dictionary/stats` - Get vocabulary statistics (word counts by language)

**Vocabulary 저장:**
- MongoDB `vocabularies` 컬렉션에 저장
- `related_words` 배열 포함 (분리 동사 등 복잡한 언어 구조 지원)
- Article별로 그룹화하여 관리

**Vocabulary 표시:**
- 저장된 단어는 초록색으로 하이라이트
- `related_words`에 포함된 단어들도 함께 초록색 표시
- 예: "hängt" 저장 시 "ab"도 자동으로 초록색 표시

---

## 🧪 Testing Infrastructure

### Web Testing (Vitest)

**Configuration**: `src/web/vitest.config.ts`

**Test Environment**:
- **Framework**: Vitest 4.0.18 with jsdom for DOM simulation
- **UI**: @vitest/ui for interactive test running
- **Testing Library**: @testing-library/react for component testing
- **Test Matchers**: @testing-library/jest-dom for DOM assertions

**Coverage Settings**:
- Provider: v8 (Node.js native coverage)
- Reporters: text, json, html
- Thresholds: 80% for lines, functions, branches, statements
- Excludes: node_modules, test files, test directories

**Test Location**:
- Pattern: `**/__tests__/**/*.test.ts` and `**/__tests__/**/*.test.tsx`
- Current test files:
  - `hooks/__tests__/usePagination.test.ts`
  - `hooks/__tests__/useStatusPolling.test.ts`
  - `lib/__tests__/api.test.ts`
  - `lib/__tests__/formatters.test.ts`
  - `lib/__tests__/styleHelpers.test.ts`

**Run Commands** (`src/web/package.json`):
```bash
npm test         # Run all tests once
npm run test:watch   # Watch mode for development
npm run test:ui      # Interactive UI for test exploration
```

**Alias Resolution**:
- `@` alias resolves to `src/web/` directory
- Matches Next.js path configuration for consistency

**Benefits**:
- Fast test execution with Vitest (ESM-native)
- Interactive UI for debugging
- Coverage reporting for quality assurance
- Type-safe testing with TypeScript
