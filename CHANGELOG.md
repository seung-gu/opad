# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
