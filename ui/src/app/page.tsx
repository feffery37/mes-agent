"use client"

import { useEffect, useRef, useState } from "react"
import { Send, Cpu, Loader2, Sparkles, ArrowUpRight, ChevronDown } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
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
    <main className="mx-auto flex h-[calc(100dvh-61px)] w-full max-w-3xl flex-col">
      <ScrollArea className="flex-1">
        <div className="space-y-7 px-5 py-7">
          {turns.length === 0 && (
            <div className="mx-auto mt-6 max-w-xl">
              <div className="flex flex-col items-center text-center">
                <div className="grid h-12 w-12 place-items-center rounded-2xl border border-border bg-secondary text-foreground shadow-sm">
                  <Sparkles className="h-5 w-5" strokeWidth={1.6} />
                </div>
                <h1 className="mt-5 text-xl font-semibold tracking-tight">今天想了解哪台设备？</h1>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  用自然语言提问，Agent 会自动查询、分析并给出结论
                </p>
              </div>

              <div className="mt-8 grid gap-2 sm:grid-cols-2">
                {EXAMPLES.slice(0, 4).map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    disabled={busy}
                    onClick={() => onSend(ex)}
                    className="group flex items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground/80 transition-all hover:-translate-y-0.5 hover:border-foreground/25 hover:shadow-sm disabled:opacity-50"
                  >
                    <span className="leading-relaxed">{ex}</span>
                    <ArrowUpRight
                      className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground"
                      strokeWidth={1.8}
                    />
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn) => (
            <div key={turn.id} className="space-y-4">
              {/* 用户消息 */}
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm">
                  {turn.user}
                </div>
              </div>

              {/* 助手消息 */}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-border bg-secondary text-[11px] font-semibold text-foreground">
                  设
                </div>
                <div className="min-w-0 flex-1 space-y-3">
                  {turn.tools.length > 0 && (
                    <details open className="group rounded-xl border border-border bg-secondary/50">
                      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs text-muted-foreground transition-colors hover:text-foreground [&::-webkit-details-marker]:hidden">
                        <Cpu className="h-3.5 w-3.5" strokeWidth={1.8} />
                        执行过程 · {turn.tools.length} 个工具调用
                        <ChevronDown className="ml-auto h-3.5 w-3.5 transition-transform group-open:rotate-180" />
                      </summary>
                      <div className="border-t border-border p-2.5">
                        <ToolUseList tools={turn.tools} />
                      </div>
                    </details>
                  )}

                  {turn.error ? (
                    <div className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm leading-relaxed text-destructive">
                      {turn.error}
                    </div>
                  ) : turn.answer ? (
                    <div className="markdown text-sm leading-relaxed text-foreground/90">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.answer}</ReactMarkdown>
                    </div>
                  ) : (
                    turn.streaming && (
                      <div className="flex items-center gap-2 px-0.5 text-sm text-muted-foreground">
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

      <div className="border-t border-border bg-background/90 px-4 pb-4 pt-3 backdrop-blur">
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              disabled={busy}
              onClick={() => onSend(ex)}
              className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/25 hover:bg-secondary hover:text-foreground disabled:opacity-40"
            >
              {ex}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-2 rounded-2xl border border-input bg-background p-1.5 pl-3 shadow-sm transition-colors focus-within:border-foreground/35">
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
            className="max-h-40 min-h-[36px] border-0 bg-transparent px-0 py-2 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
            rows={1}
          />
          <Button
            onClick={() => onSend(input)}
            disabled={busy || !input.trim()}
            size="icon"
            aria-label="发送"
            className="h-9 w-9 shrink-0 rounded-xl bg-brand text-white hover:bg-brand/90"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </main>
  )
}
