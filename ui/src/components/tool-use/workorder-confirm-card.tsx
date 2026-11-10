"use client"

import { useState } from "react"
import { Check, X, Loader2, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useWorkspace } from "@/components/layout/workspace-provider"
import type { WorkOrderDraft } from "@/lib/api/types"

const PRIORITY_LABEL: Record<string, string> = {
  low: "低",
  normal: "普通",
  high: "高",
}

/** 人在回路确认卡片：与侧栏收件箱共用同一份确认状态，避免两处重复点击。 */
export function WorkOrderConfirmCard({
  token,
  draft,
  expiresIn,
}: {
  token: string
  draft: WorkOrderDraft
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
      await resolve("workorder", token, action)
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败")
    } finally {
      setSubmitting(false)
    }
  }

  const badge =
    resolution?.state === "done" ? (
      <Badge variant="success" className="ml-auto">已创建</Badge>
    ) : resolution?.state === "cancelled" ? (
      <Badge className="ml-auto">已取消</Badge>
    ) : (
      <Badge variant="warning" className="ml-auto">待人工确认</Badge>
    )

  return (
    <div className="rounded-xl border border-foreground/20 bg-secondary/30 px-3.5 py-3">
      <div className="flex items-center gap-2 text-foreground">
        <ShieldCheck className="h-4 w-4" strokeWidth={1.8} />
        <span className="text-xs font-medium">人工确认 · 维修工单</span>
        {badge}
      </div>

      <dl className="mt-2.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-muted-foreground">设备 ID</dt>
        <dd className="font-mono">{draft.eid}</dd>
        <dt className="text-muted-foreground">工单标题</dt>
        <dd>{draft.title}</dd>
        <dt className="text-muted-foreground">优先级</dt>
        <dd>{PRIORITY_LABEL[draft.priority] ?? draft.priority}</dd>
      </dl>

      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        Agent 只能生成申请，写操作需你确认后才会执行
        {expiresIn ? ` · ${Math.round(expiresIn / 60)} 分钟内有效` : ""}。
        也可在左侧「待确认」收件箱中处理。
      </p>

      {resolution ? (
        <p className="mt-3 text-xs text-foreground">
          {resolution.state === "done" ? (
            <>
              已创建工单 <span className="font-mono font-medium">{resolution.label}</span>（confirmed_by=user）
            </>
          ) : (
            "已取消，未创建任何工单"
          )}
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
                <Check className="mr-1.5 h-3.5 w-3.5" />
              )}
              确认建单
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={submitting}
              onClick={() => act("cancel")}
              className="h-8 rounded-lg"
            >
              <X className="mr-1.5 h-3.5 w-3.5" />
              取消
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
