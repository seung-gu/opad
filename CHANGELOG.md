# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
