/**
 * 与后端 SSE 事件格式对齐的类型定义。
 * 后端 /api/chat/stream 以 `data: {json}` 逐行推送，顶层即事件对象，type 字段区分事件类型。
 */

export interface ToolResult {
  success: boolean
  message?: string
  data?: unknown
}

/** 图表规格：后端 plot_* 工具产出，前端用 Recharts 渲染 */
export interface ChartSeries {
  /** 对应 data 中的字段名 */
  key: string
  name: string
  style?: "solid" | "dashed"
}

export interface ChartRefLine {
  y: number
  label: string
}

export interface ChartSpec {
  kind: "line" | "bar"
  title: string
  x_label?: string
  y_label?: string
  unit?: string
  data: Array<Record<string, string | number>>
  series: ChartSeries[]
  ref_lines?: ChartRefLine[]
  meta?: Record<string, unknown>
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
  /** 可选：本轮决策的模型思维链（reasoning_content），无则为 null */
  reasoning?: string | null
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
  /** 可选：最终回答对应的模型思维链（reasoning_content），无则为 null */
  reasoning?: string | null
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

/** 待人工确认的维修工单申请（由 create_workorder 返回） */
export interface WorkOrderDraft {
  eid: number
  title: string
  priority: string
}

export interface PendingConfirmation {
  status: "pending_confirmation"
  confirm_token: string
  draft: WorkOrderDraft
  expires_in_seconds?: number
}

/** POST /api/workorder/confirm 返回 */
export interface WorkOrderConfirmResponse {
  success: boolean
  message?: string
  data?: {
    status: string
    confirm_token?: string
    workorder?: Record<string, unknown>
  }
}

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
