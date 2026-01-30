/**
 * Article-related type definitions.
 * 
 * These types match the FastAPI ArticleResponse and ArticleListResponse models.
 */

export type ArticleStatus = 'running' | 'completed' | 'failed' | 'deleted'

export interface Article {
  id: string
  language: string
  level: string
  length: string
  topic: string
  status: ArticleStatus
  created_at: string // ISO datetime string
  user_id: string | null
  job_id?: string | null // Job ID for progress tracking
  inputs?: {
    language: string
    level: string
    length: string
    topic: string
  }
}

export interface ArticleListResponse {
  articles: Article[]
  total: number
  skip: number
  limit: number
}

export interface ArticleListFilters {
  status?: ArticleStatus
  skip?: number
  limit?: number
}

/**
 * Vocabulary entry with grammatical metadata for language learning.
 *
 * Stores word definitions with contextual information and grammatical features
 * to support comprehensive vocabulary acquisition.
 */
export interface Vocabulary {
  /** Unique vocabulary entry identifier */
  id: string
  /** Article ID where the word was encountered */
  article_id: string
  /** Original word as it appears in the article */
  word: string
  /** Dictionary form (base/citation form) of the word */
  lemma: string
  /** Context-aware definition of the word */
  definition: string
  /** Full sentence context where the word appears */
  sentence: string
  /** Target language of the vocabulary word */
  language: string
  /** All word forms in sentence belonging to this lemma (e.g., separable verb parts: ["hängt", "ab"]) */
  related_words?: string[]
  /** Span ID linking to the word's location in the article markdown */
  span_id?: string
  /** Timestamp when the vocabulary was saved (ISO datetime string) */
  created_at: string
  /** User ID who saved this vocabulary entry */
  user_id?: string | null
  /** Part of speech (noun, verb, adjective, adverb, preposition, etc.) */
  pos?: string
  /** Grammatical gender for nouns in gendered languages (German: der/die/das, French: le/la, Spanish: el/la). Null for non-gendered languages or non-nouns. */
  gender?: string
  /** Verb conjugation forms across different tenses. Null for non-verbs. */
  conjugations?: {
    /** Present tense form */
    present?: string
    /** Past/preterite tense form */
    past?: string
    /** Perfect/past participle form */
    perfect?: string
  }
  /** CEFR difficulty level (A1, A2, B1, B2, C1, C2) for vocabulary tracking and adaptive learning */
  level?: string
}

/**
 * Aggregated vocabulary statistics grouped by lemma.
 *
 * Tracks how many times a word (lemma) has been saved across different articles,
 * showing the most recent grammatical metadata and definition.
 */
export interface VocabularyCount extends Vocabulary {
  /** Number of times this lemma was saved across all articles */
  count: number
  /** List of article IDs where this lemma appears */
  article_ids: string[]
}
