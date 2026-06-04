import { motion } from "framer-motion";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";

import { ChartData, ChartSpec, Row } from "@/lib/types";

const TEAL = "#14B8A6";
const SERIES = ["#14B8A6", "#0D9488", "#F59E0B", "#6366F1", "#DC2626", "#0EA5E9"];
const STATUS_GREEN = "#16A34A";
const STATUS_AMBER = "#F59E0B";
const STATUS_RED = "#DC2626";

type Status = "ON TRACK" | "WATCH" | "AT RISK";

function statusForPct(pct: number): Status {
  if (pct >= 80) return "ON TRACK";
  if (pct >= 50) return "WATCH";
  return "AT RISK";
}
function statusColor(s: Status): string {
  return s === "ON TRACK" ? STATUS_GREEN : s === "WATCH" ? STATUS_AMBER : STATUS_RED;
}

// Semantic slice/point colors by category name (severity, visit status, enrollment
// status); falls back to the teal series palette.
const NAME_COLORS: Record<string, string> = {
  critical: STATUS_RED, major: STATUS_AMBER, minor: TEAL,
  completed: STATUS_GREEN, scheduled: STATUS_AMBER, missed: STATUS_RED,
  "on track": STATUS_GREEN, watch: STATUS_AMBER, "at risk": STATUS_RED,
};
function colorForName(name: unknown, i: number): string {
  return NAME_COLORS[String(name).toLowerCase()] ?? SERIES[i % SERIES.length];
}

// Distinct colors per series for the "healthy vs stalled" multi-line: the healthy
// reference (Munich) reads as a strong blue, the three at-risk sites as separable
// warning colors (red / orange / amber). Falls back to the teal series palette.
const SERIES_COLORS: Record<string, string> = {
  munich: "#2563EB",   // healthy reference — strong blue
  tokyo: "#DC2626",    // at risk — red
  boston: "#EA580C",   // at risk — orange
  toronto: "#D97706",  // at risk — amber
};
function seriesColor(name: string, i: number): string {
  return SERIES_COLORS[name.toLowerCase()] ?? SERIES[i % SERIES.length];
}

function isNumeric(v: unknown): v is number {
  return typeof v === "number" && !Number.isNaN(v);
}

function fieldsPresent(rows: Row[], fields: (string | null | undefined)[]): boolean {
  if (!rows.length) return false;
  const cols = new Set(Object.keys(rows[0]));
  return fields.every((f) => !f || cols.has(f));
}

function numericField(rows: Row[], prefer?: string | null, fallback?: string | null): string | null {
  if (prefer && rows.length && isNumeric(rows[0][prefer])) return prefer;
  if (fallback && rows.length && isNumeric(rows[0][fallback])) return fallback;
  if (rows.length) {
    const n = Object.keys(rows[0]).find((k) => isNumeric(rows[0][k]));
    return n ?? null;
  }
  return null;
}

function Title({ text }: { text?: string | null }) {
  if (!text) return null;
  return <div className="mb-2 text-sm font-semibold text-navy">{text}</div>;
}

