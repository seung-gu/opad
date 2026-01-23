# 로그인 기능 기획안

## 📋 개요

OPAD에 사용자 인증 기능을 추가하여 개인별 데이터 격리 및 사용자 경험 개선을 목표로 합니다.

**현재 상태:**
- `owner_id` 필드가 이미 Article 모델에 존재하지만 항상 `None`
- MongoDB에 `owner_id` 인덱스가 이미 준비되어 있음
- 중복 체크 로직이 `owner_id`를 고려하도록 설계됨

**목표:**
- 사용자별 Article 및 Vocabulary 데이터 격리
- 사용자별 중복 체크 (다른 사용자는 같은 파라미터로 생성 가능)
- 향후 사용자별 설정 및 통계 기능 확장 가능

---

## 🎯 인증 방식 선택

### 추천: JWT (JSON Web Token) 기반 인증

**이유:**
1. **Stateless**: 서버에 세션 저장 불필요 (Redis/MongoDB 세션 저장소 불필요)
2. **확장성**: 마이크로서비스 아키텍처에 적합 (API 서비스 독립적)
3. **간단한 구현**: FastAPI와 Next.js 모두 JWT 지원이 잘 되어 있음
4. **현재 아키텍처와 호환**: 3-service 구조에서 각 서비스가 독립적으로 토큰 검증 가능

**대안:**
- **Session 기반**: 더 안전하지만 Redis 세션 저장소 필요 (현재 Redis는 Job Queue 전용)
- **OAuth만**: 구현이 간단하지만 이메일/비밀번호 로그인 불가

---

## 🏗️ 아키텍처 설계

### 1. 데이터 모델

#### Users 컬렉션 (MongoDB)
```javascript
{
  "_id": "user-uuid",           // 사용자 ID (owner_id로 사용)
  "email": "user@example.com",  // 이메일 (unique index)
  "password_hash": "...",       // bcrypt 해시
  "name": "User Name",          // 표시 이름
  "created_at": ISODate("..."),
  "updated_at": ISODate("..."),
  "last_login": ISODate("..."), // 마지막 로그인 시간
  "provider": "email" | "google" | "github"  // 로그인 제공자
}
```

**인덱스:**
- `email`: unique index (중복 방지)
- `created_at`: descending (최신 사용자 조회)

#### Articles 컬렉션 (기존)
- `owner_id` 필드 활용 (현재 `None`, 인증 후 사용자 ID로 설정)
- 기존 인덱스 그대로 사용 가능

#### Vocabularies 컬렉션 (확장 필요)
- 현재 `article_id`만 있음
- `owner_id` 필드 추가 권장 (직접 조회 시 성능 향상)

---

### 2. 인증 플로우

#### 회원가입/로그인 플로우
```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│  Web    │                    │   API   │                    │ MongoDB │
│(Next.js)│                    │(FastAPI)│                    │         │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                               │                               │
     │ POST /auth/register           │                               │
     │ {email, password, name}      │                               │
     │──────────────────────────────>│                               │
     │                               │ Check email exists            │
     │                               │──────────────────────────────>│
     │                               │<──────────────────────────────│
     │                               │ Hash password (bcrypt)        │
     │                               │ Create user document          │
     │                               │──────────────────────────────>│
     │                               │<──────────────────────────────│
     │                               │ Generate JWT                  │
     │<──────────────────────────────│                               │
     │ {token, user: {id, email}}    │                               │
     │                               │                               │
     │ Store token in localStorage    │                               │
     │ or httpOnly cookie            │                               │
```

#### 인증된 요청 플로우
```
┌─────────┐                    ┌─────────┐
│  Web    │                    │   API   │
│(Next.js)│                    │(FastAPI)│
└────┬────┘                    └────┬────┘
     │                               │
     │ GET /articles                 │
     │ Authorization: Bearer <token> │
     │──────────────────────────────>│
     │                               │ Verify JWT                   │
     │                               │ Extract user_id               │
     │                               │ Filter by owner_id           │
     │<──────────────────────────────│
     │ {articles: [...]}             │
```

---

## 🔐 보안 고려사항

### 1. 비밀번호 저장
- **bcrypt** 사용 (Python: `passlib[bcrypt]`, Node.js: `bcryptjs`)
- Salt rounds: 12 (적절한 보안/성능 균형)

