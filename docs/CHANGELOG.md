# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] - 2026-01-30

### Fixed
- Vocabulary button not appearing in article detail view (fixed firstElementChild DOM reference)
- Stale closure issue in MarkdownViewer word click handler (ref-based callback storage for event delegation)
- React DOM mismatch error on content change (key prop pattern for component remount)

### Security
- XSS vulnerability in MarkdownViewer: replaced innerHTML with escapeHtml utility and DOM API methods
- Escaped all user-provided data in HTML attributes (word, lemma, definition, sentence)
- Protected against script injection in vocabulary definitions and word forms

### Changed
- MarkdownViewer key prop pattern: `key={${articleId}-${content.length}}` for forcing remount on content change

## [0.7.0] - 2026-01-29

### Added
- Part of speech (pos) field to vocabulary data model for grammatical classification
- Grammatical gender field support for gendered languages (German, French, Spanish)
- Verb conjugations support (present, past, perfect tense forms) for verbs
- CEFR proficiency level (A1-C2) for vocabulary items to aid language learning progression
- 70 comprehensive tests covering security, functionality, and edge cases for vocabulary endpoints
- Color-coded CEFR level badges in UI (A1=green, B1=yellow, C1=red)
- POS badges and gender display in vocabulary list and article detail views
- Conjugation forms display for verb entries in frontend
- Utility functions: `formatters.ts` (formatDate, formatDateShort, formatDateTime) for consistent date formatting
- Utility functions: `styleHelpers.ts` (getLevelColor, getLevelLabel) for CEFR level styling
- API utility: `parseErrorResponse` in `api.ts` for centralized error handling
- Components: `ErrorAlert` for consistent error messaging across pages
- Components: `EmptyState` for consistent empty state UI patterns
- Hooks: `useAsyncFetch` for simplified async data fetching with loading/error states
- Hooks: `usePagination` for unified pagination logic across list pages
- Hooks: `useStatusPolling` for job status polling with configurable intervals
- Tailwind safelist configuration for CEFR level colors to prevent CSS purging
- Web testing infrastructure: Vitest 4.0.18 with jsdom, @testing-library/react, and @vitest/ui
- Test files for hooks (usePagination, useStatusPolling) and utilities (api, formatters, styleHelpers)
- Coverage thresholds: 80% for lines, functions, branches, and statements
- Conjugations.__bool__() method for truthiness checking of verb conjugation forms
- VocabularyRequest.field_validator for automatic Conjugations-to-dict conversion

### Changed
- Renamed DefineRequest/Response to SearchRequest/SearchResponse for API semantic clarity
- Enhanced VocabularyRequest and VocabularyResponse models with new grammatical fields
- Updated POST /api/dictionary/search to return pos, gender, conjugations, and level fields
- Refactored vocabulary page to use new utility functions and components for improved maintainability
- Refactored articles page to use `usePagination` hook for consistent pagination behavior
- Refactored article detail page to use `useStatusPolling` hook for job status tracking
- Updated all pages to use centralized utility functions and shared components
- Improved code organization with ~420 lines of duplicate code eliminated
- Simplified Conjugations API model handling with `__bool__` method for automatic falsy value detection
- Enhanced VocabularyRequest with field validator for automatic dictionary-to-model conversion

### Fixed
- Fixed regex injection vulnerability in vocabulary search by adding re.escape() to prevent malicious input
- Preserved German noun capitalization by removing inappropriate lemma.lower() call
- Fixed missing fields in get_vocabularies() and get_vocabulary_by_id() return values
- Conjugations type conversion bug in dictionary API for proper verb form handling
- Tailwind CSS purge issue with dynamic CEFR level classes (added safelist configuration)
- Vocabulary POST endpoint path parameter validation bug

## [0.6.0] - 2026-01-28

### Added
- 3 new post-QA agents: version-release-agent, changelog-agent, docs-agent
- Parallel execution workflow for release automation
- Structured agent instructions in `.claude/agents/`
- RESTful API restructuring with clear resource hierarchy
- New endpoint: `GET /articles/{id}/vocabularies` for article-specific vocabularies
- `POST /dictionary/search` with authentication to prevent API abuse
- Pagination support for vocabulary lists (skip, limit parameters)
- Comprehensive tests for vocabulary API endpoints
- TypeScript types: VocabularyCount with count and article_ids fields

### Changed
- Updated CLAUDE.md with new agent pipeline visualization
- Synchronized version across all services to 0.6.0
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
