# 디버깅 가이드

이 프로젝트의 소스코드를 Cursor (또는 VS Code 및 기타 IDE) 디버거로 디버깅하는 방법을 설명합니다.

## ⚠️ 중요: 사전 준비 사항

### 1. Docker로 데이터베이스 실행 (필수)

**디버깅을 시작하기 전에 반드시 MongoDB와 Redis를 Docker로 실행해야 합니다:**

```bash
# Docker Compose로 MongoDB와 Redis 실행
docker-compose -f docker-compose.local.yml up -d

# 실행 확인
docker ps | grep -E "mongodb|redis"
```

데이터베이스가 실행되지 않으면 API 서비스와 Worker 서비스가 시작되지 않습니다.

### 2. 3개 서비스 모두 실행 필요

OPAD는 **3개의 서비스(Web/API/Worker)**가 모두 실행되어야 정상 작동합니다:

- **Web (Next.js)**: 사용자 인터페이스
- **API (FastAPI)**: REST API 및 Job Queue 관리
- **Worker (Python)**: 백그라운드 Job 처리 (CrewAI 실행)

**디버깅 워크플로우:**
1. Docker로 MongoDB와 Redis 실행 (위 단계)
2. 디버깅하려는 서비스는 **IDE 디버거**로 실행 (브레이크포인트 가능)
3. 나머지 서비스는 터미널에서 일반 실행 또는 디버거로 실행

### 3. IDE 디버거 사용 (권장)

**중요**: `npm run dev`나 `uvicorn`을 터미널에서 직접 실행하면 브레이크포인트가 작동하지 않습니다. 반드시 **IDE 디버거(Cursor/VS Code)**를 사용해야 합니다.

## IDE 디버거 설정

### 필수 확장 프로그램

Cursor 또는 VS Code에서 다음 확장 프로그램을 설치하세요:

1. **Python** (ms-python.python) - Python 디버깅
2. **Python Debugger** (ms-python.debugpy) - Python 디버거
3. **JavaScript Debugger** (ms-vscode.js-debug) - Node.js/Next.js 디버깅 (기본 포함)

> **참고**: Cursor는 VS Code 기반이므로 `.vscode/launch.json` 설정 파일이 그대로 작동합니다.

## IDE 디버거 사용 방법 (공통)

### 기본 사용법 (Cursor/VS Code 공통)

1. **디버그 패널 열기**: 왼쪽 사이드바의 "Run and Debug" 아이콘 클릭 (단축키: `Cmd+Shift+D` / `Ctrl+Shift+D`)
2. **설정 선택**: 상단 드롭다운에서 원하는 디버그 설정 선택
3. **브레이크포인트 설정**: 코드 줄 번호 왼쪽을 클릭 (빨간 점 표시)
4. **디버깅 시작**: `F5` 키를 누르거나 재생 버튼 클릭
5. **디버깅 중단**: `Shift+F5` 또는 중지 버튼 클릭
6. **단계 실행**: 
   - `F10`: Step Over (다음 줄)
   - `F11`: Step Into (함수 안으로)
   - `Shift+F11`: Step Out (함수 밖으로)

### 디버그 설정 목록

`.vscode/launch.json`에 정의된 설정:
- **Python: FastAPI (API Server)** - FastAPI 서버 디버깅
- **Python: Worker Service** - Worker 서비스 디버깅
- **Next.js: Debug Server** - Next.js 웹 서버 디버깅

## Python/FastAPI 디버깅

### 1. FastAPI 서버 디버깅

**사전 준비:**
1. Docker로 MongoDB와 Redis 실행 확인
2. 나머지 서비스(Web, Worker)는 터미널에서 일반 실행 (선택사항)

