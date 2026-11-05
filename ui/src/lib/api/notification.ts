import { API_BASE_URL } from "./config"
import type { NotificationConfirmResponse } from "./types"

/**
 * 人工确认 / 忽略对外通知草稿。
 * 这是唯一会真正发送消息的入口，只有用户在确认卡片上点击才会调用。
 */
export async function confirmNotification(
  token: string,
  action: "send" | "cancel" = "send"
): Promise<NotificationConfirmResponse> {
  const resp = await fetch(`${API_BASE_URL}/notify/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm_token: token, action }),
  })
  if (!resp.ok) {
    throw new Error(`确认请求失败：HTTP ${resp.status}`)
  }
  return (await resp.json()) as NotificationConfirmResponse
}
