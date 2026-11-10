import type { Metadata } from "next"
import "./globals.css"
import { StatusPill } from "@/components/status-pill"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { SidebarToggle } from "@/components/layout/sidebar-toggle"
import { WorkspaceProvider } from "@/components/layout/workspace-provider"

export const metadata: Metadata = {
  title: "iMES 设备洞察 Agent",
  description: "制造业设备洞察智能体：查现状、看趋势、找原因、问对策",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-border bg-background/80 px-5 py-3 backdrop-blur-xl">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-foreground text-sm font-semibold text-background shadow-sm">
            设
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">iMES 设备洞察 Agent</div>
            <div className="mt-0.5 text-xs text-muted-foreground">查现状 · 看趋势 · 找原因 · 问对策</div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <SidebarToggle />
            <StatusPill />
          </div>
        </header>
        <WorkspaceProvider>
          <div className="flex min-h-0 flex-1">
            <AppSidebar />
            <div className="min-w-0 flex-1">{children}</div>
          </div>
        </WorkspaceProvider>
      </body>
    </html>
  )
}
