# API Flow Diagrams

This document contains flow diagrams for key API endpoints and request flows.

*Run `python scripts/generate_docs.py` to auto-generate from code comments.*

---

## Article Generation Flow

### Complete Request/Response Flow

```mermaid
sequenceDiagram
    participant FE as Frontend (page.tsx)
    participant API as Next.js API (route.ts)
    participant BE as FastAPI (articles.py)
    FE->>API: POST /api/generate<br/>{language, level, length, topic, force}
    API->>BE: POST /articles/generate?force={force}
    alt force=false and duplicate exists
        BE->>BE: _check_duplicate() raises HTTPException(409)
        BE-->>API: 409 Conflict + existing_job
        API-->>FE: 409 + {duplicate: true, existing_job}
        FE->>FE: window.confirm("Generate new?")
        alt User clicks OK
            FE->>API: POST /api/generate (force=true)
            API->>BE: POST /articles/generate?force=true
            BE->>BE: Skip duplicate check (force=True)
            BE->>BE: Create article + job
            BE-->>API: 200 OK + {job_id, article_id}
            API-->>FE: 200 OK + {job_id, article_id}
        end
    else No duplicate or force=true
        BE->>BE: Create article + job
        BE-->>API: 200 OK + {job_id, article_id}
        API-->>FE: 200 OK + {job_id, article_id}
    end
```

**Files:**
- Frontend: `src/web/app/page.tsx`
- Next.js API: `src/web/app/api/generate/route.ts`
- FastAPI: `src/api/routes/articles.py`

---

## Duplicate Detection Flow

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

**File:** `src/api/routes/articles.py::_check_duplicate()`
