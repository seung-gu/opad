# DEVLOG

## 2026-01-07

### 목표
- **3가지 서비스로 분리**: `web` / `api` / `worker`
- **기사/유저 단위 확장**: “최신 1개 파일” 방식에서 벗어나, `article_id` 기반으로 여러 페이지/여러 결과를 다룰 수 있게 만들기
- **병목 회피**: CrewAI 실행(무거운 작업)을 `worker`로 격리하고, `web`/`api`는 가볍게 유지

---

### 핵심 원칙: “한 컨테이너 = 한 역할(프로세스)”
컨테이너는 작은 VM이 아니라, **특정 역할의 프로세스를 실행하는 단위**로 보는 게 운영/확장에 유리하다.

- **장점**
  - **스케일링 단순화**: 느린 게 `worker`면 `worker`만 복제(수평 확장)하면 됨
  - **장애 격리**: CrewAI가 CPU/메모리를 사용해도 `web`/`api` 영향 최소화
  - **배포/롤백 분리**: `api`만 수정해도 `worker`/`web`의 위험을 줄임
  - **관측/디버깅 용이**: “이 컨테이너의 로그는 worker만”처럼 원인 추적이 쉬움

- **피해야 할 패턴**
  - 한 컨테이너에서 `next start` + `python spawn(detached)` 같이 섞어 돌리면
    - 리소스 경쟁/동시성/타임아웃 문제가 서로 얽히고
    - 작업 재시도/중복 방지/장애 복구가 애매해지기 쉬움

---

### 3-service 아키텍처(개략)
- **web (Next.js)**
  - UI 페이지: `/articles`, `/articles/[id]`, `/jobs/[jobId]`
  - “Generate” 클릭 → `api`에 요청
  - job 상태는 폴링(초기 권장) 또는 SSE(추후)

- **api (FastAPI)**
  - Article/Job CRUD
  - `POST /articles/:id/generate` 시 **즉시 `jobId` 반환**
  - Redis 큐에 job enqueue
  - DB/R2에 저장된 결과를 조회 형태로 제공

- **worker (Python + CrewAI)**
  - Redis 큐 consume → CrewAI 실행
  - 결과 저장(R2 + DB 업데이트)
  - job 상태 업데이트(`queued → running → succeeded/failed`)
  - **동시성 제한**, **재시도 정책**, **idempotency**(중복 생성 방지)

---

### 데이터/스토리지 방향(확장성 포인트)
- **Postgres**
  - `articles`: url, title, status, owner_id(추후), created_at …
  - `jobs`: article_id, status, progress, result_ref, error, started_at, finished_at …
- **Redis**
  - job queue / retry / backpressure
- **R2**
  - “고정 파일 1개”가 아니라, **Article ID 기반 Key**
  - 예: `articles/{article_id}/adapted.md`, `articles/{article_id}/meta.json`

---

### Railway에서 3-service로 운영(요약)
1. Railway 프로젝트에서 **Service 3개 생성**: `web`, `api`, `worker` (같은 레포 연결 가능)
2. **Add-on 추가**: Postgres, Redis
3. 환경변수 연결
   - `api`, `worker`: `DATABASE_URL`, `REDIS_URL`, `R2_*`, `OPENAI_API_KEY` 등
   - `web`: `API_BASE_URL`(api 주소) 등
4. 서비스별 Start Command 분리
   - `web`: `next start`
   - `api`: `uvicorn ... --port $PORT`
   - `worker`: `python ...` (HTTP 포트 불필요)
5. 병목 시 **worker만 scale out**

---

### 로드맵(마일스톤 초안)
- **M0**: 3-service skeleton + Railway(Postgres/Redis) 기본 구성 → [#7](https://github.com/seung-gu/opad/issues/7) ✅
- **M1**: Article/Job DB 스키마 + API 엔드포인트 + R2 key 구조 변경
- **M2**: FE 라우트 분리(`/articles`, `/articles/[id]`, `/jobs/[jobId]`) + 폴링 UX
- **M3**: worker 안정화(idempotency, concurrency, retry, observability) + 운영/문서화

---

## 2026-01-08

### Completed: 3-Service Architecture Implementation [#7](https://github.com/seung-gu/opad/issues/7)
- ✅ Web/API/Worker service separation and Railway deployment
- ✅ Redis Job Queue implementation
- ✅ Progress tracking (Redis-based)
- ✅ Error handling improvements

---

### 공부/참고 키워드(우선순위)
- **Queue 기반 비동기 아키텍처**: job 상태 머신(queued/running/succeeded/failed)
- **Idempotency**: generate 연타/재시도에도 중복 job 방지
- **Backpressure / Concurrency control**: 처리량보다 요청이 많을 때 시스템이 죽지 않게
- **12-Factor App**: 환경변수, stateless, 로그 stdout, 분리된 프로세스
- **Next.js App Router**: 라우팅/데이터 패칭, 폴링 UI 패턴

