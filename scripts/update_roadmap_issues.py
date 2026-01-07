#!/usr/bin/env python3
"""
Update GitHub roadmap issues with richer English descriptions.

Why a script?
- The current auth allows editing issue body/milestone, but label mutations may be restricted.
- This keeps the roadmap text consistent and reproducible.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Dict


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )


def body(text: str) -> str:
    # Normalize trailing whitespace and ensure final newline.
    return "\n".join(line.rstrip() for line in text.strip().splitlines()) + "\n"


REPO = "seung-gu/opad"

ISSUES: Dict[int, str] = {
    7: body(
        """
## Goal
Split the deployment into **three Railway services**: `web` (Next.js), `api` (FastAPI), `worker` (queue consumer). Each service runs a single role/process and can scale independently.

## Context
Today the web container starts Next.js and spawns Python for CrewAI in-process. This couples latency, resource usage, and failure domains.

## Scope
- Create/confirm 3 Railway services that build from the same repo.
- Define clear responsibility boundaries:
  - `web`: UI + calls `api` (no python spawning)
  - `api`: CRUD + job enqueue + status/result
  - `worker`: runs CrewAI jobs and writes results

## Non-goals
- Full production observability stack.
- Streaming/SSE (can be later).

## Acceptance criteria
- Three services exist and are deployable independently.
- Web requests still work even when worker is down (jobs may queue, but UI/API remain responsive).
- No CrewAI execution happens inside the web service.

## Suggested labels
devops, backend, worker, roadmap

## References
- DEVLOG.md (2026-01-07)
"""
    ),
    8: body(
        """
## Goal
Provision **Postgres** (persistent state) and **Redis** (job queue) on Railway, and wire env vars into `api` and `worker`.

## Scope
- Add Railway Postgres and Redis add-ons.
- Configure environment variables:
  - `DATABASE_URL` -> `api`, `worker`
  - `REDIS_URL` -> `api`, `worker`
  - `API_BASE_URL` (api public/internal URL) -> `web`
  - `R2_*`, `OPENAI_API_KEY`, `SERPER_API_KEY` as needed

## Acceptance criteria
- `api` can connect to Postgres and run migrations.
- `api` can enqueue a job into Redis.
- `worker` can dequeue jobs from Redis.

## Suggested labels
devops, backend, roadmap
"""
    ),
    9: body(
        """
## Goal
Define a clean build/run strategy for **web/api/worker** with Docker on Railway.

## Recommended approach
Use **role-specific Dockerfiles** for clarity:
- `Dockerfile.web` -> Next.js runtime
- `Dockerfile.api` -> FastAPI runtime
- `Dockerfile.worker` -> Worker runtime

Alternative: single image + role-specific start commands, but this usually becomes harder to reason about.

## Scope
- Decide and implement one approach.
- Ensure each service runs exactly one role/process.
- Make sure the repo build is reproducible.

## Acceptance criteria
- Railway can build/deploy each service without manual hacks.
- `web` image does not need python runtime (optional optimization).
- `worker` image includes CrewAI deps and can run jobs.

## Suggested labels
devops, roadmap
"""
    ),
    10: body(
        """
## Goal
Add minimal operational endpoints and structured logs for the `api` service.

## Scope
- Implement `GET /health` returning 200 + basic status.
- Add structured logging (JSON preferred) including `jobId`, `articleId` where relevant.
- Ensure logs go to stdout (Railway-friendly).

## Acceptance criteria
- `GET /health` is stable and fast.
- Key workflow logs can be correlated per job (enqueue/start/finish/fail).

## Suggested labels
backend, devops, roadmap
"""
    ),
    11: body(
        """
## Goal
Design and implement DB schema for multi-article + job-based generation.

## Context
Current system effectively stores a single “latest” article (fixed R2 key), which blocks multi-page/collection features.

## Scope
- Tables:
  - `articles`: id, owner_id(optional), url/topic/inputs, status, created_at, updated_at, result_ref
  - `jobs`: id, article_id, status(queued/running/succeeded/failed), progress, params_hash, error, started_at, finished_at
- Add indexes for typical queries (latest articles, jobs by status, jobs by article).

