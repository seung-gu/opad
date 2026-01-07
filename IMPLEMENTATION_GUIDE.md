# 구현 가이드: 이슈 #7 완료

## 📚 학습 내용 요약

### 1. **아키텍처 패턴: Job Queue**

#### 문제 상황
- CrewAI 실행은 2-5분 걸림
- HTTP 요청은 보통 30초 타임아웃
- 사용자는 기다릴 수 없음

#### 해결 방법: 비동기 Job 처리
```
사용자 요청 → 즉시 jobId 반환 (1초 이내)
           ↓
        백그라운드에서 실제 작업 처리
           ↓
        사용자는 jobId로 상태 폴링
```

#### 구현
- **Redis Queue**: Job을 큐에 저장 (`LPUSH`)
- **Worker**: 큐에서 Job 가져오기 (`BRPOP` - blocking)
- **상태 저장**: Redis에 Job 상태 저장 (`SET opad:job:{id}`)

---

### 2. **서비스 분리 원칙**

#### "한 컨테이너 = 한 역할"
각 서비스는 하나의 책임만 가집니다:

| 서비스 | 역할 | 실행하는 것 | 실행하지 않는 것 |
|--------|------|------------|----------------|
| **Web** | UI 제공 | Next.js 서버 | Python, CrewAI |
| **API** | CRUD + Enqueue | FastAPI 서버 | CrewAI 실행 |
| **Worker** | 작업 처리 | CrewAI 실행 | HTTP 서버 |

#### 장점
1. **독립적 스케일링**: Worker만 늘리면 됨
2. **장애 격리**: Worker 죽어도 Web/API는 정상
3. **배포 분리**: API만 수정해도 Worker 영향 없음

---

### 3. **Redis 활용**

#### Queue (List)
```python
# Job 추가
redis.lpush('opad:jobs', json.dumps(job_data))

# Job 가져오기 (blocking)
job_data = redis.brpop('opad:jobs', timeout=1)
```

#### Status (String, JSON)
```python
# 상태 저장
redis.setex(
    f'opad:job:{job_id}',
    86400,  # 24시간 TTL
    json.dumps(status_data)
)

# 상태 조회
status = json.loads(redis.get(f'opad:job:{job_id}'))
```

---

### 4. **FastAPI 기본 구조**

#### 앱 생성
```python
from fastapi import FastAPI

app = FastAPI(title="OPAD API")
```

#### 라우터 등록
```python
from api.routes import articles, jobs

app.include_router(articles.router)
app.include_router(jobs.router)
```

#### Pydantic 모델
```python
from pydantic import BaseModel

class ArticleCreate(BaseModel):
    language: str
    level: str
    length: str
    topic: str
```

#### 엔드포인트
```python
@router.post("/articles", response_model=ArticleResponse)
async def create_article(article: ArticleCreate):
    # 자동으로 JSON 파싱, 검증, 직렬화
    return ArticleResponse(...)
```

---

### 5. **현재 구조에서의 변경점**

#### Before: 단일 프로세스
```
Next.js 컨테이너
├── Next.js 서버 (Port 3000)
└── Python spawn (백그라운드)
    └── CrewAI 실행
        └── status.json 파일 쓰기
```

**문제점:**
- Next.js와 Python이 리소스 경쟁
- 확장 불가능 (둘 다 함께 스케일)
- 장애 격리 불가

#### After: 3-Service
```
Web (Next.js)
  └── HTTP → API (FastAPI)
              └── Redis Queue
                  └── Worker (Python)
                      └── CrewAI 실행
```

**장점:**
- 각 서비스 독립적
- Worker만 스케일 가능
- Worker 죽어도 Web/API 정상

---

## 🔍 코드 흐름 상세 분석

### 1. 사용자가 "Generate" 클릭

#### `web/app/page.tsx`
```typescript
const handleGenerate = async (inputs) => {
  // POST /api/generate 호출
  const response = await fetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify(inputs)
  })
  
  const data = await response.json()
  setCurrentJobId(data.job_id)  // jobId 저장
}
```

