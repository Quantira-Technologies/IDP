import { useEffect, useState } from "react";
import {
  createApiKey, getSubscription, revokeApiKey, updateConnector, updateWebhook,
  type ApiKey, type Subscription as Sub,
} from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

export function Subscription() {
  const { can } = useAuth();
  const canManage = can("subscription.manage");
  const [sub, setSub] = useState<Sub | null>(null);
  const [newKey, setNewKey] = useState<ApiKey | null>(null);
  const [label, setLabel] = useState("");
  const [webhook, setWebhook] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getSubscription().then((s) => { setSub(s); setWebhook(s.webhook_url); }).catch((e) => setError(String(e.message || e))); }, []);

  async function genKey() {
    try { const k = await createApiKey(label || "New key"); setNewKey(k); setLabel(""); setSub(await getSubscription()); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }
  async function revoke(id: string) { try { setSub(await revokeApiKey(id)); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } }
  async function toggle(id: string, status: string) { try { setSub(await updateConnector(id, status === "connected" ? "disconnected" : "connected")); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } }
  async function saveWebhook() { try { setSub(await updateWebhook(webhook)); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } }

  if (!sub) return <div className="page"><PageHead title="API & Subscription" />{error && <div className="alert">⚠ {error}</div>}</div>;
  const used = sub.plan.docs_used, cap = sub.plan.docs_per_month;

  return (
    <div className="page">
      <PageHead title="API & Subscription" subtitle="API keys, plan usage and ECM/ERP connectors" />
      {!canManage && <div className="note-bar"><Icon name="shield" size={16} /> View-only. A tenant admin manages keys and connectors.</div>}
      {error && <div className="alert">⚠ {error}</div>}

      <div className="sub-grid">
        <div className="plan-card">
          <div className="plan-name">{sub.plan.name}</div>
          <div style={{ opacity: .9, fontSize: 13, marginTop: 4 }}>{sub.plan.seats} seats · renews {sub.plan.renews}</div>
          <div className="plan-meter"><i style={{ width: `${Math.min(100, (used / cap) * 100)}%` }} /></div>
          <div style={{ fontSize: 12.5, opacity: .9 }}>{used.toLocaleString()} / {cap.toLocaleString()} documents this month</div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Webhook</h3></div>
          <div className="panel-body">
            <div className="muted" style={{ fontSize: 12.5, marginBottom: 8 }}>Approved documents are POSTed here as JSON.</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://your-system/webhooks/intel2doc" disabled={!canManage} style={{ flex: 1, padding: "9px 11px", border: "1px solid var(--line)", borderRadius: 10, background: "var(--panel-2)", color: "var(--ink)" }} />
              {canManage && <button className="btn" onClick={saveWebhook}>Save</button>}
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <h3>API keys</h3>
          {canManage && (
            <div style={{ display: "flex", gap: 8 }}>
              <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Key label" style={{ padding: "7px 10px", border: "1px solid var(--line)", borderRadius: 9, background: "var(--panel-2)", color: "var(--ink)", fontSize: 12.5 }} />
              <button className="btn btn-primary" onClick={genKey}><Icon name="plug" size={15} /> Generate key</button>
            </div>
          )}
        </div>
        <div className="panel-body">
          {newKey?.secret && (
            <div className="secret-box">
              <div style={{ marginBottom: 6, color: "#bfeede" }}>Copy this key now — it won't be shown again:</div>
              {newKey.secret}
              <div style={{ marginTop: 8 }}><button className="mini-btn" onClick={() => navigator.clipboard?.writeText(newKey.secret!)}>Copy</button></div>
            </div>
          )}
          {sub.api_keys.map((k) => (
            <div className="keyrow" key={k.id}>
              <Icon name="plug" size={16} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 650, fontSize: 13.5 }}>{k.label}</div>
                <div className="key-mono muted">{k.prefix}••••{k.last4}</div>
              </div>
              <span className={`scan-badge ${k.active ? "auto_approved" : "rejected"}`}>{k.active ? "active" : "revoked"}</span>
              {canManage && k.active && <button className="mini-btn" onClick={() => revoke(k.id)}>Revoke</button>}
            </div>
          ))}
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head"><h3>ECM / ERP connectors</h3></div>
        <div className="panel-body">
          {sub.connectors.map((c) => (
            <div className="connrow" key={c.id}>
              <span className={`status-dot ${c.status}`} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 650, fontSize: 13.5 }}>{c.name}</div>
                <div className="muted" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: .4 }}>{c.type}</div>
              </div>
              <span className="muted" style={{ fontSize: 12.5 }}>{c.status}</span>
              {canManage && <button className="mini-btn" onClick={() => toggle(c.id, c.status)}>{c.status === "connected" ? "Disconnect" : "Connect"}</button>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