**디버깅 시작:**
1. Cursor/VS Code에서 왼쪽 사이드바의 "Run and Debug" 아이콘 클릭 (또는 `Cmd+Shift+D` / `Ctrl+Shift+D`)
2. 상단 드롭다운에서 "Python: FastAPI (API Server)" 선택
3. `F5` 키를 누르거나 재생 버튼 클릭
4. 브레이크포인트를 설정하려면 코드 줄 번호 왼쪽을 클릭 (빨간 점 표시)
5. API 요청을 보내면 브레이크포인트에서 멈춤

**브레이크포인트 설정 위치 예시:**
- `src/api/routes/articles.py` - Article 엔드포인트
- `src/api/routes/jobs.py` - Job 상태 엔드포인트
- `src/adapter/mongodb/` - MongoDB repository adapters (article, user, vocabulary, token_usage)

### 2. Worker 서비스 디버깅

**사전 준비:**
1. Docker로 MongoDB와 Redis 실행 확인
2. API 서비스는 터미널에서 일반 실행 (job을 enqueue하기 위해 필요)

**디버깅 시작:**
1. Cursor/VS Code 디버그 패널에서 "Python: Worker Service" 설정 선택
2. `F5`로 실행
3. Worker가 Redis에서 job을 가져올 때 브레이크포인트에서 멈춤

**브레이크포인트 설정 위치:**
- `src/worker/processor.py` - `run_worker_loop()` 함수
- `src/adapter/crew/crew.py` - CrewAI 실행 로직

### 3. 현재 파일 디버깅

임의의 Python 파일을 직접 실행하고 디버깅하려면:
1. 파일을 열고 "Python: Current File" 설정 선택
2. `F5`로 실행

## Next.js/TypeScript 디버깅

### ⚠️ 중요: `npm run dev`로 직접 실행하면 디버깅이 안 됩니다!

터미널에서 `npm run dev`로 실행하면 브레이크포인트가 작동하지 않습니다. 반드시 **IDE 디버거 (Cursor/VS Code)**를 사용하거나 **Chrome DevTools**를 사용해야 합니다.

### 방법 1: IDE 디버거 사용 (권장)

**사전 준비:**
1. Docker로 MongoDB와 Redis 실행 확인
2. API 서비스는 터미널에서 일반 실행 (또는 디버거로 실행)

**디버깅 시작:**
1. **디버그 패널 열기**: 왼쪽 사이드바의 "Run and Debug" 아이콘 클릭 (또는 `Cmd+Shift+D`)
2. **설정 선택**: 상단 드롭다운에서 "Next.js: Debug Server" 선택
3. **브레이크포인트 설정**: TypeScript 파일의 줄 번호 왼쪽을 클릭 (빨간 점 표시)
4. **디버깅 시작**: `F5` 키를 누르거나 재생 버튼 클릭
5. **브라우저 접속**: `http://localhost:8000` 접속
6. **디버깅**: 브레이크포인트에서 코드가 멈춤

**브레이크포인트 설정 위치:**
- `src/web/app/page.tsx` - 메인 페이지
- `src/web/app/articles/page.tsx` - Article 리스트 페이지
- `src/web/app/api/**/route.ts` - API 라우트 핸들러 (서버 사이드)

### 방법 2: Chrome DevTools 디버깅 (클라이언트 사이드만)

**서버 사이드 코드 (API 라우트) 디버깅:**
- 반드시 IDE 디버거 사용 (방법 1)

**클라이언트 사이드 코드 (React 컴포넌트) 디버깅:**
1. Next.js 서버 실행 (IDE 디버거로 실행 또는 `npm run dev`)
2. 브라우저에서 `http://localhost:8000` 접속
3. `F12`로 Chrome DevTools 열기
4. Sources 탭 → `localhost:8000` → TypeScript 파일 찾기
5. 브레이크포인트 설정
6. 페이지 상호작용 시 브레이크포인트에서 멈춤

## 디버깅 워크플로우

### 완전한 디버깅 환경 설정 순서

**중요**: 다음 순서를 반드시 지켜주세요.

