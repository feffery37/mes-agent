/**
 * API 基地址。
 * 开发环境默认直连后端 http://localhost:8000/api；
 * 生产构建可通过环境变量覆盖为相对路径 /api（由 Nginx 反向代理）。
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"
