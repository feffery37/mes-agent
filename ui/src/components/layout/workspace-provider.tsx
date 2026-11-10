"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { streamChat } from "@/lib/api/chat"
import { fetchInbox } from "@/lib/api/inbox"
import { confirmNotification } from "@/lib/api/notification"
import { confirmWorkorder } from "@/lib/api/workorder"
import type { PendingItem, PendingKind, SSEEvent, ToolCallEvent } from "@/lib/api/types"

export type ChatTurn = {
  id: string
  user: string
  tools: ToolCallEvent[]
  answer: string
  /** 模型思维链（reasoning_content），取本轮最早收到的非空值 */
  reasoning?: string
  streaming: boolean
  error?: string
}

export type ChatSession = {
  /** 前端会话 ID，用于切换 / 删除 */
  id: string
  /** 后端 session_id，同一会话复用，保持多轮记忆 */
  sessionId: string
  title: string
  createdAt: number
  updatedAt: number
  turns: ChatTurn[]
}

export type SidebarTab = "sessions" | "inbox"
export type Resolution = { state: "done" | "cancelled"; label?: string }

type WorkspaceValue = {
  hydrated: boolean
  sessions: ChatSession[]
  activeId: string
  /** 当前会话的轮次 */
  turns: ChatTurn[]
  busy: boolean
  send: (message: string) => void
  newSession: () => void
  selectSession: (id: string) => void
  deleteSession: (id: string) => void
  tab: SidebarTab
  setTab: (tab: SidebarTab) => void
  inbox: PendingItem[]
  inboxLoading: boolean
  inboxError: string
  refreshInbox: () => Promise<void>
  /** token -> 已处理结果，供对话卡片与收件箱共享，避免重复点击 */
  resolved: Record<string, Resolution>
  resolve: (kind: PendingKind, token: string, action: "confirm" | "cancel") => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null)
const STORAGE_KEY = "imes.workspace.v1"
const RESOLVED_KEY = "imes.workspace.resolved.v1"
const MAX_SESSIONS = 30
const MAX_RESOLVED = 100
const INBOX_POLL_MS = 20_000

function makeSession(): ChatSession {
  const now = Date.now()
  return {
    id: crypto.randomUUID(),
    sessionId: crypto.randomUUID(),
    title: "新会话",
    createdAt: now,
    updatedAt: now,
    turns: [],
  }
}

function turnFromEvent(turn: ChatTurn, ev: SSEEvent): ChatTurn {
  switch (ev.type) {
    case "tool": {
      const tools = [...turn.tools]
      const idx = tools.findIndex((x) => x.tool_call_id === ev.tool_call_id)
      if (idx >= 0) tools[idx] = ev
      else tools.push(ev)
      return { ...turn, tools, reasoning: turn.reasoning ?? ev.reasoning ?? undefined }
    }
    case "message":
      return { ...turn, answer: ev.message, reasoning: turn.reasoning ?? ev.reasoning ?? undefined }
    case "error":
      return { ...turn, error: ev.error, streaming: false }
    default:
      return turn
  }
}

function readStored(): { sessions: ChatSession[]; activeId: string } {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return { sessions: [], activeId: "" }
    const parsed = JSON.parse(raw) as { sessions?: ChatSession[]; activeId?: string }
    const sessions = (parsed.sessions ?? [])
      .filter((s) => s && typeof s.id === "string" && typeof s.sessionId === "string")
      .slice(0, MAX_SESSIONS)
      .map((s) => ({
        ...s,
        // 刷新后不应该残留「正在分析」态
        turns: (s.turns ?? []).map((t) => ({ ...t, streaming: false })),
      }))
    return { sessions, activeId: parsed.activeId ?? "" }
  } catch {
    return { sessions: [], activeId: "" }
  }
}

