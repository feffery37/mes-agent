"use client"

import { useEffect, useRef, useState } from "react"
import { Send, Cpu, Loader2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { ToolUseList } from "@/components/tool-use"
import { useChat } from "@/hooks/use-chat"

const EXAMPLES = [
  "1号机最近温度是不是在上升？会不会出问题？",
  "查一下1号机的型号和控制限",
  "今天1号机有哪些报警？",
  "温度上升了该怎么处理？",
  "给1号机创建一张维修工单",
]

export default function Page() {
  const { turns, send, busy } = useChat()
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [turns])

  const onSend = (text: string) => {
    const t = text.trim()
    if (!t || busy) return
    send(t)
    setInput("")
  }

  return (
    <main className="mx-auto flex h-[calc(100vh-57px)] w-full max-w-3xl flex-col">
      <ScrollArea className="flex-1">
        <div className="space-y-6 px-4 py-6">
          {turns.length === 0 && (
            <div className="mt-10 text-center text-sm text-muted-foreground">
              向设备洞察 Agent 提问，例如「1号机最近温度是不是在上升？」
            </div>
          )}

          {turns.map((turn) => (
            <div key={turn.id} className="space-y-4">
              {/* 用户消息 */}
              <div className="flex items-start gap-3">
                <Avatar className="bg-muted text-muted-foreground">
                  <AvatarFallback>我</AvatarFallback>
                </Avatar>
                <div className="rounded-2xl rounded-tl-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                  {turn.user}
                </div>
              </div>

              {/* 助手消息 */}
              <div className="flex items-start gap-3">
                <Avatar className="bg-gradient-to-br from-brand to-brand-2 text-white">
                  <AvatarFallback>设</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1 space-y-3">
                  {turn.tools.length > 0 && (
                    <details open className="rounded-xl border border-border bg-card/60">
                      <summary className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
                        <Cpu className="h-4 w-4" />
                        执行过程（{turn.tools.length} 个工具调用）
                      </summary>
                      <Separator className="my-1" />
                      <div className="p-3">
                        <ToolUseList tools={turn.tools} />
                      </div>
                    </details>
                  )}

                  {turn.error ? (
                    <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                      ⚠️ {turn.error}
                    </div>
                  ) : turn.answer ? (
                    <div className="markdown text-sm text-foreground/95">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.answer}</ReactMarkdown>
                    </div>
                  ) : (
                    turn.streaming && (
                      <div className="flex items-center gap-2 px-1 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        正在分析设备数据…
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="border-t border-border bg-background/80 px-4 py-3 backdrop-blur">
        <div className="mb-2 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              disabled={busy}
              onClick={() => onSend(ex)}
              className="rounded-full border border-border bg-secondary px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-foreground disabled:opacity-50"
            >
              {ex}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                onSend(input)
              }
            }}
            placeholder="输入设备相关问题，回车发送（Shift+Enter 换行）"
            className="max-h-40"
            rows={1}
          />
          <Button onClick={() => onSend(input)} disabled={busy || !input.trim()} size="icon" aria-label="发送">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </main>
  )
}
