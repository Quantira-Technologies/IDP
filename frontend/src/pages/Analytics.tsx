import { useEffect, useState } from "react";
import { getDashboard, getGeo, runAnalyze, type DashboardData, type GeoData, type Insight } from "../api";
import { useAuth } from "../auth";
import { BarChart } from "../components/Charts";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
function flag(code: string): string {
  if (!code || code.length !== 2) return "🏳️";
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)));
}

export function Analytics() {
  const { can } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [geo, setGeoData] = useState<GeoData | null>(null);
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard().then(setData).catch((e) => setError(String(e.message || e)));
    getGeo().then(setGeoData).catch(() => setGeoData(null));
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

  return (
    <div className="page">
      <PageHead
        title="Analytics"
        subtitle="Trade insight — origins, lanes and extraction quality by country"
        actions={
          can("dashboard.analyze") && (
            <button className="btn btn-analyze" onClick={analyze} disabled={analyzing}>
              {analyzing ? <span className="spinner" /> : <><Icon name="sparkle" size={17} /> Generate insights</>}
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

      {geo && (
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="panel">
            <div className="panel-head"><h3>Consignments by origin country</h3></div>
            <div className="panel-body">
              <BarChart data={geo.by_origin.slice(0, 8).map((c) => ({ label: `${flag(c.code)} ${c.country}`, value: c.count }))} />
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>Busiest trade lanes</h3><span className="chip-label">origin → destination</span></div>
            <div className="panel-body">
              {geo.trade_lanes.map((l) => (
                <div className="geo-lane" key={l.origin}>
                  <div className="geo-route">
                    <span className="flag">{flag(l.origin_code)}</span> {l.origin}
                    <Icon name="chevron" size={14} /> <span className="flag">🇸🇦</span> {l.destination}
                  </div>
                  <span className="geo-count">{l.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="panel span-2">
            <div className="panel-head"><h3>Extraction confidence by origin country</h3><span className="chip-label">lowest needs the most review</span></div>
            <div className="panel-body">
              <table className="tbl">
                <thead><tr><th>Country</th><th>Documents</th><th>Avg confidence</th><th>Recommended</th></tr></thead>
                <tbody>
                  {geo.confidence_by_country.map((c) => (
                    <tr key={c.country}>
                      <td><b>{flag(c.code)} {c.country}</b></td>
                      <td>{c.docs.toLocaleString()}</td>
                      <td>
                        <span className="conf inline">
                          <span className={`bar`}><i style={{ width: `${c.avg_confidence * 100}%`, background: c.avg_confidence < 0.8 ? "var(--amber)" : "var(--teal)" }} /></span>
                          <span className="pct">{Math.round(c.avg_confidence * 100)}%</span>
                        </span>
                      </td>
                      <td>
                        <span className={`policy-chip ${c.avg_confidence < 0.8 ? "review" : "approve"}`}>
                          {c.avg_confidence < 0.8 ? "Route to review" : "Auto-clear eligible"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {data && (
        <div className="grid-2">
          <div className="panel">
            <div className="panel-head"><h3>Confidence distribution</h3></div>
            <div className="panel-body">
              <BarChart color="#0b64d1" data={data.confidence_buckets.map((b) => ({ label: b.bucket, value: b.count }))} />
            </div>
          </div>
          <div className="panel">
            <div className="panel-head"><h3>Top rule failures</h3></div>
            <div className="panel-body">
              <BarChart color="#d98324" data={data.top_failed_rules.map((r) => ({ label: pretty(r.rule), value: r.failures }))} />
            </div>
          </div>
          <div className="panel span-2">
            <div className="panel-head"><h3>Reviewer performance</h3><span className="chip-label">{data.by_officer.length} people</span></div>
            <div className="panel-body">
              <table className="tbl">
                <thead>
                  <tr><th>Name</th><th>Role</th><th>Processed</th><th>Corrections</th><th>Avg confidence</th></tr>
                </thead>
                <tbody>
                  {data.by_officer.map((o) => (
                    <tr key={o.name}>
                      <td><b>{o.name}</b></td>
                      <td><span className="pill-muted">{pretty(o.role)}</span></td>
                      <td>{o.processed.toLocaleString()}</td>
                      <td>{o.corrections}</td>
                      <td>
                        <span className="conf inline">
                          <span className="bar"><i style={{ width: `${o.avg_confidence * 100}%` }} /></span>
                          <span className="pct">{Math.round(o.avg_confidence * 100)}%</span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

