export type CefrCategory = 'beginner' | 'intermediate' | 'advanced' | 'unknown'

export function getCefrCategory(level?: string): CefrCategory {
  if (!level) return 'unknown'
  if (level.startsWith('A')) return 'beginner'
  if (level.startsWith('B')) return 'intermediate'
  return 'advanced'
}

export function getCefrLabel(level?: string): string {
  if (!level) return 'Unknown'
  if (level.startsWith('A')) return 'Beginner'
  if (level.startsWith('B')) return 'Intermediate'
  return 'Advanced'
}
