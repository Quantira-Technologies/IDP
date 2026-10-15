import { useEffect, useState } from "react";
import { getDashboard, runAnalyze, type DashboardData, type Insight } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { AreaChart, BarChart, ChartEmpty, Donut, TEAL, AMBER } from "../components/Charts";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function Dashboard() {
  const { can, user } = useAuth();
  const { t, num, lang } = useI18n();
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

  const goDocs = () => window.dispatchEvent(new CustomEvent("intel2doc:nav", { detail: "documents" }));

  const s = data?.summary;
  return (
    <div className="page">
      <PageHead
        title={`${t("Welcome")}${lang === "ar" ? "، " : ", "}${user?.name.split(" ")[0] ?? ""}`}
        subtitle="Operational overview — last 30 days"
        actions={
          can("dashboard.analyze") && (
            <button className="btn btn-analyze" data-tour="analyze-btn" onClick={analyze} disabled={analyzing}>
              {analyzing ? <span className="spinner" /> : <><Icon name="sparkle" size={17} /> {t("Analyze")}</>}
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
          <Kpi label={t("Documents (30d)")} value={num(s.documents_30d.toLocaleString())} trend={`+${num(s.trend_pct)}%`} icon="file" onClick={goDocs} />
          <Kpi label={t("Straight-through")} value={`${num(Math.round(s.straight_through_rate * 100))}%`} sub={`${num(s.auto_approved.toLocaleString())} ${t("auto-approved")}`} icon="check" tone="teal" onClick={goDocs} />
          <Kpi label={t("In review")} value={num(s.in_review.toLocaleString())} sub={t("awaiting a human")} icon="bell" tone="amber" onClick={goDocs} />
          <Kpi label={t("Avg confidence")} value={`${num(Math.round(s.avg_confidence * 100))}%`} sub={`${num((s.accuracy * 100).toFixed(1))}% ${t("accuracy")}`} icon="chart" tone="blue" onClick={goDocs} />
          <Kpi label={t("Hours saved")} value={num(String(s.hours_saved_30d))} sub={t("vs. manual review")} icon="history" onClick={goDocs} />
          <Kpi label={t("Avg speed")} value={`${num(s.avg_processing_seconds)}${lang === "ar" ? " ث" : "s"}`} sub={t("per document")} icon="sparkle" onClick={goDocs} />
        </div>
      )}

      {data && (
        <div className="grid-2">
          <div className="panel">
            <div className="panel-head"><h3>{t("Throughput")}</h3><span className="chip-label">{t("total vs auto-approved")}</span></div>
            <div className="panel-body">
              {data.timeseries.every((d) => d.total === 0) ? (
                <ChartEmpty text="No documents in the last 30 days — upload a document to start the timeline." />
              ) : (
                <AreaChart data={data.timeseries} />
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>{t("Routing mix")}</h3></div>
            <div className="panel-body">
              {data.routing.auto_approved + data.routing.in_review === 0 ? (
                <ChartEmpty text="No documents scanned yet." />
              ) : (
              <Donut segments={[
                { label: t("Auto-approved"), value: data.routing.auto_approved, color: TEAL },
                { label: t("In review"), value: data.routing.in_review, color: AMBER },
              ]} />
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>{t("By document type")}</h3></div>
            <div className="panel-body">
              {data.by_type.length === 0 ? (
                <ChartEmpty text="No documents scanned yet." />
              ) : (
              <BarChart data={data.by_type.slice(0, 6).map((d) => ({ label: t(pretty(d.type)), value: d.count }))} />
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>{t("By workflow")}</h3></div>
            <div className="panel-body">
              {data.by_workflow.length === 0 ? (
                <ChartEmpty text="No documents scanned yet." />
              ) : (
              <BarChart color="#0b64d1" data={data.by_workflow.map((d) => ({ label: t(pretty(d.workflow)), value: d.count }))} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, trend, icon, tone, onClick }: { label: string; value: string; sub?: string; trend?: string; icon: string; tone?: string; onClick?: () => void }) {
  return (
    <div
      className={`kpi ${tone ?? ""} ${onClick ? "kpi-click" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => (e.key === "Enter" || e.key === " ") && onClick() : undefined}
    >
      <div className="kpi-ic"><Icon name={icon} size={18} /></div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {trend && <div className="kpi-trend">▲ {trend}</div>}
    </div>
  );
}
