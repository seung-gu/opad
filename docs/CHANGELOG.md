# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 3 new post-QA agents: version-release-agent, changelog-agent, docs-agent
- Parallel execution workflow for release automation
- Structured agent instructions in `.claude/agents/`

### Changed
- Updated CLAUDE.md with new agent pipeline visualization
- Synchronized version across all services to 0.6.0

## [0.6.0] - 2026-01-28

### Added
- RESTful API restructuring with clear resource hierarchy
- New endpoint: `GET /articles/{id}/vocabularies` for article-specific vocabularies
- `POST /dictionary/search` with authentication to prevent API abuse
- Pagination support for vocabulary lists (skip, limit parameters)
- Comprehensive tests for vocabulary API endpoints
- TypeScript types: VocabularyCount with count and article_ids fields

### Changed
- `POST /dictionary/define` → `POST /dictionary/search` (semantic clarity)
- `POST /dictionary/vocabularies` → `POST /dictionary/vocabulary` (singular)
- `GET /dictionary/vocabularies` now always returns aggregated data (removed conditional logic)
- Vocabulary page UI: fixed article link positioning using flex-col with mt-auto
- Removed conditional endpoint behavior based on query parameters

### Fixed
- Vocabulary page article links: show only most recent article
- Consistent card height on vocabulary list page
- JSON type mismatch in vocabulary page (VocabularyCount vs VocabularyCount[])

### Removed
- `GET /dictionary/stats` HTML endpoint (duplicate functionality)
- Conditional article_id logic from `/dictionary/vocabularies` endpoint

## [0.2.1] - Previous Release

### Added
- Initial vocabulary management system
- Basic article generation
- User authentication foundation

## [0.1.0] - Project Initialization

### Added
- 3-service architecture (Web/API/Worker)
- MongoDB and Redis integration
- Basic user model
- Article storage structure
