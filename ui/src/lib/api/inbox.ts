import { API_BASE_URL } from "./config"
import type { PendingInboxResponse } from "./types"

/** 只读：拉取待人工确认草稿（维修工单 / 对外通知）。 */
export async function fetchInbox(): Promise<PendingInboxResponse> {
  const resp = await fetch(`${API_BASE_URL}/inbox/pending`, { cache: "no-store" })
  if (!resp.ok) {
    throw new Error(`收件箱读取失败：HTTP ${resp.status}`)
  }
  return (await resp.json()) as PendingInboxResponse
}
