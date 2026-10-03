import { useEffect, useState } from "react";
import { getBusinessRules, updateBusinessRules, type BusinessRules as BR, type DocPolicy } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
function emoji(t: string) {
  if (t.includes("waybill")) return "✈️";
  if (t.includes("declaration")) return "🛃";
  if (t.includes("origin") || t.includes("certificate")) return "📜";
  if (t.includes("purchase")) return "📦";
  if (t.includes("receipt")) return "📥";
  if (t.includes("gst")) return "🪪";
  if (t.includes("bank")) return "🏦";
  return "🧾";
}
const ACTIONS: DocPolicy["action"][] = ["auto_approve", "review", "reject"];
const LABEL: Record<string, string> = { auto_approve: "Auto-approve", review: "Review", reject: "Reject" };

export function BusinessRules() {
  const { can } = useAuth();
  const canManage = can("business_rules.manage");
  const [cfg, setCfg] = useState<BR | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getBusinessRules().then(setCfg).catch((e) => setError(String(e.message || e))); }, []);

  function setAction(i: number, action: DocPolicy["action"]) {
    if (!canManage || !cfg) return;
    const policies = cfg.policies.map((p, j) => (j === i ? { ...p, action } : p));
    setCfg({ ...cfg, policies }); setDirty(true);
  }
  function setNote(i: number, note: string) {
    if (!canManage || !cfg) return;
    const policies = cfg.policies.map((p, j) => (j === i ? { ...p, note } : p));
    setCfg({ ...cfg, policies }); setDirty(true);
  }
  function setMinConf(v: number) { if (cfg) { setCfg({ ...cfg, min_confidence: v }); setDirty(true); } }

  async function save() {
    if (!cfg) return;
    setSaving(true); setError(null);
    try { setCfg(await updateBusinessRules(cfg)); setDirty(false); setToast("Rules saved"); setTimeout(() => setToast(null), 2500); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setSaving(false); }
  }

  if (!cfg) return <div className="page"><PageHead title="Business Rules" />{error && <div className="alert">⚠ {error}</div>}</div>;

  return (
    <div className="page">
      <PageHead
        title="Business Rules"
        subtitle="Decide what happens to each document type — auto-approve, review, or reject"
        actions={canManage && <button className="btn btn-primary" onClick={save} disabled={!dirty || saving}>{saving ? <span className="spinner" /> : dirty ? "Save changes" : "Saved"}</button>}
      />
      {!canManage && <div className="note-bar"><Icon name="shield" size={16} /> View-only. These rules decide how your scans are routed — a tenant admin configures them.</div>}
      {toast && <div className="toast-ok">✓ {toast}</div>}
      {error && <div className="alert">⚠ {error}</div>}

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-body" style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>Minimum confidence for auto-approve</div>
            <div className="muted" style={{ fontSize: 12.5 }}>Documents below this are sent to review even if their type is auto-approve.</div>
          </div>
          <div style={{ flex: 1 }} />
          <input type="range" min={0.5} max={0.99} step={0.01} value={cfg.min_confidence} disabled={!canManage} onChange={(e) => setMinConf(parseFloat(e.target.value))} style={{ width: 220 }} />
          <b style={{ width: 46, textAlign: "right" }}>{Math.round(cfg.min_confidence * 100)}%</b>
        </div>
      </div>

      <div className="rules-cfg">
        {cfg.policies.map((p, i) => (
          <div className="rule-row" key={p.doc_type}>
            <div className="rule-doc"><span style={{ fontSize: 18 }}>{emoji(p.doc_type)}</span> {pretty(p.doc_type)}</div>
            <div className="seg">
              {ACTIONS.map((a) => (
                <button key={a} className={`${a === "auto_approve" ? "approve" : a} ${p.action === a ? "on" : ""}`} onClick={() => setAction(i, a)} disabled={!canManage}>
                  {LABEL[a]}
                </button>
              ))}
            </div>
            <input className="rule-note" value={p.note} placeholder="Guidance shown to officers…" disabled={!canManage} onChange={(e) => setNote(i, e.target.value)} />
          </div>
        ))}
      </div>
    </div>
  );
}
