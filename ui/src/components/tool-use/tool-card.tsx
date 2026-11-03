"use client"

import { useState } from "react"
import { Wrench, Loader2, ChevronDown, CheckCircle2, XCircle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { ToolCallEvent } from "@/lib/api/types"

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

  return (
    <Card className="overflow-hidden border-border bg-secondary/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-secondary/60"
      >
        <span className="grid h-7 w-7 place-items-center rounded-md bg-primary/15 text-primary">
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

      {open && (
        <div className="space-y-2 border-t border-border px-3 py-2">
          <div>
            <div className="mb-1 text-xs text-muted-foreground">入参</div>
            <pre className="max-h-48 overflow-auto rounded-md bg-background/60 p-2 text-xs text-foreground/90">
              {pretty(tool.function_args)}
            </pre>
          </div>
          {tool.function_result && (
            <div>
              <div className="mb-1 text-xs text-muted-foreground">
                返回{tool.function_result.message ? ` · ${tool.function_result.message}` : ""}
              </div>
              <pre className="max-h-64 overflow-auto rounded-md bg-background/60 p-2 text-xs text-foreground/90">
                {pretty(tool.function_result.data ?? {})}
              </pre>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
