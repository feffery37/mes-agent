"use client"

import { useState } from "react"
import { Bell, Check, Loader2, RefreshCw, ShieldCheck, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { PendingItem } from "@/lib/api/types"
import { useWorkspace } from "./workspace-provider"

const KIND_LABEL: Record<PendingItem["kind"], string> = {
  workorder: "维修工单",
  notification: "对外通知",
}

function remainingText(seconds: number): string {
  if (seconds <= 0) return "已过期"
  const minutes = Math.floor(seconds / 60)
  return minutes >= 1 ? `约 ${minutes} 分钟内有效` : `${seconds} 秒后过期`
}

/** 待确认收件箱：汇总两类草稿，刷新页面或切换会话后仍可找回并确认。 */
export function PendingInbox() {
  const { inbox, inboxLoading, inboxError, refreshInbox, resolved, resolve } = useWorkspace()
  const [busyToken, setBusyToken] = useState("")
  const [error, setError] = useState("")

  const act = async (item: PendingItem, action: "confirm" | "cancel") => {
    setBusyToken(item.confirm_token)
    setError("")
    try {
      await resolve(item.kind, item.confirm_token, action)
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败")
    } finally {
      setBusyToken("")
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center gap-1.5 px-1">
        <span className="text-[11px] font-medium tracking-wide text-muted-foreground">
          待确认 · {inbox.length}
        </span>
        <button
          type="button"
          onClick={() => void refreshInbox()}
          aria-label="刷新收件箱"
          title="刷新收件箱"
          className="ml-auto grid h-6 w-6 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.7} />
        </button>
      </div>
      <p className="mt-1 shrink-0 px-1 text-[10px] leading-relaxed text-muted-foreground">
        所有建单 / 通知草稿都汇总在这里，刷新页面也不会丢；确认动作仍需你点击。
      </p>

      {error && <p className="mt-2 px-1 text-[11px] text-destructive">{error}</p>}

      <div className="mt-2 min-h-0 flex-1 space-y-2 overflow-y-auto">
        {inboxLoading && (
          <p className="px-1 py-3 text-[11px] text-muted-foreground">正在读取待确认事项…</p>
        )}
        {!inboxLoading && inboxError && (
          <p className="px-1 py-3 text-[11px] leading-relaxed text-muted-foreground">
            {inboxError}。启动后端后点击右上角刷新即可。
          </p>
        )}
        {!inboxLoading && !inboxError && inbox.length === 0 && (
          <div className="rounded-lg border border-dashed border-border px-3 py-5 text-center">
            <Bell className="mx-auto h-4 w-4 text-muted-foreground" strokeWidth={1.6} />
            <p className="mt-2 text-[11px] text-muted-foreground">暂无待确认事项</p>
          </div>
        )}

        {inbox.map((item) => {
          const resolution = resolved[item.confirm_token]
          const loading = busyToken === item.confirm_token
          return (
            <div
              key={item.confirm_token}
              className="rounded-lg border border-border bg-background px-2.5 py-2"
            >
              <div className="flex items-center gap-1.5">
                {item.kind === "workorder" ? (
                  <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-muted-foreground" strokeWidth={1.7} />
                ) : (
                  <Bell className="h-3.5 w-3.5 shrink-0 text-muted-foreground" strokeWidth={1.7} />
                )}
                <Badge variant={item.kind === "notification" ? "warning" : undefined} className="shrink-0">
                  {KIND_LABEL[item.kind]}
                </Badge>
                <span className="ml-auto truncate text-[10px] text-muted-foreground">
                  {remainingText(item.remaining_seconds)}
                </span>
              </div>

              <div className="mt-1.5 truncate text-xs font-medium text-foreground" title={item.title}>
                {item.title}
              </div>
              <div className="mt-0.5 truncate text-[10px] text-muted-foreground" title={item.summary}>
                {item.summary}
              </div>

              {resolution ? (
                <p className="mt-2 text-[11px] text-foreground">
                  {resolution.state === "done"
                    ? item.kind === "workorder"
                      ? `已创建 ${resolution.label}`
                      : `已发送${resolution.label ? ` · ${resolution.label}` : ""}`
                    : "已忽略，未执行任何写操作"}
                </p>
              ) : (
                <div className="mt-2 flex gap-1.5">
                  <Button
                    size="sm"
                    disabled={loading}
                    onClick={() => void act(item, "confirm")}
                    className="h-7 flex-1 rounded-md bg-primary px-1 text-[11px] text-primary-foreground hover:bg-primary/90"
                  >
                    {loading ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <Check className="mr-1 h-3 w-3" />
                    )}
                    {item.kind === "workorder" ? "确认建单" : "发送通知"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={loading}
                    onClick={() => void act(item, "cancel")}
                    className="h-7 rounded-md px-2 text-[11px]"
                  >
                    <X className="h-3 w-3" />
                    {item.kind === "workorder" ? "取消" : "忽略"}
                  </Button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