## Acceptance criteria
- Schema supports multiple articles simultaneously.
- Schema supports multiple jobs over time (history) without races.

## Suggested labels
backend, roadmap
"""
    ),
    12: body(
        """
## Goal
Implement stable API contracts for articles and jobs.

## Endpoints (proposed)
- `POST /articles` -> create article (or save inputs/url)
- `GET /articles` -> list (filter by status, sort)
- `GET /articles/{id}` -> detail (includes result refs)
- `POST /articles/{id}/generate` -> create job, return `{ jobId }` immediately
- `GET /jobs/{jobId}` -> `{ status, progress, articleId, resultRef, error }`

## Notes
- Keep responses JSON and versionable.
- Prefer “store result then fetch” rather than long-running request waiting.

## Acceptance criteria
- Web can implement pages using only these endpoints.
- Generate returns quickly even if CrewAI takes minutes.

## Suggested labels
backend, roadmap
"""
    ),
    13: body(
        """
## Goal
Change R2 storage layout to support **many articles**, not just “latest one”.

## Proposed key layout
- `articles/{articleId}/adapted.md`
- `articles/{articleId}/meta.json` (inputs, language/level/length, source attribution, etc.)

## Scope
- Update upload logic so keys are per-article.
- Update read logic so web loads by `articleId` (via api).

## Acceptance criteria
- Creating a new article does not overwrite previous ones.
- `GET /articles/{id}` can point to the correct R2 objects.

## Suggested labels
backend, ai, roadmap
"""
    ),
    14: body(
        """
## Goal
Remove the shared `input.json` file dependency to avoid race conditions under concurrency.

## Context
Today `/api/generate` writes `input.json` then spawns python. Two generate clicks can overwrite each other.

## Scope
- Refactor CrewAI entrypoint to accept an `inputs` dict per job (no shared file).
- Store inputs in DB (or pass via queue payload).

## Acceptance criteria
- Multiple jobs can run concurrently without contaminating inputs.
- Worker can run jobs purely from queue payload + DB state.

## Suggested labels
backend, ai, roadmap
"""
    ),
    15: body(
        """
## Goal
Add idempotency for generate requests to prevent duplicate jobs and cost spikes.

## Proposed rule
For the same `(articleId, params_hash)`:
- If there is a `queued`/`running` job, return that `jobId` instead of creating a new one.
- Optionally keep history for `succeeded/failed` jobs.

## Implementation hints
- Compute `params_hash` from normalized inputs (language/level/length/topic + prompt_version).
- Enforce uniqueness with DB constraint or transaction.

## Acceptance criteria
- Repeated clicking “Generate” does not create N jobs.
- System remains stable under retry/refresh.

## Suggested labels
backend, roadmap
"""
    ),
    16: body(
        """
## Goal
Create a dedicated article list page: `/articles`.

## Scope
- Show latest articles (title/topic, status, created time).
- Basic filtering (status) and sorting (latest first).
- Link to `/articles/[id]`.

## Acceptance criteria
- Page renders using `api` list endpoint.
- Works even when some jobs are still processing.

## Suggested labels
frontend, roadmap
"""
    ),
    17: body(
        """
## Goal
Create article detail page: `/articles/[id]`.

## Scope
- Show article inputs/metadata.
- Show generated markdown when available.
- Provide “Generate” button that calls `POST /articles/{id}/generate`.
- On generate, navigate to `/jobs/[jobId]`.

## Acceptance criteria
- Works for both “not generated yet” and “already generated” cases.

## Suggested labels
frontend, roadmap
"""
    ),
    18: body(
        """
## Goal
Create job status page: `/jobs/[jobId]` with polling and completion flow.

## Scope
- Poll `GET /jobs/{jobId}` (e.g., every 2–5s).
- Display: queued/running progress, failed error, succeeded link/redirect to article.
- Stop polling when terminal state is reached.

## Acceptance criteria
- User sees progress feedback and does not need manual refresh.
- On success, user ends up on `/articles/[id]` showing the result.

## Suggested labels
frontend, roadmap
"""
    ),
    19: body(
        """
## Goal
Decouple web from local python execution. Web should call the `api` service only.