#### `web/app/api/generate/route.ts`
```typescript
// Step 1: Article 생성
const article = await fetch(`${apiBaseUrl}/articles`, {
  method: 'POST',
  body: JSON.stringify(inputs)
})

// Step 2: Job enqueue
const job = await fetch(`${apiBaseUrl}/articles/${articleId}/generate`, {
  method: 'POST',
  body: JSON.stringify(inputs)
})

return { job_id: job.job_id, article_id: articleId }
```

#### `src/api/routes/articles.py`
```python
@router.post("/{article_id}/generate")
async def generate_article(article_id: str, request: GenerateRequest):
    job_id = str(uuid.uuid4())
    
    # Redis 큐에 job 추가
    enqueue_job(job_id, article_id, inputs)
    
    # Job 상태 초기화
    update_job_status(job_id, 'queued', 0, 'Job queued...')
    
    return GenerateResponse(job_id=job_id, ...)
```

---

### 2. Worker가 Job 처리

#### `src/worker/main.py`
```python
def main():
    while True:
        # 큐에서 job 가져오기 (blocking)
        job_data = dequeue_job()
        if job_data:
            process_job(job_data)
```

#### `src/worker/processor.py`
```python
def process_job(job_data: dict):
    job_id = job_data['job_id']
    
    # 상태: running
    update_job_status(job_id, 'running', 0, 'Starting...')
    
    # CrewAI 실행
    result = run_crew(inputs=inputs)
    
    # R2 업로드
    upload_to_cloud(result.raw)
    
    # 상태: succeeded
    update_job_status(job_id, 'succeeded', 100, 'Completed!')
```

---

### 3. 클라이언트가 상태 폴링

#### `web/app/page.tsx`
```typescript
useEffect(() => {
  if (!currentJobId) return
  
  const interval = setInterval(() => {
    // GET /api/status?job_id=...
    fetch(`/api/status?job_id=${currentJobId}`)
      .then(res => res.json())
      .then(data => {
        setProgress(data)
        if (data.status === 'completed') {
          clearInterval(interval)
          loadContent()  // 결과 로드
        }
      })
  }, 2000)  // 2초마다
}, [currentJobId])
```

#### `web/app/api/status/route.ts`
```typescript
const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`)
const jobData = await response.json()

// 기존 형식과 호환되도록 변환
return {
  current_task: jobData.status === 'running' ? 'processing' : '',
  progress: jobData.progress,
  status: jobData.status === 'succeeded' ? 'completed' : ...
}
```

#### `src/api/routes/jobs.py`
```python
@router.get("/{job_id}")
async def get_job_status_endpoint(job_id: str):
    status_data = get_job_status(job_id)  # Redis에서 조회
    return JobResponse(**status_data)
```

---

## 🎓 핵심 개념 정리

### 1. **비동기 처리 (Asynchronous Processing)**
- **동기**: 요청 → 처리 → 응답 (모두 기다림)
- **비동기**: 요청 → 즉시 응답 → 백그라운드 처리 → 상태 조회

### 2. **Job Queue 패턴**
- **Producer**: Job을 큐에 추가 (API)
- **Consumer**: 큐에서 Job 가져와서 처리 (Worker)
- **상태 저장소**: Job 상태를 별도로 저장 (Redis)

### 3. **서비스 분리 (Microservices)**
- 각 서비스는 독립적으로 배포/스케일 가능
- 서비스 간 통신은 HTTP/Queue 사용
- 장애가 한 서비스에만 영향

### 4. **Redis 활용**
- **Queue**: List 자료구조 (`LPUSH`, `BRPOP`)
- **Cache**: String 자료구조 (`SET`, `GET`)
- **TTL**: 자동 만료 (`SETEX`)

---

## 🚀 다음 단계 학습

### 이슈 #8: Postgres + Redis
- 현재: 메모리 저장 (임시)
- 학습: ORM (SQLAlchemy), DB 마이그레이션

### 이슈 #9: Dockerfile 전략
- 현재: 단일 Dockerfile
- 학습: Multi-stage build, 최적화

### 이슈 #10: Health endpoint
- 현재: 기본 health check
- 학습: 의존성 체크 (Redis, DB)

---

## 📖 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Redis 명령어](https://redis.io/commands/)
- [Job Queue 패턴](https://www.cloudamqp.com/blog/2015-05-18-part1-rabbitmq-for-beginners-what-is-message-queueing.html)
- [Microservices 아키텍처](https://microservices.io/patterns/microservices.html)
