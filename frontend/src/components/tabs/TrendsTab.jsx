import React from "react";
import { LineChart as LineIcon } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { varLabel } from "../../lib/labels.js";
import { Badge, SectionTitle } from "../ui.jsx";

export default function TrendsTab({ result }) {
  const ms = result.measurements || [];
  const trends = Object.fromEntries((result.assessment.drivers_ranked || []).filter((d) => d.temporal_trend).map((d) => [d.variable, d.temporal_trend]));
  if (ms.length === 0) {
    return (
      <div className="card p-10 text-center">
        <LineIcon className="mx-auto h-8 w-8 text-ink-400" />
        <p className="mt-3 font-semibold text-ink-900">No dated measurements for this site</p>
        <p className="mt-1 text-sm text-ink-600">With two or more dated observations per variable, co-declining indicators strengthen the matching hypothesis.</p>
      </div>
    );
  }
  const byVar = {};
  ms.forEach((m) => (byVar[m.variable] = byVar[m.variable] || []).push({ date: String(m.date).slice(0, 10), value: m.value }));

  return (
    <div>
      <SectionTitle icon={LineIcon} title="Measurement history" subtitle="Indicators that decline together with your concern strengthen that explanation in the ranking" />
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {Object.entries(byVar).map(([v, pts]) => {
          const data = pts.sort((x, y) => x.date.localeCompare(y.date));
          const down = data.length > 1 && data[data.length - 1].value < data[0].value;
          const color = down ? "var(--color-clay-500)" : "var(--color-forest-500)";
          const id = `g-${v}`;
          return (
            <div key={v} className="card p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-ink-900">{varLabel(v)}</span>
                {trends[v] && <Badge tone={trends[v] === "declining" ? "clay" : trends[v] === "improving" ? "forest" : "neutral"}>{trends[v]}</Badge>}
              </div>
              <div className="mt-1 text-xs text-ink-600">
                {data[0].value} → <strong className="text-ink-900">{data[data.length - 1].value}</strong> ({data[0].date.slice(0, 4)}–{data[data.length - 1].date.slice(0, 4)})
              </div>
              <div className="mt-2 h-32">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data} margin={{ top: 6, right: 6, left: -22, bottom: 0 }}>
                    <defs>
                      <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                        <stop offset="100%" stopColor={color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--color-sand-100)" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={(d) => d.slice(0, 4)} tick={{ fontSize: 10, fill: "var(--color-ink-400)" }} axisLine={false} tickLine={false} />
                    <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "var(--color-ink-400)" }} axisLine={false} tickLine={false} width={44} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--color-sand-200)", fontSize: 12 }} />
                    <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fill={`url(#${id})`} dot={{ r: 3, fill: color }} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
