# 참고문서

API 플로우 다이어그램 및 아키텍처 문서

---

## API Architecture Overview

This diagram shows the overall architecture of the application, including Frontend, Backend, and Services.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#60a5fa','primaryTextColor':'#1e293b','primaryBorderColor':'#2563eb','lineColor':'#475569','secondaryColor':'#4ade80','tertiaryColor':'#f87171','clusterBkg':'#f1f5f9','clusterBorder':'#64748b'}}}%%
graph TB
    subgraph Frontend["Frontend - Next.js"]
        FE["page.tsx"]
        API__api_articles["GET /api/articles"]
        FE --> API__api_articles
        API__api_status["GET /api/status"]
        FE --> API__api_status
        API__api_generate["POST /api/generate"]
        FE --> API__api_generate
        API__api_article["GET /api/article"]
        FE --> API__api_article
        API__api_stats["GET /api/stats"]
        FE --> API__api_stats
        API__api_articles_id["GET /api/articles/[id]"]
        FE --> API__api_articles_id
        API__api_dictionary_search["POST /api/dictionary/search"]
        FE --> API__api_dictionary_search
        API__api_dictionary_vocabularies["POST/GET /api/dictionary/vocabularies"]
        FE --> API__api_dictionary_vocabularies
        API__api_dictionary_vocabularies_id["DELETE /api/dictionary/vocabularies/[id]"]
        FE --> API__api_dictionary_vocabularies_id
        API__api_dictionary_stats["GET /api/dictionary/stats"]
        FE --> API__api_dictionary_stats
    end

    subgraph Backend["Backend - FastAPI"]
        subgraph Articles["Articles"]
            FastAPI__articles["GET /articles"]
            FastAPI__articles_generate["POST /articles/generate"]
            FastAPI__articles_get["GET /articles/{article_id}"]
            FastAPI__articles_delete["DELETE /articles/{article_id}"]
            FastAPI__articles_content["GET /articles/{article_id}/content"]
        end
        subgraph Jobs["Jobs"]
            FastAPI__jobs_job_id["GET /jobs/{job_id}"]
        end
        subgraph Health["Health"]
            FastAPI__health["GET /health"]
        end
        subgraph Auth["Auth"]
            FastAPI__auth_register["POST /auth/register"]
            FastAPI__auth_login["POST /auth/login"]
            FastAPI__auth_me["GET /auth/me"]
        end
        subgraph Meta["Meta"]
            FastAPI__endpoints["GET /endpoints"]
        end
        subgraph Stats["Stats"]
            FastAPI__stats["GET /stats"]
        end
        subgraph Dictionary["Dictionary"]
            FastAPI__dictionary_search["POST /dictionary/search"]
            FastAPI__dictionary_vocab_post["POST /dictionary/vocabulary"]
            FastAPI__dictionary_vocab_get["GET /dictionary/vocabularies"]
            FastAPI__dictionary_vocab_delete["DELETE /dictionary/vocabularies/{vocabulary_id}"]
        end
        subgraph ArticleVocab["Articles - Vocabularies"]
            FastAPI__articles_vocabularies["GET /articles/{article_id}/vocabularies"]
        end
        subgraph Uncategorized["Uncategorized"]
            FastAPI__root["GET /"]
        end
    end

    subgraph Services["Services"]
        MongoDB[("MongoDB")]
        Redis[("Redis Queue")]
    end
    Backend --> MongoDB
    Backend --> Redis
```

---

## Request Flow - Article Generation

This sequence diagram shows the complete request flow for article generation, from client request to worker processing.

```mermaid
sequenceDiagram
    participant Client as Client (Browser)
    participant NextJS as Next.js API Route
    participant FastAPI as FastAPI Backend
    participant Redis as Redis Queue
    participant Worker as Worker Service
    participant MongoDB as MongoDB

    Note over Client,Worker: Article Generation Flow
    Client->>NextJS: POST /api/generate<br/>{language, level, length, topic}
    NextJS->>FastAPI: POST /articles/generate
    FastAPI->>FastAPI: Check for duplicates
    alt Duplicate found
        FastAPI-->>NextJS: 409 Conflict + existing_job
        NextJS-->>Client: 409 + {duplicate: true}
        Client->>Client: Confirm (force=true)
        Client->>NextJS: POST /api/generate (force=true)
        NextJS->>FastAPI: POST /articles/generate?force=true
    end
    FastAPI->>MongoDB: Save article metadata
    FastAPI->>Redis: Enqueue job
    FastAPI-->>NextJS: 200 OK + {job_id, article_id}
    NextJS-->>Client: 200 OK + {job_id, article_id}
    Client->>Client: Poll job status
    loop Polling - Update job status
        Client->>NextJS: GET /api/status?job_id=xxx
        NextJS->>FastAPI: GET /jobs/{job_id}
        FastAPI->>Redis: Get job status
        Redis-->>FastAPI: Status data
        FastAPI-->>NextJS: Job status
        NextJS-->>Client: Job status
    end
    Redis->>Worker: Dequeue job
    Worker->>Worker: Process job (CrewAI)
    Worker->>Redis: Update job status
    Worker->>MongoDB: Upload result