// ----- the hero "progress vs target" horizontal bar (color_field === status) -----
function ProgressBar({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  const pctKey = spec.x_field || "pct_of_target";
  const nameKey = spec.y_field || "name";
  const height = Math.max(200, rows.length * 38 + 30);

  const renderEndLabel = (props: any) => {
    const { x, y, width, height: h, value } = props;
    const pct = Number(value);
    const status = statusForPct(pct);
    const color = statusColor(status);
    const cx = x + width + 8;
    const cy = y + h / 2;
    const pillW = status.length * 6.2 + 14;
    return (
      <g>
        <text x={cx} y={cy} dy={4} fontSize={12} fontWeight={600} fill="#334155">
          {pct}%
        </text>
        <rect x={cx + 34} y={cy - 9} width={pillW} height={18} rx={9} fill={color} opacity={0.15} />
        <text x={cx + 34 + pillW / 2} y={cy} dy={4} fontSize={10} fontWeight={700}
              textAnchor="middle" fill={color}>
          {status}
        </text>
      </g>
    );
  };

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart layout="vertical" data={rows} margin={{ left: 8, right: 120, top: 4, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke="#f1f5f9" />
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <YAxis type="category" dataKey={nameKey} width={92} tick={{ fontSize: 11 }} />
          <Bar dataKey={pctKey} radius={[0, 4, 4, 0]} barSize={18} isAnimationActive
               label={renderEndLabel}>
            {rows.map((r, i) => (
              <Cell key={i} fill={statusColor(statusForPct(Number(r[pctKey])))} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function GenericBar({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  const xKey = spec.x_field || Object.keys(rows[0])[0];
  const yKey = numericField(rows, spec.y_field, spec.x_field) || Object.keys(rows[0])[1];
  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ left: 4, right: 16, top: 8, bottom: 8 }}>
          <CartesianGrid stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey={yKey!} fill={TEAL} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Horizontal ranked bar (teal, value labels) — for "by site" rankings where the
// category is the y-axis and the measure is numeric (deviations, screen-failure %).
function RankedBar({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  const valKey = spec.x_field!;
  const nameKey = spec.y_field!;
  const isPct = /pct|rate|%/i.test(valKey);
  const height = Math.max(200, rows.length * 34 + 30);
  const renderLabel = (props: any) => {
    const { x, width, y, height: h, value } = props;
    return (
      <text x={x + width + 6} y={y + h / 2} dy={4} fontSize={11} fontWeight={600} fill="#334155">
        {value}{isPct ? "%" : ""}
      </text>
    );
  };
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart layout="vertical" data={rows} margin={{ left: 8, right: 52, top: 4, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke="#f1f5f9" />
          <XAxis type="number" tick={{ fontSize: 11 }} unit={isPct ? "%" : ""} />
          <YAxis type="category" dataKey={nameKey} width={94} tick={{ fontSize: 11 }} />
          <Bar dataKey={valKey} fill={TEAL} radius={[0, 4, 4, 0]} barSize={16} label={renderLabel} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function pivotSeries(rows: Row[], xKey: string, yKey: string, colorKey: string) {
  const xs: string[] = [];
  const byX: Record<string, Row> = {};
  const series = new Set<string>();
  for (const r of rows) {
    const xv = String(r[xKey]);
    const sv = String(r[colorKey]);
    series.add(sv);
    if (!byX[xv]) {
      byX[xv] = { [xKey]: r[xKey] };
      xs.push(xv);
    }
    byX[xv][sv] = r[yKey];
  }
  return { data: xs.map((x) => byX[x]), series: [...series] };
}

function LineOrArea({ spec, rows, area }: { spec: ChartSpec; rows: Row[]; area?: boolean }) {
  const xKey = spec.x_field!;
  const yKey = numericField(rows, spec.y_field) || spec.y_field!;
  const Chart = area ? AreaChart : LineChart;
  let data = rows;
  let series: string[] = [yKey];
  if (spec.color_field && fieldsPresent(rows, [spec.color_field])) {
    const piv = pivotSeries(rows, xKey, yKey, spec.color_field);
    data = piv.data;
    series = piv.series;
  }
  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <Chart data={data} margin={{ left: 4, right: 16, top: 8, bottom: 8 }}>
          <CartesianGrid stroke="#f1f5f9" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {series.map((s, i) =>
            area ? (
              <Area key={s} type="monotone" dataKey={s} stroke={seriesColor(s, i)}
                    fill={seriesColor(s, i)} fillOpacity={0.2} />
            ) : (
              <Line key={s} type="monotone" dataKey={s} stroke={seriesColor(s, i)}
                    strokeWidth={2} dot={{ r: 3 }} connectNulls />
            ),
          )}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}

function PieView({ spec, rows, donut }: { spec: ChartSpec; rows: Row[]; donut?: boolean }) {
  const valueKey = numericField(rows, spec.x_field, spec.y_field);
  const nameKey = ([spec.y_field, spec.x_field].find((f) => f && f !== valueKey) || "name") as string;
  if (!valueKey) return <Table rows={rows} />;
  return (
    <div style={{ width: "100%", height: 290 }}>
      <ResponsiveContainer>
        <PieChart>
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Pie
            data={rows}
            dataKey={valueKey}
            nameKey={nameKey}
            outerRadius={95}
            innerRadius={donut ? 58 : 0}
            paddingAngle={donut ? 2 : 0}
            label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {rows.map((r, i) => (
              <Cell key={i} fill={colorForName(r[nameKey], i)} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function ScatterView({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  const xKey = spec.x_field!;
  const yKey = spec.y_field!;
  const colorKey = spec.color_field;
  const yIsPct = /pct|rate|%/i.test(yKey);
  const groups = colorKey ? [...new Set(rows.map((r) => String(r[colorKey])))] : [null];
  return (
    <div style={{ width: "100%", height: 310 }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ left: 10, right: 20, top: 12, bottom: 28 }}>
          <CartesianGrid stroke="#f1f5f9" />
          <XAxis
            type="number" dataKey={xKey} name={titleCase(xKey)} tick={{ fontSize: 11 }}
            label={{ value: titleCase(xKey), position: "insideBottom", offset: -14, fontSize: 11, fill: "#64748b" }}
          />
          <YAxis
            type="number" dataKey={yKey} name={titleCase(yKey)} tick={{ fontSize: 11 }} unit={yIsPct ? "%" : ""}
            label={{ value: titleCase(yKey), angle: -90, position: "insideLeft", fontSize: 11, fill: "#64748b" }}
          />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          {colorKey && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {groups.map((g, gi) => (
            <Scatter
              key={g ?? gi}
              name={g ?? undefined}
              data={colorKey ? rows.filter((r) => String(r[colorKey]) === g) : rows}
              fill={g ? colorForName(g, gi) : TEAL}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

// Internal/plumbing columns hidden from user-facing result tables (kept in the
// data + the injected filter; just not surfaced as a "result").
const HIDDEN_COLS = new Set(["sponsor_id"]);

function titleCase(col: string): string {
  return col
    .replace(/_/g, " ")
    .replace(/\bid\b/gi, "ID")
    .replace(/\bpct\b/gi, "%")
    .split(" ")
    .map((w) => (w === "%" || w === "ID" ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(" ");
}

function Table({ rows }: { rows: Row[] }) {
  if (!rows.length) return <p className="text-sm text-slate-400">No rows returned.</p>;
  const cols = Object.keys(rows[0]).filter((c) => !HIDDEN_COLS.has(c));
  return (
    <div className="max-h-72 overflow-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-slate-50 text-slate-500">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-2 py-1.5 font-medium">{titleCase(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((r, i) => (
            <tr key={i} className="border-t border-slate-100">
              {cols.map((c) => (
                <td key={c} className="px-2 py-1 text-slate-700">{String(r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// A chart is "degenerate" (better shown as a table) if its category axis has
// fewer than 2 distinct values, or it keys off a hidden/plumbing column.
function isDegenerate(rows: Row[], categoryField?: string | null): boolean {
  if (!categoryField || HIDDEN_COLS.has(categoryField)) return true;
  const distinct = new Set(rows.map((r) => String(r[categoryField])));
  return distinct.size < 2;
}

export function ChartRenderer({ chart, instant = false }: { chart: ChartData; instant?: boolean }) {
  const { chart_spec: spec, rows } = chart;

  const body = (() => {
    if (spec.type === "none" || !rows?.length) return <Table rows={rows ?? []} />;

    // Defensive: required fields must exist in the data, else fall back to table.
    const needsXY = ["line", "scatter", "area"].includes(spec.type);
    if (needsXY && !fieldsPresent(rows, [spec.x_field, spec.y_field])) return <Table rows={rows} />;

    switch (spec.type) {
      case "bar": {
        // Status-colored progress bar (hero) — always meaningful.
        if (spec.color_field === "status" && fieldsPresent(rows, [spec.x_field, spec.y_field]))
          return <ProgressBar spec={spec} rows={rows} />;
        // Horizontal ranked bar when the category is on Y and the measure is numeric.
        const yIsCategory =
          spec.y_field && spec.x_field &&
          typeof rows[0][spec.y_field] === "string" && isNumeric(rows[0][spec.x_field]);
        if (yIsCategory) {
          if (isDegenerate(rows, spec.y_field)) return <Table rows={rows} />;
          return <RankedBar spec={spec} rows={rows} />;
        }
        if (isDegenerate(rows, spec.x_field)) return <Table rows={rows} />;
        return <GenericBar spec={spec} rows={rows} />;
      }
      case "line":
        return <LineOrArea spec={spec} rows={rows} />;
      case "area":
        return <LineOrArea spec={spec} rows={rows} area />;
      case "pie":
      case "donut":
        if (isDegenerate(rows, spec.y_field || spec.x_field)) return <Table rows={rows} />;
        return <PieView spec={spec} rows={rows} donut={spec.type === "donut"} />;
      case "scatter":
        return <ScatterView spec={spec} rows={rows} />;
      default:
        return <Table rows={rows} />;
    }
  })();

  return (
    <motion.div
      initial={instant ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mt-3 rounded-xl border border-slate-200 bg-white p-3"
    >
      <Title text={spec.title} />
      {body}
    </motion.div>
  );
}
