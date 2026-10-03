/** Lightweight, dependency-free SVG charts tuned for the intel2doc palette. */

const TEAL = "#1f9d72";
const AMBER = "#d98324";
const BLUE = "#0b64d1";
const INK = "#5b6b76";

export function AreaChart({
  data,
  height = 190,
}: {
  data: { date: string; total: number; auto: number; review: number }[];
  height?: number;
}) {
  const w = 640;
  const h = height;
  const pad = { l: 8, r: 8, t: 12, b: 20 };
  const max = Math.max(...data.map((d) => d.total), 1);
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const x = (i: number) => pad.l + (i / Math.max(data.length - 1, 1)) * iw;
  const y = (v: number) => pad.t + ih - (v / max) * ih;

  const line = (key: "total" | "auto") =>
    data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(" ");
  const area =
    `M${x(0)},${y(data[0]?.total ?? 0)} ` +
    data.map((d, i) => `L${x(i).toFixed(1)},${y(d.total).toFixed(1)}`).join(" ") +
    ` L${x(data.length - 1)},${pad.t + ih} L${x(0)},${pad.t + ih} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
      <defs>
        <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={TEAL} stopOpacity="0.28" />
          <stop offset="100%" stopColor={TEAL} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#areaFill)" />
      <path d={line("total")} fill="none" stroke={TEAL} strokeWidth="2.5" />
      <path d={line("auto")} fill="none" stroke={BLUE} strokeWidth="2" strokeDasharray="4 4" opacity="0.75" />
      {data.map((d, i) =>
        i % 5 === 0 ? (
          <text key={i} x={x(i)} y={h - 4} fontSize="9" fill={INK} textAnchor="middle">
            {d.date.slice(5)}
          </text>
        ) : null
      )}
    </svg>
  );
}

export function BarChart({
  data,
  color = TEAL,
}: {
  data: { label: string; value: number }[];
  color?: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {data.map((d) => (
        <div key={d.label} style={{ display: "grid", gridTemplateColumns: "140px 1fr 52px", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, color: INK, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={d.label}>
            {d.label}
          </span>
          <div style={{ background: "#eef2f4", borderRadius: 8, height: 16, overflow: "hidden" }}>
            <div style={{ width: `${(d.value / max) * 100}%`, height: "100%", background: color, borderRadius: 8, transition: "width .6s cubic-bezier(.2,.8,.2,1)" }} />
          </div>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#16232b", textAlign: "right" }}>{d.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export function Donut({
  segments,
  size = 168,
}: {
  segments: { label: string; value: number; color: string }[];
  size?: number;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = size / 2 - 16;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {segments.map((s) => {
            const frac = s.value / total;
            const dash = frac * c;
            const el = (
              <circle
                key={s.label}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth="18"
                strokeDasharray={`${dash} ${c - dash}`}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
              />
            );
            offset += dash;
            return el;
          })}
        </g>
        <text x="50%" y="47%" textAnchor="middle" fontSize="22" fontWeight="800" fill="#16232b">
          {Math.round((segments[0].value / total) * 100)}%
        </text>
        <text x="50%" y="60%" textAnchor="middle" fontSize="10" fill={INK}>
          {segments[0].label}
        </text>
      </svg>
      <div style={{ display: "grid", gap: 8 }}>
        {segments.map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
            <span style={{ width: 11, height: 11, borderRadius: 3, background: s.color }} />
            <span style={{ color: INK }}>{s.label}</span>
            <b style={{ marginLeft: "auto", color: "#16232b" }}>{s.value.toLocaleString()}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

export { TEAL, AMBER, BLUE };
