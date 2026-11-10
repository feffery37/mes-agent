"use client"

import { MessageSquare, Plus, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWorkspace } from "./workspace-provider"

function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60_000) return "刚刚"
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return new Date(ts).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })
}

/** 会话列表：本机持久化，切换会话时各自的 session_id 与对话内容互不串。 */
export function SessionList({ onNavigate }: { onNavigate?: () => void }) {
  const { sessions, activeId, hydrated, busy, newSession, selectSession, deleteSession } =
    useWorkspace()
  const sorted = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt)

  const create = () => {
    newSession()
    onNavigate?.()
  }

  const select = (id: string) => {
    selectSession(id)
    onNavigate?.()
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <button
        type="button"
        disabled={!hydrated}
        onClick={create}
        className="flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-lg border border-border bg-background text-xs text-foreground transition-colors hover:bg-secondary disabled:opacity-50"
      >
        <Plus className="h-3.5 w-3.5" strokeWidth={1.8} />
        新建会话
      </button>

      <div className="mt-2 min-h-0 flex-1 space-y-0.5 overflow-y-auto">
        {!hydrated && (
          <p className="px-2 py-3 text-[11px] text-muted-foreground">正在读取本地会话…</p>
        )}
        {hydrated && sorted.length === 0 && (
          <p className="px-2 py-3 text-[11px] text-muted-foreground">暂无会话，点击上方新建。</p>
        )}
        {hydrated &&
          sorted.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group relative rounded-lg transition-colors",
                session.id === activeId
                  ? "bg-secondary text-foreground"
                  : "text-foreground/75 hover:bg-secondary/60"
              )}
            >
              <button
                type="button"
                onClick={() => select(session.id)}
                className="flex w-full items-start gap-2 rounded-lg py-1.5 pl-2 pr-7 text-left"
                title={session.title}
              >
                <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" strokeWidth={1.7} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs">{session.title}</span>
                  <span className="mt-0.5 block text-[10px] text-muted-foreground">
                    {relativeTime(session.updatedAt)} · {session.turns.length} 轮
                  </span>
                </span>
              </button>
              <button
                type="button"
                aria-label={`删除会话 ${session.title}`}
                title="删除会话"
                onClick={() => deleteSession(session.id)}
                className="absolute right-1 top-1.5 hidden h-5 w-5 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-background hover:text-destructive group-hover:grid"
              >
                <Trash2 className="h-3 w-3" strokeWidth={1.7} />
              </button>
            </div>
          ))}
      </div>

      {busy && (
        <p className="shrink-0 px-2 pt-2 text-[10px] text-muted-foreground">正在生成回答…</p>
      )}
      <p className="shrink-0 px-2 pt-2 text-[10px] leading-relaxed text-muted-foreground">
        会话保存在本机浏览器；每个会话独立复用后端 session_id。
      </p>
    </div>
  )
}
