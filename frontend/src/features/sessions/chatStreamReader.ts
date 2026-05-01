type ChatStreamEventHandler = (data: Record<string, unknown>) => boolean | void

export async function consumeChatStream(response: Response, onEvent: ChatStreamEventHandler) {
  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''
  let streamDone = false

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const jsonStr = line.slice(6).trim()
      if (!jsonStr) continue

      try {
        const data = JSON.parse(jsonStr)
        if (data && typeof data === 'object') {
          streamDone = Boolean(onEvent(data as Record<string, unknown>))
        }
      } catch {
        // Ignore malformed stream frames. The backend may keep sending valid frames.
      }
      if (streamDone) break
    }
    if (streamDone) break
  }
}
