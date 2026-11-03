"use client"

import { ToolCard } from "./tool-card"
import type { ToolCallEvent } from "@/lib/api/types"

export function ToolUseList({ tools }: { tools: ToolCallEvent[] }) {
  if (tools.length === 0) return null
  return (
    <div className="space-y-2">
      {tools.map((t) => (
        <ToolCard key={t.tool_call_id} tool={t} />
      ))}
    </div>
  )
}

export { ToolCard }
