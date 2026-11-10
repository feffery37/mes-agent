"use client"

import { useState } from "react"
import { Send, X, Loader2, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useWorkspace } from "@/components/layout/workspace-provider"
import type { NotificationDraft } from "@/lib/api/types"

const LEVEL_LABEL: Record<string, string> = {
  info: "信息",
  warning: "提醒",
  critical: "高风险",
}

/** 人在回路确认卡片：与侧栏收件箱共用同一份确认状态，避免两处重复发送。 */
export function NotificationConfirmCard({
  token,
  draft,
  expiresIn,
}: {
  token: string
  draft: NotificationDraft
  expiresIn?: number
}) {
  const { resolved, resolve } = useWorkspace()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")
  const resolution = resolved[token]

  const act = async (action: "confirm" | "cancel") => {
    setSubmitting(true)
    setError("")
    try {
      await resolve("notification", token, action)
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败")
    } finally {
      setSubmitting(false)
    }
  }

  const badge =
    resolution?.state === "done" ? (
      <Badge variant="success" className="ml-auto">已发送</Badge>
    ) : resolution?.state === "cancelled" ? (
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
        也可在左侧「待确认」收件箱中处理。
      </p>

      {resolution ? (
        <p className="mt-3 text-xs text-foreground">
          {resolution.state === "done"
            ? `已发送通知${resolution.label ? ` · ${resolution.label}` : ""}`
            : "已忽略，未发送任何通知"}
        </p>
      ) : (
        <>
          {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              disabled={submitting}
              onClick={() => act("confirm")}
              className="h-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="mr-1.5 h-3.5 w-3.5" />
              )}
              发送通知
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={submitting}
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
