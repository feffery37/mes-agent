"use client"

import { useState } from "react"
import { Send, X, Loader2, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { confirmNotification } from "@/lib/api/notification"
import type { NotificationDraft } from "@/lib/api/types"

const LEVEL_LABEL: Record<string, string> = {
  info: "信息",
  warning: "提醒",
  critical: "高风险",
}

type CardState = "idle" | "submitting" | "sent" | "cancelled" | "error"

/** 人在回路确认卡片：对外通知必须由此处的人工点击触发。 */
export function NotificationConfirmCard({
  token,
  draft,
  expiresIn,
}: {
  token: string
  draft: NotificationDraft
  expiresIn?: number
}) {
  const [state, setState] = useState<CardState>("idle")
  const [error, setError] = useState("")

  const act = async (action: "send" | "cancel") => {
    setState("submitting")
    setError("")
    try {
      const res = await confirmNotification(token, action)
      if (!res.success) throw new Error(res.message || "操作失败")
      setState(action === "cancel" ? "cancelled" : "sent")
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败")
      setState("error")
    }
  }

  const badge =
    state === "sent" ? (
      <Badge variant="success" className="ml-auto">已发送</Badge>
    ) : state === "cancelled" ? (
      <Badge className="ml-auto">已忽略</Badge>
    ) : (
      <Badge variant="warning" className="ml-auto">待人工确认</Badge>
    )

  return (
    <div className="rounded-xl border border-foreground/20 bg-secondary/30 px-3.5 py-3">
      <div className="flex items-center gap-2 text-foreground">
        <Bell className="h-4 w-4" strokeWidth={1.8} />
        <span className="text-xs font-medium">人工确认 · 对外通知</span>
        {badge}
      </div>

      <div className="mt-2.5 space-y-1.5 text-xs">
        <div>
          <span className="text-muted-foreground">标题：</span>
          {draft.title}
        </div>
        <pre className="whitespace-pre-wrap rounded-lg bg-secondary/70 p-2 font-mono text-[11px] leading-relaxed">
          {draft.body}
        </pre>
        <div className="text-muted-foreground">
          级别：{LEVEL_LABEL[draft.level] ?? draft.level} · 渠道：
          {draft.channels?.length ? draft.channels.join("、") : "默认"}
        </div>
      </div>

      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        Agent 只能生成草稿，发送需你确认后才会执行
        {expiresIn ? ` · ${Math.round(expiresIn / 60)} 分钟内有效` : ""}。
      </p>

      {state === "sent" || state === "cancelled" ? (
        <p className="mt-3 text-xs text-foreground">
          {state === "sent" ? "已发送通知" : "已忽略，未发送任何通知"}
        </p>
      ) : (
        <>
          {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              disabled={state === "submitting"}
              onClick={() => act("send")}
              className="h-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {state === "submitting" ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="mr-1.5 h-3.5 w-3.5" />
              )}
              发送通知
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={state === "submitting"}
              onClick={() => act("cancel")}
              className="h-8 rounded-lg"
            >
              <X className="mr-1.5 h-3.5 w-3.5" />
              忽略
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
