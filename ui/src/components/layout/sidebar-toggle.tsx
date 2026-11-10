"use client"

import { PanelLeft } from "lucide-react"
import { emitSidebarToggle } from "@/lib/sidebar-events"

/** 窄屏顶栏的抽屉开关（桌面由 CSS 隐藏） */
export function SidebarToggle() {
  return (
    <button
      type="button"
      onClick={emitSidebarToggle}
      aria-label="打开侧栏"
      className="grid h-8 w-8 place-items-center rounded-lg border border-border text-foreground/70 transition-colors hover:bg-secondary hover:text-foreground lg:hidden"
    >
      <PanelLeft className="h-4 w-4" strokeWidth={1.8} />
    </button>
  )
}
