const BASE = import.meta.env.VITE_API_BASE_URL || ''

interface LoginResponse {
  access_token: string
  token_type: string
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams({ username, password })
  const res = await fetch(`${BASE}/api/v1/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  })
  if (!res.ok) throw new Error('Invalid credentials')
  return res.json()
}

export async function getSessions(token: string): Promise<unknown> {
  const res = await fetch(`${BASE}/api/v1/chat/sessions`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}

export async function getSessionHistory(token: string, sessionId: string): Promise<unknown> {
  const res = await fetch(`${BASE}/api/v1/chat/sessions/${sessionId}/history`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}

export async function deleteSession(token: string, sessionId: string): Promise<void> {
  await fetch(`${BASE}/api/v1/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function streamChat(
  token: string,
  sessionId: string,
  message: string,
  onEvent: (eventType: string, payload: unknown) => void
): () => void {
  let cancelled = false
  ;(async () => {
    const res = await fetch(`${BASE}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ session_id: sessionId, message }),
    })
    if (!res.ok) {
      onEvent('error', { message: `HTTP ${res.status}` })
      return
    }
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (!cancelled) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const lines = part.split('\n')
        let eventType = 'message'
        let dataStr = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          if (line.startsWith('data: ')) dataStr = line.slice(6).trim()
        }
        if (dataStr) {
          try { onEvent(eventType, JSON.parse(dataStr)) } catch { /* ignore */ }
        }
      }
    }
  })()
  return () => { cancelled = true }
}
