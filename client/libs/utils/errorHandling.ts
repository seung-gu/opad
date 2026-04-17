export async function parseErrorResponse(
  response: Response,
  defaultMessage: string = 'An error occurred'
): Promise<string> {
  try {
    const data = await response.json()
    return data.error || data.detail || data.message || defaultMessage
  } catch {
    return defaultMessage
  }
}