/**
 * 工作台共享状态：多会话（本地持久化）、侧栏 tab、待确认收件箱与统一的确认入口。
 * 放在 layout 层，使侧栏与对话页看到同一份会话 / 草稿状态。
 */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState("")
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<SidebarTab>("sessions")
  const [inbox, setInbox] = useState<PendingItem[]>([])
  const [inboxLoading, setInboxLoading] = useState(true)
  const [inboxError, setInboxError] = useState("")
  const [resolved, setResolved] = useState<Record<string, Resolution>>({})

  // SSE 回调是异步闭包，用 ref 保证读到最新会话，切换会话也不会把事件写错地方
  const sessionsRef = useRef<ChatSession[]>([])
  const activeIdRef = useRef("")
  const busyRef = useRef(false)
  const resolvedRef = useRef<Record<string, Resolution>>({})

  const commit = useCallback((updater: (prev: ChatSession[]) => ChatSession[]) => {
    const next = updater(sessionsRef.current).slice(0, MAX_SESSIONS)
    sessionsRef.current = next
    setSessions(next)
  }, [])

  const setActive = useCallback((id: string) => {
    activeIdRef.current = id
    setActiveId(id)
  }, [])

  useEffect(() => {
    const stored = readStored()
    const next = stored.sessions.length ? stored.sessions : [makeSession()]
    const id = next.some((s) => s.id === stored.activeId) ? stored.activeId : next[0].id
    sessionsRef.current = next
    setSessions(next)
    activeIdRef.current = id
    setActiveId(id)
    try {
      const raw = window.localStorage.getItem(RESOLVED_KEY)
      resolvedRef.current = raw ? (JSON.parse(raw) as Record<string, Resolution>) : {}
      setResolved(resolvedRef.current)
    } catch {
      resolvedRef.current = {}
    }
    setHydrated(true)
  }, [])

  // 防抖写入：SSE 事件较密集，避免每个分片都同步写 localStorage
  useEffect(() => {
    if (!hydrated) return
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, activeId }))
      } catch {
        // 配额超限时忽略，不影响当前会话
      }
    }, 300)
    return () => window.clearTimeout(timer)
  }, [sessions, activeId, hydrated])

  useEffect(() => {
    if (!hydrated) return
    try {
      window.localStorage.setItem(RESOLVED_KEY, JSON.stringify(resolved))
    } catch {
      // 忽略
    }
  }, [resolved, hydrated])

  const refreshInbox = useCallback(async () => {
    try {
      const data = await fetchInbox()
      setInbox(data.items)
      setInboxError("")
    } catch {
      setInbox([])
      setInboxError("后端未连接，收件箱暂不可用")
    } finally {
      setInboxLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!hydrated) return
    void refreshInbox()
    const timer = window.setInterval(() => void refreshInbox(), INBOX_POLL_MS)
    return () => window.clearInterval(timer)
  }, [hydrated, refreshInbox])

  const resolve = useCallback(
    async (kind: PendingKind, token: string, action: "confirm" | "cancel") => {
      if (resolvedRef.current[token]) return
      let label = ""
      if (kind === "workorder") {
        const res = await confirmWorkorder(token, action === "cancel" ? "cancel" : "confirm")
        if (!res.success) throw new Error(res.message || "操作失败")
        label = (res.data?.workorder as { wo_id?: string } | undefined)?.wo_id ?? ""
      } else {
        const res = await confirmNotification(token, action === "cancel" ? "cancel" : "send")
        if (!res.success) throw new Error(res.message || "操作失败")
        label = (res.data?.channels ?? []).join("、")
      }
      const entries = Object.entries({
        ...resolvedRef.current,
        [token]: {
          state: action === "cancel" ? ("cancelled" as const) : ("done" as const),
          label,
        },
      }).slice(-MAX_RESOLVED)
      resolvedRef.current = Object.fromEntries(entries)
      setResolved(resolvedRef.current)
      await refreshInbox()
    },
    [refreshInbox]
  )

  const send = useCallback(
    (message: string) => {
      const text = message.trim()
      if (!text || busyRef.current) return
      const targetId = activeIdRef.current
      const target = sessionsRef.current.find((s) => s.id === targetId)
      if (!target) return
      const sessionId = target.sessionId
      const turnId = crypto.randomUUID()

      busyRef.current = true
      setBusy(true)
      commit((prev) =>
        prev.map((s) =>
          s.id !== targetId
            ? s
            : {
                ...s,
                title:
                  s.turns.length === 0
                    ? text.length > 18
                      ? `${text.slice(0, 18)}…`
                      : text
                    : s.title,
                updatedAt: Date.now(),
                turns: [
                  ...s.turns,
                  { id: turnId, user: text, tools: [], answer: "", streaming: true },
                ],
              }
        )
      )

      const apply = (ev: SSEEvent) =>
        commit((prev) =>
          prev.map((s) =>
            s.id !== targetId
              ? s
              : {
                  ...s,
                  updatedAt: Date.now(),
                  turns: s.turns.map((t) =>
                    t.id === turnId ? turnFromEvent(t, ev) : t
                  ),
                }
          )
        )

      void (async () => {
        try {
          await streamChat(text, sessionId, apply)
        } catch (e) {
          commit((prev) =>
            prev.map((s) =>
              s.id !== targetId
                ? s
                : {
                    ...s,
                    turns: s.turns.map((t) =>
                      t.id === turnId
                        ? {
                            ...t,
                            error: e instanceof Error ? e.message : "请求失败",
                            streaming: false,
                          }
                        : t
                    ),
                  }
            )
          )
        } finally {
          commit((prev) =>
            prev.map((s) =>
              s.id !== targetId
                ? s
                : {
                    ...s,
                    turns: s.turns.map((t) =>
                      t.id === turnId ? { ...t, streaming: false } : t
                    ),
                  }
            )
          )
          busyRef.current = false
          setBusy(false)
        }
      })()
    },
    [commit]
  )

  const newSession = useCallback(() => {
    const next = makeSession()
    commit((prev) => [next, ...prev])
    setActive(next.id)
    setTab("sessions")
  }, [commit, setActive])

  const selectSession = useCallback(
    (id: string) => {
      if (!sessionsRef.current.some((s) => s.id === id)) return
      setActive(id)
      setTab("sessions")
    },
    [setActive]
  )

  const deleteSession = useCallback(
    (id: string) => {
      const rest = sessionsRef.current.filter((s) => s.id !== id)
      const next = rest.length ? rest : [makeSession()]
      commit(() => next)
      if (activeIdRef.current === id) setActive(next[0].id)
    },
    [commit, setActive]
  )

  const turns = sessions.find((s) => s.id === activeId)?.turns ?? []
  const value: WorkspaceValue = {
    hydrated,
    sessions,
    activeId,
    turns,
    busy,
    send,
    newSession,
    selectSession,
    deleteSession,
    tab,
    setTab,
    inbox,
    inboxLoading,
    inboxError,
    refreshInbox,
    resolved,
    resolve,
  }

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace(): WorkspaceValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error("useWorkspace 必须在 WorkspaceProvider 内使用")
  return ctx
}
