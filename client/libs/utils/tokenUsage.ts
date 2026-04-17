const OPERATION_LABELS: Record<string, string> = {
  dictionary_search: 'Dictionary Search',
  article_generation: 'Article Generation',
}

export function extractAgentName(metadata?: { agent_name?: unknown; agent_role?: unknown }): string | undefined {
  const rawAgentName = metadata?.agent_name
  if (typeof rawAgentName === 'string' && rawAgentName) {
    return rawAgentName
  }
  const rawAgentRole = metadata?.agent_role
  if (typeof rawAgentRole === 'string' && rawAgentRole) {
    return rawAgentRole
  }
  return undefined
}

export function formatOperationName(operation: string, agentName?: string): string {
  if (agentName) {
    return agentName
  }
  return operation.replaceAll('_', ' ').replaceAll(/\b\w/g, c => c.toUpperCase())
}

export function getOperationLabel(key: string): string {
  return OPERATION_LABELS[key] || key.replaceAll('_', ' ').replaceAll(/\b\w/g, c => c.toUpperCase())
}

export function formatTokens(tokens: number): string {
  return tokens.toLocaleString()
}

export function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}