1. **Docker로 데이터베이스 실행 (필수)**
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   docker ps | grep -E "mongodb|redis"  # 실행 확인
   ```

2. **나머지 서비스 실행 (3개 중 선택)**

#### 시나리오 1: FastAPI 디버깅

1. **MongoDB/Redis**: Docker로 실행 (1단계)
2. **FastAPI**: IDE 디버거로 실행 ("Python: FastAPI (API Server)" 선택 → `F5`)
3. **Worker**: 터미널에서 일반 실행 (필요 시)
   ```bash
   PYTHONPATH=src uv run python -m worker.main
   ```
4. **Next.js**: 터미널에서 일반 실행
   ```bash
   cd src/web && API_BASE_URL=http://localhost:8001 npm run dev
   ```

#### 시나리오 2: Next.js 디버깅

1. **MongoDB/Redis**: Docker로 실행 (1단계)
2. **FastAPI**: 터미널에서 일반 실행
   ```bash
   PYTHONPATH=src uvicorn api.main:app --reload --port 8001
   ```
3. **Worker**: 터미널에서 일반 실행 (필요 시)
   ```bash
   PYTHONPATH=src uv run python -m worker.main
   ```
4. **Next.js**: IDE 디버거로 실행 ("Next.js: Debug Server" 선택 → `F5`)

#### 시나리오 3: Worker 디버깅

1. **MongoDB/Redis**: Docker로 실행 (1단계)
2. **FastAPI**: 터미널에서 일반 실행 (job을 enqueue하기 위해 필요)
   ```bash
   PYTHONPATH=src uvicorn api.main:app --reload --port 8001
   ```
3. **Worker**: IDE 디버거로 실행 ("Python: Worker Service" 선택 → `F5`)
4. **Next.js**: 터미널에서 일반 실행 (선택사항)
   ```bash
   cd src/web && API_BASE_URL=http://localhost:8001 npm run dev
   ```

### 권장 워크플로우

**대부분의 경우 한 번에 하나만 디버깅하는 것을 권장합니다:**

- FastAPI 버그 수정 → FastAPI만 IDE 디버거로 실행, 나머지는 터미널
- Next.js 버그 수정 → Next.js만 IDE 디버거로 실행, 나머지는 터미널
- Worker 버그 수정 → Worker만 IDE 디버거로 실행, 나머지는 터미널
- 전체 플로우 테스트 → 모두 터미널에서 일반 실행 (디버거 없이)

## 디버깅 팁

### 1. 조건부 브레이크포인트

브레이크포인트를 우클릭하고 "Edit Breakpoint" → "Condition"을 설정하면 특정 조건에서만 멈춤

예시:
- `article_id == "specific-id"`
- `status == "failed"`

### 2. 로그포인트

브레이크포인트 대신 로그만 출력하려면:
- 브레이크포인트 우클릭 → "Edit Breakpoint" → "Logpoint"
- 메시지 입력: `Article ID: {article_id}, Status: {status}`

### 3. Watch 표현식

디버그 패널의 "Watch" 섹션에서 변수나 표현식을 모니터링:
- `article.status`
- `len(articles)`
- `response.status_code`

### 4. Call Stack 확인

디버그 패널의 "Call Stack"에서 함수 호출 경로 확인 가능

### 5. 변수 검사

- "Variables" 패널에서 현재 스코프의 모든 변수 확인
- "Debug Console"에서 표현식 실행 가능 (예: `article.get('status')`)


디버깅 설정(`.vscode/launch.json`)에는 이미 로컬 환경 변수가 포함되어 있습니다:
- `MONGO_URL=mongodb://localhost:27017/`
- `MONGODB_DATABASE=opad`
- `REDIS_URL=redis://localhost:6379`

추가 환경 변수(예: `OPENAI_API_KEY`, `SERPER_API_KEY`)가 필요하면 `.env` 파일을 프로젝트 루트에 생성:

```bash
# .env
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key
```

