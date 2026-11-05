import { API_BASE_URL } from "./config"
import type { WorkOrderConfirmResponse } from "./types"

/**
 * 人工确认 / 取消待建工单。
 * 这是唯一会触发写操作的入口，只有用户在确认卡片上点击才会调用。
 */
export async function confirmWorkorder(
  token: string,
  action: "confirm" | "cancel" = "confirm"
): Promise<WorkOrderConfirmResponse> {
  const resp = await fetch(`${API_BASE_URL}/workorder/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm_token: token, action }),
  })
  if (!resp.ok) {
    throw new Error(`确认请求失败：HTTP ${resp.status}`)
  }
  return (await resp.json()) as WorkOrderConfirmResponse
}
