"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { streamChat } from "@/lib/api/chat"
import type { SSEEvent, ToolCallEvent } from "@/lib/api/types"

export type ChatTurn = {
  id: string
  user: string
  tools: ToolCallEvent[]
  answer: string
  streaming: boolean
  error?: string
}

/**
 * 管理对话轮次与流式事件。
 * 同一会话复用 sessionId（后端据此提供多轮记忆），工具事件按 tool_call_id 去重更新。
 */
export function useChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [busy, setBusy] = useState(false)
  const sessionIdRef = useRef<string | null>(null)

  // 客户端挂载后再生成会话 ID，避免预渲染阶段调用 crypto.randomUUID()
  useEffect(() => {
    sessionIdRef.current = crypto.randomUUID()
  }, [])

  const send = useCallback(
    async (message: string) => {
      if (busy || !message.trim()) return
      const turnId = crypto.randomUUID()
      const newTurn: ChatTurn = {
        id: turnId,
        user: message,
        tools: [],
        answer: "",
        streaming: true,
      }
      setTurns((prev) => [...prev, newTurn])
      setBusy(true)

      const apply = (ev: SSEEvent) =>
        setTurns((prev) =>
          prev.map((t) => {
            if (t.id !== turnId) return t
            switch (ev.type) {
              case "tool": {
                const tools = [...t.tools]
                const idx = tools.findIndex((x) => x.tool_call_id === ev.tool_call_id)
                if (idx >= 0) tools[idx] = ev
                else tools.push(ev)
                return { ...t, tools }
              }
              case "message":
                return { ...t, answer: ev.message }
              case "error":
                return { ...t, error: ev.error, streaming: false }
              default:
                return t
            }
          })
        )

      try {
        await streamChat(message, sessionIdRef.current, apply)
      } catch (e) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === turnId
              ? { ...t, error: e instanceof Error ? e.message : "请求失败", streaming: false }
              : t
          )
        )
      } finally {
        setTurns((prev) =>
          prev.map((t) => (t.id === turnId ? { ...t, streaming: false } : t))
        )
        setBusy(false)
      }
    },
    [busy]
  )

  return { turns, send, busy }
}
