import { useEffect, useState } from "react";
import { getDashboard, runAnalyze, type DashboardData, type Insight } from "../api";
import { useAuth } from "../auth";
import { AreaChart, BarChart, Donut, TEAL, AMBER } from "../components/Charts";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function Dashboard() {
  const { can, user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard().then(setData).catch((e) => setError(String(e.message || e)));
  }, []);

  async function analyze() {
    setAnalyzing(true);
    try {
      setInsights((await runAnalyze()).insights);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  }

  const s = data?.summary;
  return (
    <div className="page">
      <PageHead
        title={`Welcome, ${user?.name.split(" ")[0] ?? ""}`}
        subtitle="Operational overview — last 30 days"
        actions={
          can("dashboard.analyze") && (
            <button className="btn btn-analyze" data-tour="analyze-btn" onClick={analyze} disabled={analyzing}>
              {analyzing ? <span className="spinner" /> : <><Icon name="sparkle" size={17} /> Analyze</>}
            </button>
          )
        }
      />

      {error && <div className="alert">⚠ {error}</div>}

      {insights && (
        <div className="insights">
          {insights.map((it, i) => (
            <div className={`insight ${it.tone}`} key={i}>
              <div className="insight-ic"><Icon name="sparkle" size={16} /></div>
              <div>
                <div className="insight-title">{it.title}</div>
                <div className="insight-detail">{it.detail}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {s && (
        <div className="kpis">
          <Kpi label="Documents (30d)" value={s.documents_30d.toLocaleString()} trend={`+${s.trend_pct}%`} icon="file" />
          <Kpi label="Straight-through" value={`${Math.round(s.straight_through_rate * 100)}%`} sub={`${s.auto_approved.toLocaleString()} auto-approved`} icon="check" tone="teal" />
          <Kpi label="In review" value={s.in_review.toLocaleString()} sub="awaiting a human" icon="bell" tone="amber" />
          <Kpi label="Avg confidence" value={`${Math.round(s.avg_confidence * 100)}%`} sub={`${(s.accuracy * 100).toFixed(1)}% accuracy`} icon="chart" tone="blue" />
          <Kpi label="Hours saved" value={String(s.hours_saved_30d)} sub="vs. manual review" icon="history" />
          <Kpi label="Avg speed" value={`${s.avg_processing_seconds}s`} sub="per document" icon="sparkle" />
        </div>
      )}

      {data && (
        <div className="grid-2">
          <div className="panel">
            <div className="panel-head"><h3>Throughput</h3><span className="chip-label">total vs auto-approved</span></div>
            <div className="panel-body"><AreaChart data={data.timeseries} /></div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>Routing mix</h3></div>
            <div className="panel-body">
              <Donut segments={[
                { label: "Auto-approved", value: data.routing.auto_approved, color: TEAL },
                { label: "In review", value: data.routing.in_review, color: AMBER },
              ]} />
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>By document type</h3></div>
            <div className="panel-body">
              <BarChart data={data.by_type.slice(0, 6).map((d) => ({ label: pretty(d.type), value: d.count }))} />
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>By workflow</h3></div>
            <div className="panel-body">
              <BarChart color="#0b64d1" data={data.by_workflow.map((d) => ({ label: pretty(d.workflow), value: d.count }))} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, trend, icon, tone }: { label: string; value: string; sub?: string; trend?: string; icon: string; tone?: string }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <div className="kpi-ic"><Icon name={icon} size={18} /></div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {trend && <div className="kpi-trend">▲ {trend}</div>}
    </div>
  );
}
