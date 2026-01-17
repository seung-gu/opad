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
  owner_id: string | null
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
