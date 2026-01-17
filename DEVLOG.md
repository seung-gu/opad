# DEVLOG

---

## Milestone M0 ✅

### Completed Issues

- ✅ [#7](https://github.com/seung-gu/opad/issues/7) - 3-Service Architecture Implementation *(2026-01-07)*
- ✅ [#9](https://github.com/seung-gu/opad/issues/9) - [M0] Service start commands + Dockerfile strategy *(2026-01-08)*
- ✅ [#8](https://github.com/seung-gu/opad/issues/8) - [M0] Add Postgres + Redis add-ons and wire env vars *(2026-01-09)*
- ✅ [#10](https://github.com/seung-gu/opad/issues/10) - [M0] Add /health endpoint and structured logs in api *(2026-01-10)*

---

## Milestone M1

### Completed Issues
- ✅ [#11](https://github.com/seung-gu/opad/issues/11) - [M1] DB schema: articles + jobs (user optional) *(2026-01-15)*
- ✅ [#12](https://github.com/seung-gu/opad/issues/12) - Article CRUD Operations *(2026-01-17)*

### In Progress / Planned
- [#14](https://github.com/seung-gu/opad/issues/14) - Remove input.json shared file (pass inputs per job)
- [#15](https://github.com/seung-gu/opad/issues/15) - Idempotency: dedupe generate requests

---

## Milestone M2

### Completed Issues
- ✅ [#16](https://github.com/seung-gu/opad/issues/16) - FE: /articles list page *(2026-01-17)*
- [#17](https://github.com/seung-gu/opad/issues/17) - FE: /articles/[id] detail page *(2026-01-17)*

### In Progress / Planned
- [#18](https://github.com/seung-gu/opad/issues/18) - FE: /jobs/[jobId] page (polling + redirect)
- [#19](https://github.com/seung-gu/opad/issues/19) - Web -> API integration (stop Next spawning python)

---

## Milestone M3

### In Progress / Planned
- [#20](https://github.com/seung-gu/opad/issues/20) - Worker: consume queue and run CrewAI generate job
- [#21](https://github.com/seung-gu/opad/issues/21) - Worker hardening: concurrency limit + retry/backoff
- [#22](https://github.com/seung-gu/opad/issues/22) - Observability: job logs, timings, failure reasons
- [#23](https://github.com/seung-gu/opad/issues/23) - [Docs] Update README for 3-service Railway deployment

---

## Other Issues

### Open
- [#24](https://github.com/seung-gu/opad/issues/24) - Roadmap: 3-service split (web/api/worker)
- [#26](https://github.com/seung-gu/opad/issues/26) - [Enhancement] Replace polling with SSE for real-time progress updates

---

**Note**: For detailed information about each issue, including closed dates, please check the [GitHub Issues board](https://github.com/seung-gu/opad/issues).