```

## Duplicate Detection Flow

### Backend Flow

```mermaid
graph TD
    A[POST /articles/generate] --> B{force=true?}
    B -->|Yes| C[Skip duplicate check]
    B -->|No| D[Search MongoDB for duplicates]
    D --> E{Found duplicate?}
    E -->|Yes| F[Get job status from Redis]
    F --> G[Raise HTTPException 409 with existing_job]
    G -->|force=true|A
    E -->|No| H[Continue: Create article]
    C --> H
    H --> I[Generate article_id + job_id]
    I --> J[Save to MongoDB]
    J --> K[Enqueue job to Redis]
    K --> L[Return job_id]
```

### Complete Flow (Browser to Backend)

This diagram shows the complete flow when a duplicate is detected, including browser interaction and retry logic.

**Files:**
- FastAPI: `src/api/routes/articles.py:189` - Raises `HTTPException(status_code=409)`
- Next.js API Route: `src/web/app/api/generate/route.ts:58-78` - Handles 409 and returns `NextResponse.json({ status: 409 })`
- Browser: `src/web/app/page.tsx:235-273` - Fetches and handles 409 response

```
User submits form
    ↓
handleGenerate(inputs, force=false)  ← First call
    ↓
fetch('/api/generate', { force: false })
    ↓
FastAPI: _check_duplicate(inputs, force=False)
    ↓
Duplicate found! → HTTPException(409)
    ↓
Browser: response.status === 409
    ↓
window.confirm("A queued job exists. Do you want to generate new?")
    ↓
User clicks "OK"
    ↓
handleGenerate(inputs, force=true)  ← Second call (recursive!)
    ↓
fetch('/api/generate', { force: true })
    ↓
FastAPI: _check_duplicate(inputs, force=True)
    ↓
force=True → Skip duplicate check!
    ↓
New article + job created successfully! ✅
```

---

## Next.js to FastAPI HTTP Communication Flow

This diagram shows how Next.js API Route communicates with FastAPI backend over HTTP network.

**Files:**
- Next.js API Route: `src/web/app/api/generate/route.ts:32-44` - Calls FastAPI with fetch
- FastAPI: `src/api/routes/articles.py` - Receives HTTP request and responds

```
Next.js API Route (route.ts)
localhost:8000
    │
    │ fetch("http://localhost:8001/articles/generate", {
    │   method: 'POST',
    │   body: JSON.stringify({...})
    │ })
    │
    ▼
HTTP Network Request
(TCP/IP socket communication)
    │
    ▼
FastAPI Server (articles.py)
localhost:8001
@router.post("/generate")  ← URL path matching!
async def generate_article():
    raise HTTPException(409)
    │
    │ HTTP 409 Response
    │
    ▼
HTTP Network Response
    │
    ▼
