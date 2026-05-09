import { getCefrCategory, type CefrCategory } from '@opad/libs'

const TAILWIND_BY_CATEGORY: Record<CefrCategory, string> = {
  beginner: 'bg-good/20 text-good',
  intermediate: 'bg-accent-warn/20 text-accent-warn',
  advanced: 'bg-accent-danger/20 text-accent-danger',
  unknown: 'bg-card text-text-dim',
}

export function getLevelColor(level?: string): string {
  return TAILWIND_BY_CATEGORY[getCefrCategory(level)]
}
