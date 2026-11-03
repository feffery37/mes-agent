/**
 * 与后端 SSE 事件格式对齐的类型定义。
 * 后端 /api/chat/stream 以 `data: {json}` 逐行推送，顶层即事件对象，type 字段区分事件类型。
 */

export interface ToolResult {
  success: boolean
  message?: string
  data?: unknown
}

/** 工具调用事件：status 为 calling（调用中）/ called（已返回） */
export interface ToolCallEvent {
  id: string
  type: "tool"
  created_at: string
  tool_call_id: string
  tool_name: string
  function_name: string
  function_args: Record<string, unknown>
  function_result: ToolResult | null
  status: "calling" | "called"
  /** 可选：工具执行的简短说明（部分工具提供） */
  summary?: string
}

/** 助手消息事件 */
export interface AssistantMessageEvent {
  id: string
  type: "message"
  created_at: string
  role: "assistant"
  message: string
  attachments: unknown[]
}

export interface ErrorEvent {
  type: "error"
  error: string
}

export interface DoneEvent {
  type: "done"
}

export type SSEEvent = ToolCallEvent | AssistantMessageEvent | ErrorEvent | DoneEvent

/** GET /api/status 返回 */
export interface StatusResponse {
  service: string
  env: string
  llm_provider: string
  llm_model: string
  agent_max_iterations: number
  uptime_seconds: number
  status: string
}
