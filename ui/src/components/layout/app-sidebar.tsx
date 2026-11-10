"use client"

import { useEffect } from "react"
import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { useSidebar } from "@/hooks/use-sidebar"
import { cn } from "@/lib/utils"
import { QuickActions } from "./quick-actions"
import { RuntimeCard } from "./runtime-card"

/** 左侧工作台：桌面常驻（可折叠），窄屏为抽屉。内容均为只读展示。 */
export function AppSidebar() {
  const { collapsed, toggleCollapsed, mobileOpen, closeMobile } = useSidebar()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMobile()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [closeMobile])

  const renderContent = (compact: boolean, onClose?: () => void) => (
    <>
      <div
        className={cn(
          "flex h-11 shrink-0 items-center border-b border-border px-3",
          compact ? "justify-center" : "justify-between"
        )}
      >
        {!compact && (
          <span className="text-[11px] font-medium tracking-wide text-muted-foreground">工作台</span>
        )}
        <button
          type="button"
          onClick={onClose ?? toggleCollapsed}
          aria-label={onClose ? "关闭侧栏" : compact ? "展开侧栏" : "折叠侧栏"}
          className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          {onClose ? (
            <X className="h-4 w-4" strokeWidth={1.8} />
          ) : compact ? (
            <ChevronRight className="h-4 w-4" strokeWidth={1.8} />
          ) : (
            <ChevronLeft className="h-4 w-4" strokeWidth={1.8} />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        <QuickActions compact={compact} />
        <div className="my-3 h-px bg-border" />
        {compact ? (
          <div className="flex justify-center">
            <RuntimeCard compact />
          </div>
        ) : (
          <RuntimeCard />
        )}
      </div>

      {!compact && (
        <div className="shrink-0 border-t border-border px-3 py-2 text-[10px] text-muted-foreground">
          P0 侧栏 · 只读展示
        </div>
      )}
    </>
  )

  return (
    <>
      <aside
        className={cn(
          "sticky top-0 hidden h-[calc(100dvh-61px)] shrink-0 flex-col border-r border-border bg-secondary/30 lg:flex",
          collapsed ? "w-14" : "w-60"
        )}
      >
        {renderContent(collapsed)}
      </aside>

      {mobileOpen && (
        <div className="lg:hidden">
          <div
            className="fixed inset-x-0 bottom-0 top-[61px] z-30 bg-foreground/10"
            onClick={closeMobile}
            aria-hidden="true"
          />
          <aside className="fixed left-0 top-[61px] z-40 flex h-[calc(100dvh-61px)] w-64 flex-col border-r border-border bg-background shadow-lg">
            {renderContent(false, closeMobile)}
          </aside>
        </div>
      )}
    </>
  )
}