`.vscode/launch.json`의 `envFile` 설정으로 `.env` 파일이 자동으로 로드됩니다.

## 일반적인 디버깅 시나리오

### API 엔드포인트 디버깅

1. `src/api/routes/articles.py`의 `get_article_endpoint` 함수에 브레이크포인트 설정
2. "Python: FastAPI (API Server)" 실행
3. 브라우저나 `curl`로 API 호출:
   ```bash
   curl http://localhost:8000/articles/{article_id}
   ```
4. 브레이크포인트에서 멈춤 → 변수 확인

### 프론트엔드 API 호출 디버깅

1. `src/web/app/api/articles/route.ts`에 브레이크포인트 설정
2. "Next.js: Debug Server" 실행
3. 브라우저에서 `/articles` 페이지 접속
4. 브레이크포인트에서 멈춤 → 요청/응답 확인

### Worker Job 처리 디버깅

1. `src/worker/processor.py`의 `process_job` 함수에 브레이크포인트 설정
2. "Python: Worker Service" 실행
3. API를 통해 job 생성
4. Worker가 job을 처리할 때 브레이크포인트에서 멈춤

## Cursor에서 디버깅 팁

### 빠른 디버깅 시작

1. **코드에서 직접 실행**: Python 파일을 열고 `F5`를 누르면 "Python: Current File" 설정으로 실행됩니다.
2. **터미널 통합**: 디버그 콘솔에서 Python 표현식을 직접 실행할 수 있습니다.
3. **변수 검사**: 디버그가 멈춘 상태에서 변수에 마우스를 올리면 값이 표시됩니다.

## 문제 해결

### MongoDB 연결 오류 (로컬 디버깅 시)

**증상**: `MONGO_URL not configured` 또는 `Failed to create MongoDB indexes` 경고

**해결 방법**:
1. MongoDB가 실행 중인지 확인:
   ```bash
   docker ps | grep mongodb
   # 또는
   docker-compose -f docker-compose.local.yml ps
   ```

2. MongoDB가 실행되지 않았다면:
   ```bash
   docker-compose -f docker-compose.local.yml up -d mongodb
   ```

3. 포트가 올바른지 확인 (기본값: 27017)

4. `.vscode/launch.json`의 환경 변수가 올바른지 확인:
   ```json
   "env": {
     "MONGO_URL": "mongodb://localhost:27017/",
     "MONGODB_DATABASE": "opad"
   }
   ```

### Python 디버거가 연결되지 않음

- `PYTHONPATH`가 올바르게 설정되었는지 확인
- `.vscode/settings.json`의 `python.defaultInterpreterPath` 확인
- 가상환경이 활성화되었는지 확인
- Cursor에서 Python 인터프리터가 올바르게 선택되었는지 확인 (상단 상태바에서 확인 가능)

### Next.js 소스맵이 작동하지 않음

- `src/web/next.config.js`에 소스맵 설정 추가:
  ```js
  module.exports = {
    reactStrictMode: true,
    productionBrowserSourceMaps: true
  }
  ```

### 브레이크포인트가 작동하지 않음

- 파일이 저장되었는지 확인 (`Cmd+S` / `Ctrl+S`)
- 디버거가 올바른 파일을 실행하고 있는지 확인
- `justMyCode: false` 설정 확인 (외부 라이브러리 디버깅 시 필요)
- Cursor를 재시작해보세요

### Cursor 특화 팁

- **AI와 함께 디버깅**: Cursor의 AI 기능을 사용해 에러 메시지를 분석하거나 디버깅 도움을 받을 수 있습니다.
- **코드 검색**: `Cmd+P` (Mac) / `Ctrl+P` (Windows)로 파일을 빠르게 찾아 디버깅할 수 있습니다.
- **통합 터미널**: `Cmd+` ` (백틱)으로 터미널을 열어 로그를 확인하거나 수동으로 서버를 실행할 수 있습니다.
