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

export interface Vocabulary {
  id: string
  article_id: string
  word: string
  lemma: string
  definition: string
  sentence: string
  language: string
  related_words?: string[] // All words in sentence belonging to this lemma (e.g., for separable verbs)
  span_id?: string // Span ID of the clicked word in the article
  created_at: string // ISO datetime string
}
