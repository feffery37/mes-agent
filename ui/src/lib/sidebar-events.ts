/**
 * 窄屏侧栏抽屉开关事件。
 * layout.tsx 是 Server Component，顶栏按钮无法直接改侧栏内部状态，用 CustomEvent 解耦。
 */

export const SIDEBAR_TOGGLE_EVENT = "imes:sidebar-toggle"

export function emitSidebarToggle(): void {
  window.dispatchEvent(new Event(SIDEBAR_TOGGLE_EVENT))
}