Next.js API Route
generateResponse.status === 409  ← Response handling!
```

---

## FastAPI Endpoints

### Summary
- Total endpoints: 16
- Tags: meta, health, jobs, stats, articles, dictionary

### Endpoints by Tag

#### Articles

- **GET** `/articles` - List articles with filters (status, language, level) and pagination
- **POST** `/articles/generate` - Create article and start generation (unified endpoint)
- **GET** `/articles/{article_id}` - Get article metadata
- **DELETE** `/articles/{article_id}` - Soft delete article (marks status='deleted')
- **GET** `/articles/{article_id}/content` - Get article content (markdown)
- **GET** `/articles/{article_id}/vocabularies` - Get vocabularies for a specific article

#### Default

- **GET** `/` - Root

#### Health

- **GET** `/health` - Health

#### Jobs

- **GET** `/jobs/{job_id}` - Get Job Status Endpoint

#### Meta

- **GET** `/endpoints` - List Endpoints

#### Stats

- **GET** `/stats` - Get Database Stats Endpoint

#### Dictionary

- **POST** `/dictionary/search` - Search for word definition and lemma from sentence context
- **POST** `/dictionary/vocabulary` - Add vocabulary word
- **GET** `/dictionary/vocabularies` - Get aggregated vocabulary list (grouped by lemma with counts)
- **DELETE** `/dictionary/vocabularies/{vocabulary_id}` - Delete vocabulary word

#### Authentication

- **POST** `/auth/register` - Register a new user account
- **POST** `/auth/login` - Authenticate and obtain JWT token
- **GET** `/auth/me` - Get current authenticated user information

---

## Detailed API Endpoint Documentation

### Articles Endpoints

#### POST /articles/generate

**Description**: Create article and start generation (unified endpoint).

**Auth**: Required (JWT)

**Request**:
```json
{
  "language": "string",
  "level": "string",
  "length": "string",
  "topic": "string"
}
```

**Query Parameters**:
- `force` (boolean, optional): If true, skip duplicate check and create new article

**Response** (200):
```json
{
  "job_id": "uuid",
  "article_id": "uuid",
  "message": "Article generation started. Use job_id to track progress."
}
```

**Response** (409 - Duplicate):
```json
{
  "detail": {
    "error": "Duplicate article detected",
    "message": "An article with identical parameters was created within the last 24 hours.",
    "article_id": "uuid",
    "existing_job": {
      "id": "uuid",
      "status": "queued|running|completed|failed",
      "progress": 0-100
    }
  }
}
```

---

#### GET /articles

**Description**: Get article list with filters and pagination.

**Auth**: Required (JWT) - Returns only articles owned by authenticated user

**Query Parameters**:
- `skip` (integer, default: 0): Number of articles to skip
- `limit` (integer, default: 20, max: 100): Maximum articles to return
- `status` (string, optional): Filter by status (running, completed, failed, deleted)
- `language` (string, optional): Filter by language
- `level` (string, optional): Filter by level

**Response** (200):
```json
{
  "articles": [
    {
      "id": "uuid",
      "language": "string",
      "level": "string",
      "length": "string",
      "topic": "string",
      "status": "running|completed|failed|deleted",
      "created_at": "2025-01-28T12:34:56+00:00",
      "user_id": "uuid",
      "job_id": "uuid",
      "inputs": {
        "language": "string",
        "level": "string",
        "length": "string",
        "topic": "string"
      }
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 20
}
```

---

#### GET /articles/{article_id}

**Description**: Get article metadata by ID.

**Auth**: Required (JWT) - Users can only access their own articles

**Response** (200):
```json
{
  "id": "uuid",
  "language": "string",
  "level": "string",
  "length": "string",
  "topic": "string",
  "status": "running|completed|failed|deleted",
  "created_at": "2025-01-28T12:34:56+00:00",
  "user_id": "uuid",
  "job_id": "uuid",
  "inputs": {
    "language": "string",
    "level": "string",
    "length": "string",
    "topic": "string"
  }
}
```

---

#### GET /articles/{article_id}/content

**Description**: Get article content in markdown format.

**Auth**: Required (JWT) - Users can only access their own articles

**Response** (200): Plain text markdown content

**Response** (404): If content not available yet (article still processing)

---

#### GET /articles/{article_id}/vocabularies

**Description**: Get vocabularies for a specific article with grammatical metadata.

**Auth**: Required (JWT) - Users can only access their own articles' vocabularies

**Response** (200):
```json
[
  {
    "id": "uuid",
    "article_id": "uuid",
    "word": "string",
    "lemma": "string",
    "definition": "string",
    "sentence": "string",
    "language": "string",
    "related_words": ["string"],
    "span_id": "string",
    "created_at": "2025-01-28T12:34:56+00:00",
    "user_id": "uuid",
    "pos": "noun|verb|adjective|etc",
    "gender": "der|die|das|le|la|el|la",
    "conjugations": {
      "present": "string",
      "past": "string",
      "perfect": "string"
    },
    "level": "A1|A2|B1|B2|C1|C2"
  }
]
```

---

#### DELETE /articles/{article_id}

**Description**: Soft delete article by setting status='deleted'.

**Auth**: Required (JWT) - Users can only delete their own articles

**Response** (200):
```json
{
  "success": true,
  "article_id": "uuid",
  "message": "Article soft deleted (status='deleted')"
}
```

---

### Authentication Endpoints

#### POST /auth/register

**Description**: Register a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "name": "User Name"
}
```

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)

**Response** (201 - Created):
```json
{
  "token": "jwt_token_string",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

**Response** (400 - Invalid Password):
```json
{
  "detail": "Password must contain at least one uppercase letter"
}
```

**Response** (409 - Email Already Registered):
```json
{
  "detail": "Email already registered"
}
```

---

#### POST /auth/login

**Description**: Authenticate and obtain JWT token.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response** (200):
```json
{
  "token": "jwt_token_string",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

**Response** (401 - Invalid Credentials):
```json
{
  "detail": "Invalid email or password"
}
```

---

#### GET /auth/me

**Description**: Get current authenticated user information.

**Auth**: Required (JWT)

**Response** (200):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name"
}
```

**Response** (401 - Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### Dictionary Endpoints

#### POST /dictionary/search

**Description**: Search for word definition, lemma, and grammatical metadata using OpenAI API.

**Auth**: Required (JWT) - Prevents API abuse

**Request**:
```json
{
  "word": "string",
  "sentence": "string",
  "language": "string"
}
```

**Response** (200):
```json
{
  "lemma": "string",
  "definition": "string",
  "related_words": ["string"],
  "pos": "noun|verb|adjective|adverb|etc",
  "gender": "der|die|das|le|la|el|la (null if not applicable)",
  "conjugations": {
    "present": "string",
    "past": "string",
    "perfect": "string"
  },
  "level": "A1|A2|B1|B2|C1|C2"
}
```

**Field Descriptions**:
- `lemma`: Dictionary form of the word
- `definition`: Context-aware definition
- `related_words`: All words in sentence belonging to this lemma (e.g., for separable verbs)
- `pos`: Part of speech (noun, verb, adjective, adverb, preposition, etc.)
- `gender`: Grammatical gender for nouns in gendered languages (German: der/die/das, French: le/la, Spanish: el/la)
- `conjugations`: Verb conjugations (present, past, perfect forms). Null for non-verbs.
- `level`: CEFR difficulty level (A1-C2)

---

#### POST /dictionary/vocabulary

**Description**: Add a word to vocabulary list with grammatical metadata.

**Auth**: Required (JWT)

**Request**:
```json
{
  "article_id": "uuid",
  "word": "string",
  "lemma": "string",
  "definition": "string",
  "sentence": "string",
  "language": "string",
  "related_words": ["string"],
  "span_id": "string",
  "pos": "noun|verb|adjective|etc",
  "gender": "der|die|das|le|la|el|la",
  "conjugations": {
    "present": "string",
    "past": "string",
    "perfect": "string"
  },
  "level": "A1|A2|B1|B2|C1|C2"
}
```

**Response** (200):
```json
{
  "id": "uuid",
  "article_id": "uuid",
  "word": "string",
  "lemma": "string",
  "definition": "string",
  "sentence": "string",
  "language": "string",
  "related_words": ["string"],
  "span_id": "string",
  "created_at": "2025-01-28T12:34:56+00:00",
  "user_id": "uuid",
  "pos": "noun|verb|adjective|etc",
  "gender": "der|die|das|le|la|el|la",
  "conjugations": {
    "present": "string",
    "past": "string",
    "perfect": "string"
  },
  "level": "A1|A2|B1|B2|C1|C2"
}
```

---

#### GET /dictionary/vocabularies

**Description**: Get aggregated vocabulary list grouped by lemma with counts and grammatical metadata.

**Auth**: Required (JWT) - Returns only vocabularies owned by authenticated user

**Query Parameters**:
- `language` (string, optional): Filter by language
- `skip` (integer, default: 0): Number of entries to skip (for pagination)
- `limit` (integer, default: 100, max: 1000): Maximum entries to return

**Response** (200):
```json
[
  {
    "id": "uuid",
    "article_id": "uuid",
    "word": "string",
    "lemma": "string",
    "definition": "string",
    "sentence": "string",
    "language": "string",
    "related_words": ["string"],
    "span_id": "string",
    "created_at": "2025-01-28T12:34:56+00:00",
    "user_id": "uuid",
    "count": 5,
    "article_ids": ["uuid1", "uuid2", "uuid3"],
    "pos": "noun|verb|adjective|etc",
    "gender": "der|die|das|le|la|el|la",
    "conjugations": {
      "present": "string",
      "past": "string",
      "perfect": "string"
    },
    "level": "A1|A2|B1|B2|C1|C2"
  }
]
```

**Note**: All grammatical metadata fields (`pos`, `gender`, `conjugations`, `level`) are from the most recent vocabulary entry for each lemma.

---

#### DELETE /dictionary/vocabularies/{vocabulary_id}

**Description**: Delete a vocabulary word.

**Auth**: Required (JWT) - Users can only delete their own vocabulary

**Response** (200):
```json
{
  "message": "Vocabulary deleted successfully"
}
```

---

## Next.js API Routes

### Summary
- Total routes: 10

- **GET** `/api/articles`
  - File: `src/web/app/api/articles/route.ts`
- **GET** `/api/status`
  - File: `src/web/app/api/status/route.ts`
- **POST** `/api/generate`
  - File: `src/web/app/api/generate/route.ts`
- **GET** `/api/article`
  - File: `src/web/app/api/article/route.ts`
- **GET** `/api/stats`
  - File: `src/web/app/api/stats/route.ts`
- **GET** `/api/articles/[id]`
  - File: `src/web/app/api/articles/[id]/route.ts`
- **POST** `/api/dictionary/search`
  - File: `src/web/app/api/dictionary/search/route.ts`
- **POST** `/api/dictionary/vocabularies`
  - File: `src/web/app/api/dictionary/vocabularies/route.ts`
- **GET** `/api/dictionary/vocabularies`
  - File: `src/web/app/api/dictionary/vocabularies/route.ts`
- **DELETE** `/api/dictionary/vocabularies/[id]`
  - File: `src/web/app/api/dictionary/vocabularies/[id]/route.ts`
- **GET** `/api/dictionary/stats`
  - File: `src/web/app/api/dictionary/stats/route.ts`

---

## API Models

### Conjugations Model

**File**: `src/api/models.py:12-21`

**Purpose**: Store verb conjugation forms across tenses (present, past, perfect).

**Fields**:
```python
class Conjugations(BaseModel):
    present: Optional[str] = None
    past: Optional[str] = None
    perfect: Optional[str] = None
```

**Special Method - `__bool__()`**:
```python
def __bool__(self) -> bool:
    """Return False if all fields are None."""
    return any(v is not None for v in (self.present, self.past, self.perfect))
```

**Behavior**:
- Returns `True` if at least one conjugation field has a value
- Returns `False` if all fields are None (empty conjugations)
- Enables truthiness checking: `if conjugations:` instead of explicit null checks

**Usage Example**:
```python
# Create conjugations
conjugations = Conjugations(present="geht", past="ging", perfect="ist gegangen")
if conjugations:  # True - has values
    print("Has conjugations")

# Empty conjugations
empty = Conjugations()
if empty:  # False - all None
    print("This won't print")

# Used in field validator
if isinstance(v, Conjugations):
    return v.model_dump() if v else None  # Returns None for empty
```

**Benefits**:
- Simplifies validation logic throughout codebase
- Prevents storing empty conjugation objects in database
- More Pythonic: `if conjugations:` vs `if conjugations.present or conjugations.past or conjugations.perfect:`

---

### VocabularyRequest Model

**File**: `src/api/models.py:91-117`

**Purpose**: Request model for adding vocabulary with automatic type conversion.

**Field Validator - `convert_conjugations()`**:
```python
@field_validator('conjugations', mode='before')
@classmethod
def convert_conjugations(cls, v):
    """Convert Conjugations to dict, return None if empty."""
    if v is None:
        return None
    if isinstance(v, Conjugations):
        return v.model_dump() if v else None  # Uses __bool__
    if isinstance(v, dict):
        return v if any(v.values()) else None
    return v
```

**Behavior**:
- Runs before Pydantic validation (`mode='before'`)
- Converts Conjugations model to dict for MongoDB storage
- Returns None if conjugations object is empty (using `__bool__` check)
- Handles both dict and Conjugations input types
- Prevents storing empty conjugation objects: `{"present": null, "past": null, "perfect": null}` becomes `null`

**Flow**:
1. Frontend sends conjugations as dict: `{"present": "geht", "past": null, "perfect": null}`
2. Validator checks if any values exist: `any(v.values())`
3. Returns dict if has values, None if all null
4. Prevents empty objects in MongoDB

**Benefits**:
- Automatic conversion from model to dict
- No need for explicit null checks in route handlers
- Database stores `null` instead of empty objects
- Cleaner MongoDB documents

**Example**:
```python
# Request with conjugations
request = VocabularyRequest(
    conjugations={"present": "geht", "past": "ging", "perfect": None}
)
# Stored as: {"present": "geht", "past": "ging"}

# Request with empty conjugations
request = VocabularyRequest(
    conjugations={"present": None, "past": None, "perfect": None}
)
# Stored as: null (not an empty object)
```

---

## Testing

### Web Testing with Vitest

**Configuration File**: `src/web/vitest.config.ts`

**Framework**: Vitest 4.0.18 with jsdom environment

**Test Setup**:
- Environment: jsdom for DOM simulation
- Globals: Enabled for test functions (describe, it, expect)
- Test pattern: `**/__tests__/**/*.test.ts` and `**/__tests__/**/*.test.tsx`

**Dependencies**:
- `vitest@4.0.18` - Test framework (ESM-native, fast)
- `@vitest/ui@4.0.18` - Interactive test UI
- `jsdom@27.4.0` - DOM simulation for Node.js
- `@testing-library/react@16.3.2` - React component testing utilities
- `@testing-library/jest-dom@6.9.1` - DOM assertion matchers

**Coverage Configuration**:
- Provider: v8 (Node.js native coverage)
- Reporters: text, json, html
- Thresholds: 80% for lines, functions, branches, statements
- Excludes: node_modules, test files (`**/*.test.ts`, `**/*.test.tsx`), test directories

**Path Aliases**:
- `@` resolves to `src/web/` (matches Next.js tsconfig)

**Available Commands** (`package.json`):
```bash
# Run all tests once
npm test

# Watch mode for development
npm run test:watch

# Interactive UI for test exploration
npm run test:ui
```

**Current Test Coverage**:
- `hooks/__tests__/usePagination.test.ts` - Pagination logic tests
- `hooks/__tests__/useStatusPolling.test.ts` - Job polling tests
- `lib/__tests__/api.test.ts` - API client tests
- `lib/__tests__/formatters.test.ts` - Date formatting tests
- `lib/__tests__/styleHelpers.test.ts` - CEFR styling tests

**Example Test File Structure**:
```typescript
import { describe, it, expect } from 'vitest'
import { formatDate } from '@/lib/formatters'

describe('formatDate', () => {
  it('should format ISO date string correctly', () => {
    const result = formatDate('2024-01-29T12:30:00Z')
    expect(result).toMatch(/January 29, 2024/)
  })
})
```

**Benefits**:
- Fast test execution with Vitest's ESM-native architecture
- Interactive UI for debugging failing tests
- Coverage reporting for quality assurance
- Type-safe testing with full TypeScript support
- Compatible with React Testing Library ecosystem

---

## Frontend Utilities & Hooks

### API Client Utilities (`lib/api.ts`)

#### fetchWithAuth()

Fetch wrapper that automatically adds JWT Authorization header from localStorage.

**Usage**:
```typescript
import { fetchWithAuth } from '@/lib/api'

const response = await fetchWithAuth('/api/articles', {
  method: 'GET'
})
```

**Features**:
- Automatically retrieves token from localStorage via `getToken()`
- Adds `Authorization: Bearer <token>` header if token exists
- Compatible with standard fetch API

---

#### parseErrorResponse()

Parse error message from API response in a consistent way.

**Parameters**:
- `response` (Response): Fetch Response object
- `defaultMessage` (string, default: 'An error occurred'): Fallback message

**Returns**: Promise resolving to error message string

**Usage**:
```typescript
import { parseErrorResponse } from '@/lib/api'

const response = await fetch('/api/endpoint')
if (!response.ok) {
  const errorMsg = await parseErrorResponse(response, 'Failed to fetch data')
  throw new Error(errorMsg)
}
```

**Error Extraction Order**:
1. `error` field from response JSON
2. `detail` field from response JSON
3. `message` field from response JSON
4. Falls back to `defaultMessage`

---

### Date Formatting Utilities (`lib/formatters.ts`)

#### formatDate()

Format a date string using Intl.DateTimeFormat with customizable options.

**Parameters**:
- `dateString` (string): ISO date string to format
- `locale` (string, default: 'en-US'): Locale string
- `options` (Intl.DateTimeFormatOptions, default: long format with time): Formatting options

**Returns**: Formatted date string, or original string if parsing fails

**Usage**:
```typescript
import { formatDate } from '@/lib/formatters'

formatDate('2024-01-29T12:30:00Z')
// => "January 29, 2024, 12:30 PM"

formatDate('2024-01-29T12:30:00Z', 'en-US', { month: 'short' })
// => "Jan 29, 2024, 12:30 PM"
```

---

#### formatDateShort()

Format a date string to short format (e.g., "Jan 29, 2024").

**Parameters**:
- `dateString` (string): ISO date string to format

**Returns**: Short formatted date string

**Usage**:
```typescript
import { formatDateShort } from '@/lib/formatters'

formatDateShort('2024-01-29T12:30:00Z')
// => "Jan 29, 2024"
```

---

#### formatDateTime()

Format a date string to include time (e.g., "Jan 29, 2024, 12:30 PM").

**Parameters**:
- `dateString` (string): ISO date string to format

**Returns**: Formatted date string with time

**Usage**:
```typescript
import { formatDateTime } from '@/lib/formatters'

formatDateTime('2024-01-29T12:30:00Z')
// => "Jan 29, 2024, 12:30 PM"
```

---

### Style Utilities (`lib/styleHelpers.ts`)

#### getLevelColor()

Get Tailwind CSS classes for CEFR level badge.

**Parameters**:
- `level` (string, optional): CEFR level string (e.g., 'A1', 'B2', 'C1')

**Returns**: Tailwind CSS class string for background and text color

**Color Scheme**:
- A levels (A1, A2): Green (beginner)
- B levels (B1, B2): Yellow (intermediate)
- C levels (C1, C2): Red (advanced)
- No level: Gray (unknown)

**Usage**:
```typescript
import { getLevelColor } from '@/lib/styleHelpers'

getLevelColor('A1')  // => 'bg-green-100 text-green-700'
getLevelColor('B2')  // => 'bg-yellow-100 text-yellow-700'
getLevelColor('C1')  // => 'bg-red-100 text-red-700'
getLevelColor()      // => 'bg-gray-100 text-gray-600'
```

**Note**: These classes are safelisted in `tailwind.config.ts` to prevent purging by Tailwind's tree-shaking.

---

#### getLevelLabel()

Get a descriptive label for CEFR level.

**Parameters**:
- `level` (string, optional): CEFR level string

**Returns**: Human-readable level description

**Usage**:
```typescript
import { getLevelLabel } from '@/lib/styleHelpers'

getLevelLabel('A1')  // => 'Beginner'
getLevelLabel('B2')  // => 'Intermediate'
getLevelLabel('C1')  // => 'Advanced'
getLevelLabel()      // => 'Unknown'
```

---

### Custom Hooks

#### useAsyncFetch

Generic hook for async data fetching with loading/error/data state management.

**Type Parameters**:
- `T`: Expected data type

**Returns**:
```typescript
{
  data: T | null           // Fetched data
  loading: boolean         // Loading state
  error: string | null     // Error message
  fetch: (url: string, options?: RequestInit) => Promise<void>
  setData: (data: T | null) => void
  setError: (error: string | null) => void
}
```

**Features**:
- Automatic loading state management
- Error handling with message extraction
- Automatic 401 redirect to login page
- Type-safe data state

**Usage**:
```typescript
import { useAsyncFetch } from '@/hooks/useAsyncFetch'

function ArticleList() {
  const { data, loading, error, fetch } = useAsyncFetch<Article[]>()

  useEffect(() => {
    fetch('/api/articles')
  }, [fetch])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  return <div>{data?.map(article => ...)}</div>
}
```

---

#### usePagination

Hook for pagination calculations and state management.

**Parameters**:
```typescript
{
  total: number   // Total number of items
  limit: number   // Items per page
  skip: number    // Current offset
}
```

**Returns**:
```typescript
{
  currentPage: number          // Current page (1-indexed)
  totalPages: number           // Total number of pages
  hasNextPage: boolean         // Whether next page exists
  hasPrevPage: boolean         // Whether previous page exists
  nextSkip: number             // Skip value for next page
  prevSkip: number             // Skip value for previous page
  getSkipForPage: (page: number) => number  // Get skip for specific page
}
```

**Usage**:
```typescript
import { usePagination } from '@/hooks/usePagination'

function PaginatedList() {
  const [skip, setSkip] = useState(0)
  const limit = 10
  const total = 100

  const {
    currentPage,
    totalPages,
    hasNextPage,
    hasPrevPage,
    nextSkip,
    prevSkip
  } = usePagination({ total, limit, skip })

  return (
    <div>
      <p>Page {currentPage} of {totalPages}</p>
      <button
        disabled={!hasPrevPage}
        onClick={() => setSkip(prevSkip)}
      >
        Previous
      </button>
      <button
        disabled={!hasNextPage}
        onClick={() => setSkip(nextSkip)}
      >
        Next
      </button>
    </div>
  )
}
```

---

#### useStatusPolling

Hook for polling job status with automatic interval management.

**Parameters**:
```typescript
{
  jobId: string | null           // Job ID to poll for status
  enabled: boolean               // Whether polling is enabled
  onComplete?: () => void        // Callback when job completes
  onError?: () => void           // Callback when job fails
  interval?: number              // Polling interval in ms (default: 5000)
}
```

**Returns**:
```typescript
{
  progress: {
    current_task: string
    progress: number
    message: string
    error: string | null
  }
  isPolling: boolean
}
```

**Features**:
- Automatic polling at 5-second intervals (configurable)
- Progress state management
- Automatic cleanup on completion/error
- Callbacks for status changes
- Prevents unnecessary re-renders with state comparison

**Usage**:
```typescript
import { useStatusPolling } from '@/hooks/useStatusPolling'

function ArticleDetail() {
  const { progress, isPolling } = useStatusPolling({
    jobId: article?.job_id || null,
    enabled: article?.status === 'running',
    onComplete: () => {
      // Reload article data
      fetchArticle()
    },
    onError: () => {
      console.error('Job failed')
    }
  })

  if (isPolling) {
    return (
      <div>
        <p>{progress.current_task}</p>
        <progress value={progress.progress} max={100} />
      </div>
    )
  }

  return <div>Article content...</div>
}
```

---

#### useVocabularyDelete

Custom hook for deleting vocabulary entries.

**Returns**:
```typescript
{
  deleteVocabulary: (vocabId: string) => Promise<void>
}
```

**Features**:
- Makes DELETE request to vocabulary API
- Handles error responses with detailed messages
- Throws errors for the caller to handle (e.g., update UI state)

**Usage**:
```typescript
import { useVocabularyDelete } from '@/hooks/useVocabularyDelete'

function VocabularyList() {
  const [vocabularies, setVocabularies] = useState<Vocabulary[]>([])
  const [error, setError] = useState<string | null>(null)
  const { deleteVocabulary } = useVocabularyDelete()

  const handleDelete = async (vocabId: string) => {
    try {
      await deleteVocabulary(vocabId)
      // Update local state on success
      setVocabularies(prev => prev.filter(v => v.id !== vocabId))
    } catch (error: any) {
      // Handle error in UI
      setError(error.message)
    }
  }

  return (
    <div>
      {vocabularies.map(vocab => (
        <button onClick={() => handleDelete(vocab.id)}>Delete</button>
      ))}
    </div>
  )
}
```

---

### Reusable Components

#### ErrorAlert

Reusable error alert component for displaying error messages.

**File**: `src/web/components/ErrorAlert.tsx`

**Props**:
```typescript
{
  error: string | null      // Error message to display (null hides component)
  onRetry?: () => void      // Optional retry button handler
  className?: string        // Additional CSS classes
}
```

**Styling**:
- Light red background with border: `bg-red-50 border border-red-200`
- Rounded corners with padding: `rounded-lg p-4`
- Error text: Dark red (`text-red-800`)
- Retry button: Red text with underline and hover effect
- Bottom margin: `mb-6` (can be overridden)

**Features**:
- Consistent error styling (red background with border)
- Optional retry button for recoverable errors
- Automatic hiding when error is null
- Accessible error messaging with proper color contrast

**Behavior**:
- Returns `null` when `error` prop is null/undefined
- Renders retry button only if `onRetry` callback is provided
- Button styled with underline and hover effect for clear affordance

**Usage**:
```typescript
import ErrorAlert from '@/components/ErrorAlert'

function MyComponent() {
  const [error, setError] = useState<string | null>(null)

  return (
    <div>
      <ErrorAlert
        error={error}
        onRetry={() => {
          setError(null)
          fetchData()
        }}
      />
    </div>
  )
}
```

**Used In**:
- `src/web/app/vocabulary/page.tsx` - Vocabulary fetch errors
- Other pages with error states requiring user feedback

---

### MarkdownViewer Component

**File**: `src/web/components/MarkdownViewer.tsx`

**Component Remounting Pattern**:

To prevent React hydration mismatches when article content changes, MarkdownViewer uses a key prop pattern that forces component remount on content changes.

**Pattern** (from `src/web/app/articles/[id]/page.tsx:266`):
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

**Why This Matters**:
- When article content changes (e.g., after generation completes), React must fully remount the component
- Without key prop: React attempts to reuse DOM nodes, causing hydration mismatches
- Key pattern `${articleId}-${content.length}` ensures unique key per content state
- Component remount triggers `data-processed` reset (line 456), allowing word-clickable logic to re-run

**Processing State Check** (`src/web/components/MarkdownViewer.tsx:456-458`):
```typescript
// Skip if already processed (component remounts on content change via key prop)
if (containerRef.current.getAttribute('data-processed') === 'true') {
  return
}
```

**Benefits**:
- Prevents React DOM mismatch errors
- Ensures clean state on content changes
- Avoids stale event listeners from previous content
- Simplifies component lifecycle (no complex update logic needed)

**Alternative Approaches (Why Not Used)**:
- Manual DOM cleanup: Error-prone, complex to maintain
- useEffect dependency on content: Can cause double-processing
- Force update: Doesn't guarantee full DOM reset

---

### MarkdownViewer Security

**File**: `src/web/components/MarkdownViewer.tsx`

**XSS Prevention Measures**:

#### 1. HTML Escaping Utility (lines 92-96)

```typescript
const escapeHtml = (text: string): string => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}
```

**Purpose**: Convert user-provided text to HTML-safe string
**Mechanism**: Browser's HTML encoder via textContent → innerHTML
**Applied To**: All vocabulary data (word, lemma, definition, sentence, pos, gender, level)

#### 2. DOM API Methods Instead of innerHTML (lines 663-713)

**Before (Vulnerable)**:
```typescript
defSpan.innerHTML = `<strong>${lemma}</strong>: ${meaning} ${buttonHtml}`
```

**After (Secure)**:
```typescript
const strong = document.createElement('strong')
strong.textContent = displayLemma  // Safe: textContent escapes HTML
defSpan.appendChild(strong)
defSpan.appendChild(document.createTextNode(': ' + meaning))

