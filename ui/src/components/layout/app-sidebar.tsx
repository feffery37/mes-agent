"use client"

import { useEffect, useState } from "react"
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Inbox,
  LayoutGrid,
  MessageSquare,
  Plus,
  X,
  type LucideIcon,
} from "lucide-react"
import { useSidebar } from "@/hooks/use-sidebar"
import { cn } from "@/lib/utils"
import { QuickActions } from "./quick-actions"
import { RuntimeCard } from "./runtime-card"
import { SessionList } from "./session-list"
import { PendingInbox } from "./pending-inbox"
import { useWorkspace, type SidebarTab } from "./workspace-provider"

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
  count,
}: {
  active: boolean
  onClick: () => void
  icon: LucideIcon
  label: string
  count?: number
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs transition-colors",
        active
          ? "bg-secondary text-foreground"
          : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
      )}
    >
      <Icon className="h-3.5 w-3.5" strokeWidth={1.7} />
      {label}
      {!!count && (
        <span className="grid h-4 min-w-4 place-items-center rounded-full bg-foreground px-1 text-[10px] font-medium text-background">
          {count}
        </span>
      )}
    </button>
  )
}

/** 左侧工作台（P1）：会话列表 + 待确认收件箱 + 纯展示功能列表 + 运行状态。 */
export function AppSidebar() {
  const { collapsed, toggleCollapsed, mobileOpen, closeMobile } = useSidebar()
  const { tab, setTab, inbox, newSession } = useWorkspace()
  const [featuresOpen, setFeaturesOpen] = useState(false)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMobile()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [closeMobile])

  const openTab = (next: SidebarTab) => {
    setTab(next)
    if (collapsed) toggleCollapsed()
  }

  const compactButton =
    "grid h-9 w-9 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"

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

      {compact ? (
        <div className="flex flex-1 flex-col items-center gap-1 px-2 py-3">
          <button
            type="button"
            title="新建会话"
            aria-label="新建会话"
            onClick={() => {
              newSession()
              if (collapsed) toggleCollapsed()
            }}
            className={compactButton}
          >
            <Plus className="h-4 w-4" strokeWidth={1.8} />
          </button>
          <button type="button" title="会话列表" aria-label="会话列表" onClick={() => openTab("sessions")} className={compactButton}>
            <MessageSquare className="h-4 w-4" strokeWidth={1.8} />
          </button>
          <button
            type="button"
            title="待确认收件箱"
            aria-label="待确认收件箱"
            onClick={() => openTab("inbox")}
            className={cn("relative", compactButton)}
          >
            <Inbox className="h-4 w-4" strokeWidth={1.8} />
            {inbox.length > 0 && (
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-foreground" />
            )}
          </button>
          <div className="my-1.5 h-px w-6 bg-border" />
          <button
            type="button"
            title="功能列表（纯展示）"
            aria-label="功能列表"
            onClick={() => {
              toggleCollapsed()
              setFeaturesOpen(true)
            }}
            className={compactButton}
          >
            <LayoutGrid className="h-4 w-4" strokeWidth={1.8} />
          </button>
          <div className="mt-auto py-2">
            <RuntimeCard compact />
          </div>
        </div>
      ) : (
        <>
          <div className="flex shrink-0 gap-1 border-b border-border px-2 py-2">
            <TabButton
              active={tab === "sessions"}
              onClick={() => setTab("sessions")}
              icon={MessageSquare}
              label="会话"
            />
            <TabButton
              active={tab === "inbox"}
              onClick={() => setTab("inbox")}
              icon={Inbox}
              label="待确认"
              count={inbox.length}
            />
          </div>

          <div className="flex min-h-0 flex-1 flex-col px-2 py-2.5">
            {tab === "sessions" ? <SessionList onNavigate={onClose} /> : <PendingInbox />}
          </div>

          <div className="shrink-0 border-t border-border">
            <button
              type="button"
              onClick={() => setFeaturesOpen((value) => !value)}
              className="flex w-full items-center gap-1.5 px-3 py-2 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
            >
              <LayoutGrid className="h-3 w-3" strokeWidth={1.8} />
              功能列表
              <ChevronDown
                className={cn("ml-auto h-3 w-3 transition-transform", featuresOpen && "rotate-180")}
              />
            </button>
            {featuresOpen && (
              <div className="max-h-52 overflow-y-auto px-2 pb-2">
                <QuickActions />
              </div>
            )}
          </div>

          <div className="shrink-0 border-t border-border px-2 py-2">
            <RuntimeCard />
          </div>
          <div className="shrink-0 border-t border-border px-3 py-1.5 text-[10px] text-muted-foreground">
            P1 侧栏 · 会话与收件箱
          </div>
        </>
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
