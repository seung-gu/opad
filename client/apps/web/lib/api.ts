import { getToken } from './auth'

export { parseErrorResponse } from '@opad/libs'

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken()

  const headers = {
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  }

  return fetch(url, {
    ...options,
    headers,
  })
}