// Parse button HTML in controlled way
const tempDiv = document.createElement('div')
tempDiv.innerHTML = buttonHtml.trim()
const button = tempDiv.firstElementChild
if (button) {
  defSpan.appendChild(button)
}
```

**Security Benefits**:
- `textContent` automatically escapes HTML entities
- No script execution from user data
- Button HTML parsed in isolated container
- Element extraction via `firstElementChild` (not `innerHTML`)

#### 3. Data Attribute Escaping (lines 112-131)

```typescript
const wordEscaped = escapeHtml(word)
const lemmaEscaped = escapeHtml(lemma)
const definitionEscaped = escapeHtml(definition)
const relatedWordsStr = relatedWords ? JSON.stringify(relatedWords).replace(/"/g, '&quot;') : ''
const sentenceEscaped = escapeHtml(sentence).replace(/"/g, '&quot;')

const buttonHtml = `<button data-word="${wordEscaped}" data-lemma="${lemmaEscaped}" ...>`
```

**Protection**:
- All data attributes HTML-escaped before embedding
- JSON strings escaped with `replace(/"/g, '&quot;')` for attribute safety
- Prevents attribute injection: `word="hello" onclick="alert('xss')"`

#### 4. Event Delegation (lines 514-534)

**Before (Vulnerable to Stale Closures)**:
```typescript
// Inline event handlers - stale state
wordSpan.addEventListener('click', () => {
  handleWordClick(spanId, word)  // May use outdated state
})
```

**After (Secure & Performance)**:
```typescript
// Single event listener on container
containerRef.current.addEventListener('click', (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (target.classList.contains('vocab-word') && target.classList.contains('user-clickable')) {
    const spanId = target.getAttribute('data-span-id')
    const word = target.getAttribute('data-word')
    if (spanId && word) {
      handleWordClickRef.current(spanId, word)  // Always current ref
    }
  }
})

// Ref-based callback storage (lines 446-449)
const handleWordClickRef = useRef(handleWordClick)
useEffect(() => {
  handleWordClickRef.current = handleWordClick
}, [handleWordClick])
```

**Security Benefits**:
- Ref-based callback prevents stale closures
- Single listener reduces attack surface
- Data read from attributes (already escaped)
- No inline handlers (`onclick`) that could be injected

#### Attack Scenarios Prevented

**Scenario 1: Script Injection in Definition**
```typescript
// Malicious definition from API
definition: "<script>alert('XSS')</script>"

// Old code (vulnerable)
innerHTML = `<strong>${lemma}</strong>: ${definition}`
// Result: Script executes!

// New code (safe)
textContent = definition
// Result: "<script>alert('XSS')</script>" displayed as text
```

**Scenario 2: Attribute Injection**
```typescript
// Malicious word from API
word: 'hello" onclick="alert(\'xss\')'

// Old code (vulnerable)
innerHTML = `<span data-word="${word}">...</span>`
// Result: <span data-word="hello" onclick="alert('xss')">...</span>

// New code (safe)
const wordEscaped = escapeHtml(word)  // "hello&quot; onclick=&quot;alert('xss')&quot;"
innerHTML = `<span data-word="${wordEscaped}">...</span>`
// Result: onclick stored as text, not executed
```

**Scenario 3: Event Handler Injection**
```typescript
// Malicious lemma from API
lemma: "test<img src=x onerror=alert('XSS')>"

// Old code (vulnerable)
innerHTML = `<strong>${lemma}</strong>`
// Result: Image loads, onerror executes

// New code (safe)
strong.textContent = lemma
// Result: All HTML rendered as text
```

**Impact**: Prevents DOM-based XSS attacks, protects against script execution from vocabulary data.

---

#### EmptyState

Reusable empty state component for displaying when no data is available.

**File**: `src/web/components/EmptyState.tsx`

**Props**:
```typescript
{
  title: string              // Main title
  description: string        // Description text
  icon?: string              // Optional emoji/icon
  action?: {                 // Optional action button
    label: string
    onClick: () => void
  }
  className?: string         // Additional CSS classes
}
```

**Styling**:
- White card with rounded corners and shadow: `bg-white rounded-lg shadow-lg`
- Centered text layout with padding: `p-8 text-center`
- Icon: 4xl font size with bottom margin
- Title: Gray-500 large text
- Description: Gray-400 regular text
- Action button: Blue button with hover effect

**Features**:
- Consistent empty state styling across all pages
- Optional action button for primary CTA
- Centered layout with icon support
- Flexible with additional className prop

**Usage**:
```typescript
import EmptyState from '@/components/EmptyState'

function ArticleList() {
  if (articles.length === 0) {
    return (
      <EmptyState
        title="No articles yet"
        description="Generate your first article to get started"
        icon="📚"
        action={{
          label: "Generate Article",
          onClick: () => router.push('/')
        }}
      />
    )
  }

  return <div>{articles.map(...)}</div>
}
```

**Used In**:
- `src/web/app/vocabulary/page.tsx` - No vocabulary state
- Other list pages when data is empty

---