## Scope
- Remove/stop using Next API routes that spawn python (`/web/app/api/generate`).
- Replace with API calls:
  - create article
  - generate job (returns jobId)
  - poll job status
  - fetch article result

## Acceptance criteria
- Web service can run without python deps.
- All generation happens via `worker` only.

## Suggested labels
frontend, backend, devops, roadmap
"""
    ),
    20: body(
        """
## Goal
Implement the worker process that consumes generate jobs and runs CrewAI.

## Scope
- Dequeue jobs from Redis.
- Update job state in DB: `queued -> running -> succeeded/failed`.
- Run CrewAI pipeline using per-job inputs.
- Store outputs in R2 under per-article keys.
- Write `result_ref` back to DB.

## Acceptance criteria
- End-to-end: generate request creates job, worker completes it, web can display result.

## Suggested labels
worker, ai, roadmap
"""
    ),
    21: body(
        """
## Goal
Prevent overload and make failures recoverable with clear policies.

## Scope
- Concurrency limit per worker instance (e.g., 1–2 jobs at once).
- Retry/backoff for transient errors (network/LLM timeouts).
- No infinite retries; record failure reason.

## Acceptance criteria
- Under burst traffic, jobs queue instead of crashing services.
- Failures are visible and actionable (error recorded).

## Suggested labels
worker, devops, roadmap
"""
    ),
    22: body(
        """
## Goal
Make job execution debuggable: logs, timings, and failure reasons.

## Scope
- Structured logs for each step (extract -> summarize -> upload).
- Record timings and final error in DB.
- Optional: store partial progress / last step.

## Acceptance criteria
- Given a jobId, we can answer: where it is stuck, how long it took, why it failed.

## Suggested labels
worker, backend, devops, roadmap
"""
    ),
    23: body(
        """
## Goal
Update README to reflect the new 3-service Railway architecture and operations.

## Scope
- Document services: web/api/worker responsibilities.
- Required env vars per service.
- How to add Postgres/Redis on Railway.
- How to scale worker and troubleshoot common failures.

## Acceptance criteria
- A new contributor can deploy the system end-to-end using only the README.

## Suggested labels
docs, devops, roadmap
"""
    ),
    24: body(
        """
## Roadmap: 3-service split (web/api/worker)

This issue tracks the roadmap for splitting OPAD into three services:
- **web**: Next.js UI (calls api)
- **api**: CRUD + job control + queue enqueue
- **worker**: queue consumer + CrewAI execution

### Milestone M0: 3-service skeleton (Railway)
- [ ] https://github.com/seung-gu/opad/issues/7
- [ ] https://github.com/seung-gu/opad/issues/8
- [ ] https://github.com/seung-gu/opad/issues/9
- [ ] https://github.com/seung-gu/opad/issues/10

### Milestone M1: API+DB (Articles/Jobs) + R2 keys
- [ ] https://github.com/seung-gu/opad/issues/11
- [ ] https://github.com/seung-gu/opad/issues/12
- [ ] https://github.com/seung-gu/opad/issues/13
- [ ] https://github.com/seung-gu/opad/issues/14
- [ ] https://github.com/seung-gu/opad/issues/15

### Milestone M2: FE routing (Articles/Jobs pages)
- [ ] https://github.com/seung-gu/opad/issues/16
- [ ] https://github.com/seung-gu/opad/issues/17
- [ ] https://github.com/seung-gu/opad/issues/18
- [ ] https://github.com/seung-gu/opad/issues/19

### Milestone M3: Worker hardening (reliability/ops)
- [ ] https://github.com/seung-gu/opad/issues/20
- [ ] https://github.com/seung-gu/opad/issues/21
- [ ] https://github.com/seung-gu/opad/issues/22
- [ ] https://github.com/seung-gu/opad/issues/23

## Labeling guidance (manual)
Suggested labels to create/use: devops, backend, frontend, worker, ai, docs, roadmap.

## Reference
- DEVLOG.md (2026-01-07)
"""
    ),
}


def main() -> int:
    # Update bodies via `gh issue edit` (arg-safe, no shell quoting issues).
    for issue_number, issue_body in sorted(ISSUES.items(), key=lambda x: x[0]):
        run(["gh", "issue", "edit", str(issue_number), "--repo", REPO, "--body", issue_body])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