### 2. JWT 토큰
- **Secret Key**: 환경변수로 관리 (`JWT_SECRET_KEY`)
- **만료 시간**: 
  - Access Token: 7일 (일반 사용)
  - Refresh Token: 30일 (선택적, 향후 구현)
- **Algorithm**: HS256 (대칭키, 단순하고 충분)

### 3. 토큰 저장
**옵션 1: localStorage (추천)**
- 장점: 구현 간단, XSS만 방어하면 됨
- 단점: XSS 공격에 취약 (하지만 Next.js는 기본적으로 XSS 방어)

**옵션 2: httpOnly Cookie**
- 장점: XSS 공격에 더 안전
- 단점: CSRF 방어 필요, CORS 설정 복잡

**초기 구현**: localStorage 사용, 향후 필요시 Cookie로 전환

### 4. CORS 설정
- `allow_credentials=True`로 변경 필요 (Cookie 사용 시)
- `CORS_ORIGINS` 환경변수에 명시적 origin 리스트 설정

---

## 📁 구현 구조

### Backend (FastAPI)

```
src/api/
├── routes/
│   └── auth.py              # 새로 생성
│       ├── POST /auth/register
│       ├── POST /auth/login
│       ├── POST /auth/logout (선택적)
│       └── GET /auth/me     # 현재 사용자 정보
├── middleware/
│   └── auth.py              # 새로 생성
│       ├── get_current_user()  # JWT 검증 및 사용자 추출
│       └── Optional[User]      # 선택적 인증 (public endpoints)
└── models.py
    └── User 모델 추가
```

**의존성 추가:**
```toml
# pyproject.toml
[project]
dependencies = [
    "python-jose[cryptography]>=3.3.0",  # JWT 처리
    "passlib[bcrypt]>=1.7.4",            # 비밀번호 해싱
    "python-multipart>=0.0.6",           # Form 데이터 파싱
]
```

### Frontend (Next.js)

```
src/web/
├── app/
│   ├── login/
│   │   └── page.tsx         # 로그인 페이지
│   ├── register/
│   │   └── page.tsx         # 회원가입 페이지
│   └── api/
│       └── auth/
│           ├── login/
│           │   └── route.ts  # 로그인 API 프록시
│           └── register/
│               └── route.ts  # 회원가입 API 프록시
├── components/
│   ├── LoginForm.tsx        # 로그인 폼
│   ├── RegisterForm.tsx     # 회원가입 폼
│   └── AuthProvider.tsx     # 인증 컨텍스트 (선택적)
└── lib/
    └── auth.ts              # 토큰 관리 유틸리티
```

**의존성 추가:**
```json
// package.json
{
  "dependencies": {
    "js-cookie": "^3.0.5"  // Cookie 관리 (선택적)
  }
}
```

---

## 🔄 기존 API 수정 사항

### 1. Articles API

**변경 전:**
```python
@router.post("/generate")
async def generate_article(request: GenerateRequest):
    owner_id = None  # 항상 None
```

**변경 후:**
```python
@router.post("/generate")
async def generate_article(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user)  # 인증 필수
):
    owner_id = current_user.id
```

**Public Endpoints (인증 불필요):**
- `GET /health` - 헬스 체크
- `GET /` - 루트 엔드포인트

**Protected Endpoints (인증 필수):**
- `POST /articles/generate` - Article 생성
- `GET /articles` - Article 목록 (자신의 것만)
- `GET /articles/{id}` - Article 조회 (소유자만)
- `DELETE /articles/{id}` - Article 삭제 (소유자만)

### 2. Dictionary API

**변경:**
- Vocabulary 저장/조회 시 `owner_id` 필터링 추가
- 사용자별 Vocabulary 통계 제공

### 3. Stats API

**변경:**
- 사용자별 통계 제공 (전체 통계는 관리자만)

---

## 🎨 UI/UX 설계

### 1. 로그인/회원가입 페이지

**레이아웃:**
- 간단한 폼 디자인 (Tailwind CSS 활용)
- 이메일/비밀번호 입력
- "로그인" / "회원가입" 버튼
- 에러 메시지 표시

**위치:**
- `/login` - 로그인 페이지
- `/register` - 회원가입 페이지

### 2. 인증 상태 표시

**헤더/네비게이션:**
- 로그인 상태: 사용자 이메일 표시 + "로그아웃" 버튼
- 비로그인 상태: "로그인" / "회원가입" 버튼

