"use client"

import {
  Activity,
  Bell,
  BookOpen,
  Gauge,
  LineChart,
  Search,
  Send,
  TrendingUp,
  Wrench,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"

type ActionItem = { label: string; icon: LucideIcon }
type ActionGroup = { label: string; icon: LucideIcon; items: ActionItem[] }

/**
 * 侧栏功能列表：纯前端展示，不绑定任何点击事件、不调用模型或后端接口。
 * 保留分组与图标只是为了让左侧视觉更完整，后续接功能时再单独加交互。
 */
const GROUPS: ActionGroup[] = [
  {
    label: "查现状",
    icon: Search,
    items: [
      { label: "设备与控制限", icon: Search },
      { label: "报警记录", icon: Bell },
    ],
  },
  {
    label: "看趋势",
    icon: TrendingUp,
    items: [
      { label: "稳健趋势", icon: TrendingUp },
      { label: "SPC 判异", icon: Activity },
      { label: "控制图", icon: LineChart },
      { label: "过程能力 Cpk", icon: Gauge },
    ],
  },
  {
    label: "问对策",
    icon: BookOpen,
    items: [
      { label: "SOP 建议", icon: BookOpen },
      { label: "创建工单", icon: Wrench },
      { label: "通知班组", icon: Send },
    ],
  },
]

export function QuickActions({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex flex-col items-center gap-1">
        {GROUPS.flatMap((group) => group.items).map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.label}
              title={item.label}
              className="grid h-9 w-9 place-items-center rounded-lg text-foreground/65 transition-colors hover:bg-secondary hover:text-foreground"
            >
              <Icon className="h-4 w-4" strokeWidth={1.7} />
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {GROUPS.map((group) => {
        const GroupIcon = group.icon
        return (
          <div key={group.label}>
            <div className="mb-1.5 flex items-center gap-1.5 px-2 text-[11px] font-medium tracking-wide text-muted-foreground">
              <GroupIcon className="h-3 w-3" strokeWidth={1.8} />
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.label}
                    className={cn(
                      "group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-foreground/75",
                      "transition-colors hover:bg-secondary hover:text-foreground"
                    )}
                  >
                    <Icon
                      className="h-3.5 w-3.5 shrink-0 text-muted-foreground group-hover:text-foreground"
                      strokeWidth={1.7}
                    />
                    <span className="truncate">{item.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
