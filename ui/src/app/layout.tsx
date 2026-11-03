import type { Metadata } from "next"
import "./globals.css"
import { StatusPill } from "@/components/status-pill"

export const metadata: Metadata = {
  title: "iMES 设备洞察 Agent",
  description: "制造业设备洞察智能体：查现状、看趋势、找原因、问对策",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-border bg-background/80 px-4 py-3 backdrop-blur">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand to-brand-2 font-bold text-white">
            设
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold">iMES 设备洞察 Agent</div>
            <div className="text-xs text-muted-foreground">查现状 · 看趋势 · 找原因 · 问对策</div>
          </div>
          <div className="ml-auto">
            <StatusPill />
          </div>
        </header>
        {children}
      </body>
    </html>
  )
}
