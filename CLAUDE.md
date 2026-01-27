# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

OPAD (One Paragraph A Day) is an AI-powered system that transforms news articles into personalized educational reading materials for language learners using CrewAI.

## Agent Pipeline

**For Advisory/Questioning Intent:**
```
code-suggester (model: sonnet)
    ↓ Analyzes and suggests improvements
    ↓ When ready to implement → code-modifier
```

**For Direct Code Modification Commands:**
```
code-modifier (model: opus)
    ↓ Modifies code directly
code-reviewer (model: opus)
    ↓ Reviews for quality, security, performance
unittest-agent (model: sonnet)
    ↓ Creates test files (test_{filename}.py)
qa-agent (model: haiku)
    ↓ Runs tests and validates quality
```

See `.claude/agents/` for detailed agent instructions.

## Commands

### Running Services (Local Development)

Start dependencies first:
```bash
docker-compose -f docker-compose.local.yml up -d  # MongoDB + Redis
```

Run in 3 separate terminals:
```bash
# API (FastAPI) - port 8001
PYTHONPATH=src uvicorn api.main:app --reload --port 8001

# Worker (CrewAI processor)
PYTHONPATH=src uv run python -m worker.main

# Web (Next.js) - port 8000
cd src/web && API_BASE_URL=http://localhost:8001 npm run dev
```

### Testing

```bash
# Python tests
uv run pytest src/api/tests/ -v
uv run pytest src/worker/tests/ -v

# With coverage
uv run pytest --cov=src --cov-report=term-missing
```

### Python Commands

Always use `uv run` for Python commands, never `python3` or `python`.

## Architecture

**3-Service Microservices:**
- **Web** (Next.js, port 8000): UI + API proxies
- **API** (FastAPI, port 8001): REST endpoints, job queue management
- **Worker** (Python): Polls Redis queue, runs CrewAI, saves to MongoDB

**Data Flow:**
1. Web → API: HTTP request
2. API → Redis: RPUSH job to queue
3. Worker → Redis: BLPOP from queue
4. Worker → CrewAI: Process article (2-5 minutes)
5. Worker → MongoDB: Save content, update status
6. Web: Poll `/jobs/{job_id}` for status

**Data Storage:**
- MongoDB: `articles`, `vocabularies`, `users` collections
- Redis: Job queue (`opad:jobs`), job status (`opad:job:{id}`)
