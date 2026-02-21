# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2026-02-20

### Added
- **Article domain model enhancements** — value objects: `SourceInfo`, `EditRecord`, `GenerationResult` providing type-safe article metadata (Issue #101)
- **Article aggregate methods** — `create()`, `complete()`, `fail()`, `delete()`, `is_deleted`, `has_content`, `is_owned_by()` encapsulating article lifecycle logic
- **Articles collection class** — paginated results container for article queries
- **JobQueuePort protocol** — outbound port abstracting job queue operations (enqueue, dequeue, update status)
- **RedisJobQueueAdapter** — production implementation of JobQueuePort using Redis BLPOP/RPUSH for async job processing
- **FakeJobQueueAdapter** — in-memory test adapter for deterministic queue testing
- **ArticleGeneratorPort protocol** — outbound port abstracting article generation via external processors
- **CrewAIArticleGenerator adapter** — production implementation using CrewAI for multi-stage article generation
- **FakeArticleGenerator** — in-memory test adapter for testing without CrewAI dependencies
- **ArticleGenerationService** — orchestration layer with `submit_generation()` and `generate_article()` methods coordinating ports
- **Domain exceptions** — `DuplicateArticleError` (for duplicate article detection), `EnqueueError` (for queue failures)
- **Comprehensive test suite** — 31 unit tests for article_generation_service covering service orchestration, port interactions, and error cases

### Changed
- **Crew adapter migration** — `crew/` → `adapter/crew/` following hexagonal architecture for framework isolation
- **Route error handling** — replaced inline HTTPException logic with domain exception pattern for consistent error semantics
- **Route function naming** — removed `_endpoint` suffixes for cleaner function names
- **Token usage tracking** — renamed `track_crew_usage` → `track_agent_usage` for framework-agnostic naming
- **Worker processor refactoring** — integrated ArticleGenerationService and ports for decoupled job processing

### Removed
- **`src/api/job_queue.py`** — replaced by hexagonal architecture adapters (`adapter/queue/redis_job_queue.py`)
- **Direct framework dependencies** — CrewAI and Redis imports removed from service/route layers (now isolated in adapters)

### Technical Impact
- **Queue abstraction**: JobQueuePort enables swapping Redis with other queue systems (RabbitMQ, Celery, etc.) without service changes
- **Generation flexibility**: ArticleGeneratorPort decouples CrewAI implementation from domain logic, enabling alternate generators
- **Testability**: FakeJobQueueAdapter and FakeArticleGenerator enable fast unit tests without external dependencies
- **Error semantics**: Domain exceptions (DuplicateArticleError, EnqueueError) replace generic HTTP status codes
- **Worker decoupling**: Processor depends on ports, not concrete implementations
- **Separation of concerns**: Adapters own framework logic, services own business logic, routes own HTTP concerns

## [0.16.0] - 2026-02-19

### Added
- **VocabularyPort protocol** — new port for vocabulary aggregate queries (count_by_lemma, find_lemmas) separated from VocabularyRepository CRUD to clarify intent (Issue #100)
- **NLPPort protocol** — outbound port for NLP extraction (Stanza, spaCy) enabling language-agnostic linguistic feature extraction
- **Separate vocabulary routes** (`api/routes/vocabulary.py`) for vocabulary CRUD operations (add, list, delete) distinct from dictionary search
- **Seven comprehensive vocabulary route tests** covering:
  - GET /dictionary/vocabularies endpoint with language filter, pagination, and max limit enforcement
  - POST /dictionary/vocabulary endpoint for adding words with full metadata
  - DELETE /dictionary/vocabularies/{id} endpoint with permission checks and ownership validation
  - Authentication requirement for all vocabulary operations
  - Error handling (404 NotFound, 403 PermissionDenied, 500 SaveFailure)
- **LemmaResult and NLPPort extraction** — modular lemma extraction module as service function with NLP adapter injection

### Changed
- **Router split**: Dictionary routes refactored to handle search only (`/dictionary/search`), vocabulary operations moved to separate routes (`/dictionary/vocabulary`, `/dictionary/vocabularies`)
- **Lemma extraction moved to services**: `services/lemma_extraction.py` as module-level functions accepting injected NLPPort and LLMPort
- **Sense selection moved to services**: `services/sense_selection.py` as module-level functions accepting injected LLMPort
- **DictionaryPort methods expanded** — added `build_sense_listing()`, `get_sense()`, and `extract_grammar()` methods to encapsulate entry-structure knowledge
- **Dependency injection**: Routes now inject VocabularyPort for aggregate queries and NLPPort for linguistic extraction
- Refactored `vocabulary_service` to use module-level functions (`save`, `delete`) accepting injected VocabularyRepository
- Architecture diagrams updated: `service_diagram_layers.drawio` with 4 new port nodes (DictionaryPort, LLMPort, NLPPort, VocabularyPort) and consistent color scheme

### Removed
- `utils/dictionary_api.py` — entry structure knowledge moved to DictionaryPort implementation
- `utils/lemma_extraction.py` from utils (moved to services layer)
- `utils/sense_selection.py` from utils (moved to services layer)
- Corresponding unit tests in `utils/tests/` for lemma_extraction and sense_selection (tests moved to api/tests)

### Technical Impact
- **API clarity**: Separate routes for search (stateless) vs vocabulary management (stateful) improves cognitive load
- **Port consolidation**: 4 focused ports (Dictionary, LLM, NLP, TokenUsageRepository) replace ad-hoc utility imports
- **Testability**: Service-layer extraction enables testing without MockLibrary patterns — use FakeVocabularyRepository, FakeNLPAdapter directly
- **Extensibility**: NLPPort enables pluggable NLP backends (Stanza for German, spaCy for English, etc.)
- **Layer separation**: Services own business logic (vocabulary deduplication, lemma extraction logic), routes handle HTTP concerns only

## [0.15.0] - 2026-02-16

### Added
- **DictionaryPort and LLMPort abstraction** — outbound ports for external API abstractions enabling provider-agnostic integration (Issue #100)
- `FreeDictionaryAdapter` implementing `DictionaryPort` for Free Dictionary API lookups
- `LiteLLMAdapter` implementing `LLMPort` for provider-agnostic LLM calls via LiteLLM
- `FakeDictionaryAdapter` and `FakeLLMAdapter` for testing without external dependencies
- FastAPI dependency injection functions: `get_dictionary_port()` and `get_llm_port()` in `api/dependencies.py`
- `lemma_extraction.py` accepts injected `LLMPort` for language-specific lemma extraction (Stanza for German, LLM for others)
- `sense_selection.py` accepts injected `LLMPort` for context-aware sense selection from dictionary entries
- `SenseResult` dataclass for structured sense selection output

### Changed
- **Converted `DictionaryService` to module functions** — `lookup()` now orchestrates the hybrid pipeline with injected ports
- **Eliminated request/response DTOs** — `LookupRequest`, `LookupResult`, `DictionaryAPIResult` removed, uses plain dicts for simplicity
- Lemma extraction and sense selection modules now depend on `LLMPort` instead of direct `call_llm_with_tracking` imports
- Dictionary routes inject `DictionaryPort` and `LLMPort` dependencies instead of calling service directly
- `lemma_extraction.extract_lemma()` signature: accepts `llm: LLMPort` parameter for flexible LLM provider injection
- `sense_selection.select_best_sense()` signature: accepts `llm: LLMPort` parameter for flexible LLM provider injection
- FastAPI Depends pattern unified: all external services use port-based dependency injection

### Fixed
- Test mocking strategy simplified — replaced `@patch('...call_llm_with_tracking')` with concrete `FakeLLMAdapter` and `FakeDictionaryAdapter` instances

### Technical Impact
- **Testability**: Adapter injection enables deterministic testing without mocking framework dependencies
- **Extensibility**: New dictionary providers (e.g., Merriam-Webster) can be added by implementing `DictionaryPort`
- **Provider flexibility**: LLM provider swappable via `LiteLLMAdapter` configuration (OpenAI, Claude, Gemini, etc.)
- **SOLID compliance**: Dependency Inversion Principle — business logic depends on abstractions (ports), not concrete implementations (adapters)
- **Code reduction**: Eliminated verbose DTOs, test boilerplate reduced via concrete fake adapters
- **All 504 tests passing** — comprehensive coverage across lemma extraction, sense selection, and dictionary service integration

## [Unreleased]

### Changed
- **Enhanced `service_diagram.drawio` with CQRS visual distinction** — all 31 edges now color-coded for architecture clarity (Issue #98)
  - Red solid lines (13 edges): Command operations (Write operations)
  - Green dashed lines (6 edges): Query operations (Read operations)
  - Gray lines (12 edges): Infrastructure/utility connections
- Added CQRS legend to diagram with 3 primary categories
- Fixed 2 miscategorized edges during code review:
  - `DictionaryPort → DictionaryService`: Reclassified from Write to Read (query operation)
  - `processor → VocabularyRepository`: Reclassified from Write to Read (query operation)

## [0.14.0] - 2026-02-14

### Added
- Phase 2 completion: User, Vocabulary, and TokenUsage repositories migrated to hexagonal pattern (Issues #98/#99)
- Domain models: `User`, `Vocabulary`, `VocabularyCount`, `GrammaticalInfo`, and `TokenUsage` with clean business logic separation
- `UserRepository`, `VocabularyRepository`, and `TokenUsageRepository` protocols (ports) defining contracts for persistence
- `MongoUserRepository`, `MongoVocabularyRepository`, and `MongoTokenUsageRepository` adapters implementing MongoDB persistence
- `FakeUserRepository`, `FakeVocabularyRepository`, and `FakeTokenUsageRepository` in-memory adapters for testing without database
- Shared index management: `adapter/mongodb/indexes.py` with `create_index_safe()` and `ensure_all_indexes()` for conflict resolution
- Operational statistics module: `adapter/mongodb/stats.py` for database and vocabulary collection analytics
- Vocabulary service (`services/vocabulary_service.py`) extracting business logic: duplicate detection, CEFR level filtering
- Each MongoXxxRepository now includes `ensure_indexes()` method for autonomous index management
- FastAPI lifespan pattern migration from deprecated `@app.on_event("startup")` to modern `@asynccontextmanager`
- Authentication requirement for `/stats` endpoint via `get_current_user_required` dependency

### Changed
- Deleted legacy `utils/mongodb.py` (2,000+ lines) — monolithic utility replaced by dedicated repositories
- API routes now inject repository Protocol types instead of direct MongoDB calls
- `/stats` endpoint now requires authentication (was previously public)
- Worker processor uses dependency-injected repositories from composition roots
- API models now use `UserResponse` instead of direct `User` domain model (authentication refactoring)
- Refactored user/vocabulary/token_usage imports to use domain models and protocols throughout codebase

### Removed
- `utils/mongodb.py` — entire 2,000+ line monolithic utility file deleted
- Old MongoDB utility functions for user, vocabulary, and token usage management
- `api/middleware/auth.py` — renamed to `api/security.py` as authentication utility module
- Domain model tests moved to unit test suite (previously inline in domain models)
- Direct MongoDB imports from route handlers (now injected via dependencies)

### Technical Impact
- **Code reduction**: Net 4,561 lines deleted (MongoDB utility + duplicates), net improvement in codebase maintainability
- **Testability**: Repository protocols enable seamless swapping between MongoDB and in-memory adapters
- **Separation of concerns**: Business logic extracted from persistence layer into dedicated services
- **Index management**: Centralized safe index creation with conflict resolution prevents schema migration issues
- **SOLID principles**: Dependency Inversion (ports/adapters), Single Responsibility (per repository), Open/Closed (protocols for extensibility)

## [0.13.0] - 2026-02-14

### Added
- Hexagonal Architecture (Ports & Adapters) implementation for Article entity (Issue #98 Phase 1)
- New domain model layer: `Article`, `ArticleInputs`, `ArticleStatus` for clean business logic separation
- `ArticleRepository` Protocol (port) defining contract for article persistence with 8 core operations
- `MongoArticleRepository` adapter providing MongoDB implementation of ArticleRepository Protocol
- `FakeArticleRepository` adapter for in-memory testing without database dependencies
- Dependency injection composition roots: `api/dependencies.py` for FastAPI and Worker main.py
- 36 comprehensive tests covering domain model (21 tests) and repository operations (15 tests)
- Repository pattern enables seamless adaptation between MongoDB (production) and in-memory (testing) implementations

### Changed
- Migrated Article persistence from monolithic `mongodb.py` to dedicated adapters following hexagonal architecture
- API routes now inject `ArticleRepository` Protocol instead of directly accessing MongoDB
- Worker processor now uses dependency-injected repository for article storage
- Article retrieval methods unified through `MongoArticleRepository.get_by_id()` and `find_many()` operations
- Refactored database access layer to comply with Dependency Inversion Principle (SOLID)

### Deprecated
- 8 Article functions in `utils/mongodb.py` marked for Phase 2 removal: `save_article_metadata()`, `save_article_content()`, `get_article()`, `list_articles()`, `find_duplicate_article()`, `update_article_status()`, `delete_article()`, and related direct database queries

## [0.12.0] - 2026-02-09

### Added
- Stanza NLP integration for German lemma extraction providing 15-20x performance improvement (~51ms vs ~800ms LLM call)
- Thread-safe Stanza singleton with double-check locking pattern for efficient resource management
- Stanza pipeline preloading at API startup for instant lemma extraction availability
- New `SenseResult` dataclass for structured sense selection output with clear return types
- Comprehensive unit tests for lemma extraction (46 tests) and sense selection (56 tests) with edge case coverage

### Changed
- Refactored dictionary service pipeline into two distinct steps: Step 1 (lemma extraction) → API → Step 2 (sense selection)
- Extracted lemma extraction logic into new `src/utils/lemma_extraction.py` module (Strategy Pattern: `LemmaExtractor` ABC with `StanzaLemmaExtractor` for German and `LLMLemmaExtractor` for other languages)
- Extracted sense selection logic into new `src/utils/sense_selection.py` module for improved separation of concerns
- Refactored language-specific handlers into pure data module `src/utils/language_metadata.py` containing language constants (GENDER_MAP, REFLEXIVE_PREFIXES, REFLEXIVE_SUFFIXES, PHONETICS_SUPPORTED) with inline logic in `dictionary_api.py` for improved simplicity and maintainability
- Reduced `dictionary_service.py` from ~534 to ~272 lines by acting as pure orchestrator
- Reduced `prompts.py` to ~70 lines containing only full LLM fallback prompt
- Stanza lemma extraction runs in `asyncio.to_thread()` context to prevent blocking event loop
- Updated `_find_target_token` to return (token, sentence) tuple for correct sentence context in lemma selection
- CEFR vocabulary level determination moved to second LLM call (sense selection) for German Stanza path
- Removed `Handler` class pattern from `language_handlers.py` (replaced with simpler metadata-driven approach)
- Moved `_accumulate_stats` from `dictionary_service.py` to `llm.py` as public `accumulate_stats()` function, co-locating `TokenUsageStats` and its operations

### Dependencies
- Added `stanza>=1.9.0` for neural NLP pipeline and German lemmatization

## [0.11.6] - 2026-02-09

### Fixed
- Vocabulary words not highlighted for Korean (and other languages) when `related_words` is empty/null in MarkdownViewer.tsx
- article_picker selecting articles from CrewAI memory instead of finder's results (removed all memory: ShortTermMemory, LongTermMemory, EntityMemory)
- article_picker hallucinating articles not in finder's output — added "MUST select ONLY from provided list" constraint
- article_finder returning old articles — changed SerperDevTool to search_type="news"
- article_finder returning snippets instead of full text — added ScrapeWebsiteTool for full article scraping
- article_reviewer changing direct quotes and author's stylistic choices

### Changed
- article_finder: 3-5 → 5-7 articles, topic+language only (removed length/difficulty filtering)
- article_picker: criteria now priority-ordered (topic > level > length), prefers single-topic articles over roundups
- article_picker: only returns none if topic is completely unrelated (length/level mismatches acceptable)
- article_rewriter: NEVER fabricate information, keep rewrite short if original is short
- article_reviewer: only fix grammar, flow, level-appropriateness; preserve quotes and author style
- Stale docstring in test_dictionary_service.py updated

### Removed
- CrewAI memory system (ShortTermMemory, LongTermMemory, EntityMemory) and ./memory/ directory

## [0.11.5] - 2026-02-08

### Fixed
- Vocabulary words now correctly get highlighted (green color) for Korean and other languages when `related_words` is empty or null. The guard clause in `MarkdownViewer.tsx` now ensures the clicked word itself is always highlighted regardless of `related_words` availability
- Stale docstring in test_dictionary_service.py referencing old method name `_select_best_sense` (now `_select_best_entry_sense`)

## [0.11.4] - 2026-02-07

### Added
- `extract_entry_metadata()` public function in dictionary_api.py for extracting POS, phonetics, forms, and gender from any Free Dictionary API entry
- `_build_entry_sense_prompt`, `_parse_entry_sense_response`, `_get_definition_from_selection` static helper functions in dictionary_service.py for LLM-based entry selection

### Changed
- `_get_language_code` renamed to `get_language_code` in dictionary_api.py (now public)
- `_select_best_sense` replaced with `_select_best_entry_sense` to use full entry/sense/subsense hierarchy instead of entry[0] default
- Dictionary API entry selection now uses LLM-based X.Y.Z format (entry.sense.subsense) achieving 96.2% accuracy vs previous entry[0] approach
- Reduced cyclomatic complexity from C(17) to B(9) for entry selection logic through improved code organization

### Fixed
- Dictionary API now correctly selects appropriate entry, sense, and subsense using intelligent LLM selection instead of always defaulting to entries[0] (issue #92)

### Removed
- Dead code: `_parse_api_response()` function (inlined into calling functions)
- `all_senses` field replaced by `all_entries` for clearer API representation

## [0.11.3] - 2026-02-07

### Fixed
- Word-only cache key (`language:word`) in dictionary lookup now includes sentence context (`language:word:sentence`) to ensure correct lemma and definition selection for context-dependent words like "sich", "an", "auf" in German (issue #88)
- Updated cache logic in `lemmaCacheRef` (6 locations) and `wordToLemmaRef` (4 locations) to use context-aware cache keys
- Moved `extractSentence` call before cache checks in `handleWordClick` to ensure sentence context is available for cache key generation
- Enhanced `getWordMeaning` and `getRelatedWords` functions to accept sentence parameter for accurate cache key generation

## [0.11.2] - 2026-02-07

### Fixed
- Sentence extraction for duplicate words in same paragraph now uses DOM offset-based matching with TreeWalker and sentence-splitter range info instead of fragile includes-based first-match (issue #87)
- Added fallback warning log for sentence extraction when DOM offset calculation fails
- Vocabulary button no longer appears for `<code>` and `<pre>` blocks (code review improvement)

## [0.11.1] - 2026-02-06

### Added
- Reduced prompt testing script (`test_reduced_prompt.py`) with 50 new unit tests for dictionary service refactoring
- Test cases and test definition selection scripts for comprehensive dictionary service validation
- `test_cases.py` for benchmarking and testing sense selection improvements
- `max_tokens=10` parameter for sense selection LLM calls to prevent unbounded token usage

### Changed
- Refactored dictionary service with strategy pattern for improved code organization
- Consolidated `TokenUsageStats` - removed duplicate from dictionary_service.py, now uses canonical version from utils/llm
- Updated `_select_best_sense` to use `call_llm_with_tracking` instead of raw litellm for consistent token tracking
- Renamed prompt building functions `build_test_prompt_de/en` to `build_reduced_prompt_de/en` in prompts.py for clarity
- Reduced `REDUCED_PROMPT_MAX_TOKENS` from 2000 to 200 for more efficient prompt usage
- Improved sense selection parsing with robust regex (`re.search`) instead of fragile `int()` conversion
- Enhanced token stats accumulation to include sense selection LLM costs
- Fixed formatting in full fallback prompt (added missing space before colon)

### Fixed
- Always returns `DEFAULT_DEFINITION` on JSON parse failure instead of exposing raw LLM content
- Robust handling of sense selection responses with regex-based parsing for edge cases
- Eliminated duplicate prompt definitions from test scripts
- Dictionary service no longer exposes raw LLM errors to frontend

### Removed
- Dead code: `_extract_definition()` and `_extract_examples()` functions from dictionary_api.py
- Redundant `--test-prompt` CLI flag from test script
- Duplicate `TokenUsageStats` class definition from dictionary_service.py

## [0.11.0] - 2026-02-03

### Added
- Free Dictionary API integration (freedictionaryapi.com) for hybrid dictionary lookup combining LLM and API sources
- Support for German pronunciation (IPA) and word forms/conjugations via Free Dictionary API
- Automatic fallback to LLM-based dictionary lookup when API fails
- New `DictionaryAPIClient` utility class for managing Free Dictionary API calls
- Comprehensive API integration tests for dictionary lookup functionality
- Phonetics (IPA pronunciation) support displayed next to lemma for English words only
- Example sentences from Free Dictionary API with collapsible display
- VocabularyCard component for unified vocabulary display across views

### Changed
- Enhanced dictionary lookup prompts to leverage Free Dictionary API data
- Optimized token usage in vocabulary extraction (approximately 40% reduction)
- Updated dictionary route to utilize hybrid LLM + API approach for improved accuracy and cost efficiency
- Unified VocabularyCard component from duplicate code in VocabularyList and vocabulary/page
- Made examples always collapsible (removed collapsibleExamples prop)
- Used VocabularyMetadata TypedDict to reduce save_vocabulary parameters from 15 to 10
- Unified Conjugations type definition (exported from types/article.ts)
- Added Readonly<VocabularyCardProps> for props immutability

### Fixed
- Improved robustness of dictionary lookups with proper error handling and graceful fallback
- Fixed bare except clause in mongodb.py (changed to except Exception)
- Improved count condition clarity in VocabularyCard
- Fixed TypeScript error in phonetics/word conditional rendering

## [0.10.0] - 2026-02-03

### Added
- Article reviewer agent (Claude Sonnet 4) for quality assurance review of generated content
- Review article quality task to ensure natural language flow and semantic coherence
- CEFR vocabulary level filtering via `get_allowed_vocab_levels()` function
- Target level parameter support in vocabulary fetching for level-appropriate content selection
- Task and step callback logging to crew.py for improved workflow observability
- Comprehensive vocabulary level filtering test suite (49 tests) covering edge cases and filtering logic
- ReviewedArticle JSON output format with guardrail for structured article review results
- ReplacedSentence model for tracking sentence modifications and changes
- Pydantic property to CrewResult class for improved data structure handling
- Replaced sentences logging in processor.py for detailed change tracking

### Changed
- Updated adapt_news_article task to prohibit bold/italic/backtick formatting for vocabulary words to prevent breaking interactive word click handlers
- Enhanced get_user_vocabulary_for_generation() to filter vocabulary by target_level parameter for improved relevance
- Modified processor.py to pass target_level when fetching user vocabulary for article generation
- Removed callback functions from crew.py to streamline agent configuration

### Fixed
- Edge case bug in get_allowed_vocab_levels() handling negative max_above parameter values
- Added isinstance check for type safety in article processing

## [0.9.0] - 2026-01-29

### Added
- Centralized CSS variable theming system for consistent styling across web interface
- Token usage tracking and monitoring dashboard with cost calculations
- JobTracker coordinator for unified token tracking across worker processes
- LiteLLM callback integration for automatic token usage tracking

### Changed
- Migrated ESLint configuration to Biome for improved linting performance
- Updated agent names in configuration for clarity and consistency
- Enhanced token usage tracking with proper callback save/restore pattern

### Fixed
- Default vocabulary assignment to prevent template errors during article generation
- Parameter type correction in GET function for article usage

## [0.8.1] - 2026-01-28

### Changed
- Updated documentation requirements to reference Context7 MCP tools for accessing latest library information

## [0.8.0]

## [0.7.0]

## [0.6.0]
