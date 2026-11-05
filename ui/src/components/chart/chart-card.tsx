"use client"

import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts"
import type { ChartSpec } from "@/lib/api/types"

const AXIS_PROPS = {
  tick: { fill: "#a1a1aa", fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: "#e8e8ea" },
  interval: "preserveStartEnd" as const,
  minTickGap: 28,
}

const TOOLTIP_PROPS = {
  contentStyle: {
    background: "#ffffff",
    border: "1px solid #e8e8ea",
    borderRadius: 10,
    boxShadow: "0 4px 16px rgba(17,17,19,0.06)",
    fontSize: 12,
    padding: "6px 10px",
  },
  labelStyle: { color: "#7c7c85", fontSize: 11, marginBottom: 2 },
  itemStyle: { color: "#111113", fontSize: 12 },
  cursor: { stroke: "#e4e4e7", strokeDasharray: "4 4" },
}

/** 依据数据与参考线计算 Y 轴范围，避免参考线被裁剪到边缘 */
function yDomain(spec: ChartSpec): [number, number] {
  const values: number[] = []
  for (const row of spec.data) {
    for (const s of spec.series) {
      const v = row[s.key]
      if (typeof v === "number" && Number.isFinite(v)) values.push(v)
    }
  }
  for (const r of spec.ref_lines ?? []) values.push(r.y)
  if (values.length === 0) return [0, 1]
  const min = Math.min(...values)
  const max = Math.max(...values)
  const pad = (max - min) * 0.08 || 1
  return [Math.floor(min - pad), Math.ceil(max + pad)]
}

export function ChartCard({ spec }: { spec: ChartSpec }) {
  const domain = yDomain(spec)
  const unit = spec.unit ?? ""
  const showLegend = spec.series.length > 1

  const commonAxis = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f2" vertical={false} />
      <XAxis dataKey="t" {...AXIS_PROPS} />
      <YAxis domain={domain} width={44} {...AXIS_PROPS} minTickGap={20} />
      <Tooltip {...TOOLTIP_PROPS} formatter={(value) => `${value ?? "-"}${unit}`} />
      {showLegend && (
        <Legend
          verticalAlign="top"
          align="right"
          height={20}
          iconType="plainline"
          iconSize={12}
          wrapperStyle={{ fontSize: 11, color: "#7c7c85", paddingBottom: 4 }}
        />
      )}
    </>
  )

  const refLines = (spec.ref_lines ?? []).map((r) => (
    <ReferenceLine
      key={`${r.label}-${r.y}`}
      y={r.y}
      stroke="#d4d4d8"
      strokeDasharray="5 4"
      ifOverflow="extendDomain"
      label={{ value: r.label, position: "insideTopRight", fill: "#a1a1aa", fontSize: 10 }}
    />
  ))

  const chart =
    spec.kind === "bar" ? (
      <BarChart data={spec.data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        {commonAxis}
        <Bar dataKey={spec.series[0].key} name={spec.series[0].name} fill="#111113" radius={[4, 4, 0, 0]} maxBarSize={56} />
        {refLines}
      </BarChart>
    ) : (
      <LineChart data={spec.data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        {commonAxis}
        {spec.series.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.style === "dashed" ? "#a1a1aa" : "#111113"}
            strokeWidth={s.style === "dashed" ? 1.4 : 1.8}
            strokeDasharray={s.style === "dashed" ? "5 4" : undefined}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0, fill: s.style === "dashed" ? "#a1a1aa" : "#111113" }}
            isAnimationActive={false}
          />
        ))}
        {refLines}
      </LineChart>
    )

  return (
    <div className="w-full">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <div className="text-xs font-medium text-foreground">{spec.title}</div>
        <div className="text-[11px] text-muted-foreground">
          {spec.y_label}
          {spec.meta?.slope_per_hour !== undefined && ` · 斜率 ${spec.meta.slope_per_hour}/h`}
        </div>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chart}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
