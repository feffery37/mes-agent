import { API_BASE_URL } from "./config"
import type { SSEEvent } from "./types"

/**
 * 以 POST + fetch ReadableStream 消费后端 SSE 流。
 * 浏览器原生 EventSource 仅支持 GET，而后端 chat 接口为 POST，故采用 fetch 手动解析。
 */
export async function streamChat(
  message: string,
  sessionId: string | null,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`请求失败：HTTP ${resp.status}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split("\n")
    buf = lines.pop() ?? ""
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith("data:")) continue
      const payload = trimmed.slice(5).trim()
      if (!payload) continue
      try {
        onEvent(JSON.parse(payload) as SSEEvent)
      } catch {
        // 忽略无法解析的分片
      }
    }
  }
}
