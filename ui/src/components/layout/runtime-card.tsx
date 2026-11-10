"use client"

import { useEffect, useState } from "react"
import { Activity } from "lucide-react"
import { fetchStatus } from "@/lib/api/status"
import type { StatusResponse } from "@/lib/api/types"

export function RuntimeCard({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () => {
      fetchStatus()
        .then((data) => {
          if (!alive) return
          setStatus(data)
          setOffline(false)
        })
        .catch(() => {
          if (alive) setOffline(true)
        })
    }
    load()
    const timer = window.setInterval(load, 30_000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [])

  if (compact) {
    return (
      <span
        title={offline ? "服务离线" : `在线 · ${status?.llm_model ?? ""}`}
        className={`inline-block h-2 w-2 rounded-full ${offline ? "bg-destructive" : "bg-foreground"}`}
      />
    )
  }

  const rows = [
    { label: "服务", value: offline ? "离线" : status ? `在线 · ${Math.round(status.uptime_seconds)}s` : "连接中…" },
    { label: "模型", value: status ? `${status.llm_provider} / ${status.llm_model}` : "—" },
    { label: "环境", value: status ? `${status.env} · ${status.agent_max_iterations} 轮` : "—" },
  ]

  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 px-2 text-[11px] font-medium tracking-wide text-muted-foreground">
        <Activity className="h-3 w-3" strokeWidth={1.8} />
        运行状态
      </div>
      <div className="mx-1 rounded-lg border border-border bg-background px-2.5 py-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-2 py-0.5 text-[11px]">
            <span className="shrink-0 text-muted-foreground">{row.label}</span>
            <span className="truncate text-right font-mono text-foreground/80" title={row.value}>
              {row.value}
            </span>
          </div>
        ))}
        <div className="mt-1.5 border-t border-border pt-1.5 text-[10px] leading-relaxed text-muted-foreground">
          数据来自 /api/status，30 秒刷新；侧栏不触发分析或通知
        </div>
      </div>
    </div>
  )
}
