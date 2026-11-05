"use client"

import { useState } from "react"
import { Wrench, Loader2, ChevronDown, CheckCircle2, XCircle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChartCard } from "@/components/chart/chart-card"
import { cn } from "@/lib/utils"
import type { ChartSpec, ToolCallEvent } from "@/lib/api/types"

function pretty(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function ToolCard({ tool }: { tool: ToolCallEvent }) {
  const [open, setOpen] = useState(false)
  const calling = tool.status === "calling"
  const ok = tool.function_result?.success !== false
  // 图表工具的返回里带 chart spec，直接渲染成图，JSON 区里用占位符代替
  const resultData = tool.function_result?.data as { chart?: ChartSpec } | undefined
  const chart = resultData?.chart
  const jsonData = chart ? { ...resultData, chart: "[已在下方渲染为图表]" } : (tool.function_result?.data ?? {})

  return (
    <Card className="overflow-hidden border-border bg-background shadow-none">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-secondary"
      >
        <span className="grid h-7 w-7 place-items-center rounded-md border border-border bg-secondary text-foreground">
          {calling ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wrench className="h-4 w-4" />
          )}
        </span>
        <span className="font-mono text-sm text-foreground">{tool.function_name}</span>
        {calling ? (
          <Badge variant="warning" className="ml-auto">
            调用中
          </Badge>
        ) : ok ? (
          <Badge variant="success" className="ml-auto">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            已调用
          </Badge>
        ) : (
          <Badge variant="destructive" className="ml-auto">
            <XCircle className="mr-1 h-3 w-3" />
            失败
          </Badge>
        )}
        <ChevronDown
          className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>

      {chart && (
        <div className="border-t border-border px-3 py-3">
          <ChartCard spec={chart} />
        </div>
      )}

      {open && (
        <div className="space-y-2 border-t border-border px-3 py-2">
          <div>
            <div className="mb-1 text-xs text-muted-foreground">入参</div>
            <pre className="max-h-48 overflow-auto rounded-lg bg-secondary p-2 font-mono text-xs text-foreground/80">
              {pretty(tool.function_args)}
            </pre>
          </div>
          {tool.function_result && (
            <div>
              <div className="mb-1 text-xs text-muted-foreground">
                返回{tool.function_result.message ? ` · ${tool.function_result.message}` : ""}
              </div>
              <pre className="max-h-64 overflow-auto rounded-lg bg-secondary p-2 font-mono text-xs text-foreground/80">
                {pretty(jsonData)}
              </pre>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
