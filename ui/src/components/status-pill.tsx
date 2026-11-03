"use client"

import { useEffect, useState } from "react"
import { fetchStatus } from "@/lib/api/status"
import { Badge } from "@/components/ui/badge"

export function StatusPill() {
  const [text, setText] = useState<string>("连接中…")
  const [online, setOnline] = useState<boolean>(false)

  useEffect(() => {
    const load = async () => {
      try {
        const s = await fetchStatus()
        setOnline(true)
        setText(`${s.llm_provider} / ${s.llm_model}`)
      } catch {
        setOnline(false)
        setText("离线")
      }
    }
    load()
  }, [])

  return (
    <Badge variant={online ? "success" : "destructive"}>
      <span
        className={`mr-1 inline-block h-2 w-2 rounded-full ${
          online ? "bg-brand-2" : "bg-destructive"
        }`}
      />
      {text}
    </Badge>
  )
}