### 3. 보호된 페이지

**리다렉션:**
- 인증되지 않은 사용자가 보호된 페이지 접근 시 `/login`으로 리다렉션
- 로그인 후 원래 페이지로 돌아가기 (redirect 파라미터)

---

## 📊 마이그레이션 전략

### 1. 기존 데이터 처리

**옵션 1: Anonymous User 유지 (추천)**
- 기존 `owner_id=None`인 Article은 그대로 유지
- 로그인하지 않은 사용자는 여전히 Article 생성 가능 (owner_id=None)
- 로그인한 사용자는 자신의 Article만 조회

**옵션 2: 기존 데이터를 특정 사용자에게 할당**
- 마이그레이션 스크립트로 기존 Article에 `owner_id` 할당
- 복잡하고 위험함 (권장하지 않음)

**초기 구현**: 옵션 1 사용

### 2. 점진적 배포

**Phase 1: 인증 기능 추가 (기존 기능 유지)**
- 로그인/회원가입 기능 추가
- 기존 API는 인증 선택적 (Optional)
- 로그인한 사용자는 `owner_id` 설정, 비로그인은 `None`

**Phase 2: 인증 강제 (선택적)**
- 특정 엔드포인트만 인증 필수로 변경
- 사용자 피드백 수집 후 결정

---

## 🧪 테스트 계획

### 1. Backend 테스트
- 회원가입 성공/실패 케이스
- 로그인 성공/실패 케이스
- JWT 토큰 검증
- 인증된 요청에서 `owner_id` 자동 설정
- 사용자별 데이터 격리 확인

### 2. Frontend 테스트
- 로그인/회원가입 폼 유효성 검사
- 토큰 저장/로드
- 인증되지 않은 요청 처리
- 로그아웃 기능

### 3. 통합 테스트
- 전체 인증 플로우 (회원가입 → 로그인 → Article 생성 → 조회)
- 여러 사용자 간 데이터 격리 확인

---

## 📝 구현 단계

### Phase 1: 기본 인증 (MVP)
1. ✅ Users 컬렉션 및 모델 생성
2. ✅ 회원가입 API (`POST /auth/register`)
3. ✅ 로그인 API (`POST /auth/login`)
4. ✅ JWT 토큰 생성/검증 미들웨어
5. ✅ 로그인/회원가입 페이지 (Next.js)
6. ✅ 토큰 저장/관리 (localStorage)
7. ✅ Article 생성 시 `owner_id` 자동 설정
8. ✅ Article 조회 시 `owner_id` 필터링

**예상 작업 시간**: 2-3일

### Phase 2: 데이터 격리 강화
1. ✅ Vocabulary에 `owner_id` 추가
2. ✅ 모든 CRUD 작업에 `owner_id` 필터링
3. ✅ 통계 API 사용자별 필터링

**예상 작업 시간**: 1일

### Phase 3: UX 개선 (선택적)
1. ✅ "현재 사용자" 표시 (헤더)
2. ✅ 로그아웃 기능
3. ✅ 자동 로그인 (토큰 갱신)
4. ✅ 비밀번호 재설정 (이메일 인증)

**예상 작업 시간**: 2-3일

---

## 🔮 향후 확장 가능성

### 1. OAuth 로그인
- Google, GitHub 로그인 추가
- `provider` 필드 활용

### 2. 사용자 프로필
- 프로필 수정 (이름, 이메일)
- 언어 설정 저장
- 학습 목표 설정

### 3. 사용자 통계
- 생성한 Article 수
- 저장한 Vocabulary 수
- 학습 진행률

### 4. 소셜 기능 (선택적)
- Article 공유
- Vocabulary 공유
- 학습 그룹

---

## ⚠️ 주의사항

1. **비밀번호 정책**: 최소 8자, 영문+숫자 조합 권장
2. **이메일 검증**: 초기에는 선택적, 향후 이메일 인증 추가 가능
3. **Rate Limiting**: 로그인/회원가입 API에 rate limiting 적용 (DDoS 방어)
4. **에러 메시지**: 보안을 위해 구체적인 에러 메시지 피하기 (예: "이메일 또는 비밀번호가 올바르지 않습니다")

---

## 📚 참고 자료

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Next.js Authentication](https://nextjs.org/docs/authentication)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
