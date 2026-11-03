import { API_BASE_URL } from "./config"
import type { StatusResponse } from "./types"

export async function fetchStatus(signal?: AbortSignal): Promise<StatusResponse> {
  const resp = await fetch(`${API_BASE_URL}/status`, { signal })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return (await resp.json()) as StatusResponse
}
