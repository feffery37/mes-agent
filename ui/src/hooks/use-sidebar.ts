"use client"

import { useCallback, useEffect, useState } from "react"
import { SIDEBAR_TOGGLE_EVENT } from "@/lib/sidebar-events"

const STORAGE_KEY = "imes.sidebar.collapsed"

/** 侧栏折叠（桌面，持久化）与抽屉开关（窄屏）状态。 */
export function useSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(STORAGE_KEY) === "1")
    const toggle = () => setMobileOpen((value) => !value)
    const closeOnDesktop = () => {
      if (window.innerWidth >= 1024) setMobileOpen(false)
    }
    window.addEventListener(SIDEBAR_TOGGLE_EVENT, toggle)
    window.addEventListener("resize", closeOnDesktop)
    return () => {
      window.removeEventListener(SIDEBAR_TOGGLE_EVENT, toggle)
      window.removeEventListener("resize", closeOnDesktop)
    }
  }, [])

  const toggleCollapsed = useCallback(() => {
    setCollapsed((previous) => {
      const next = !previous
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0")
      return next
    })
  }, [])

  const closeMobile = useCallback(() => setMobileOpen(false), [])

  return { collapsed, toggleCollapsed, mobileOpen, closeMobile }
}
