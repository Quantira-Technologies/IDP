import { useEffect, useState } from "react";
import { exportScan, getExportTargets, type ExportTarget } from "../api";
import type { DocumentResult, Extraction, SubDocumentResult } from "../types";
import { Icon } from "./Icons";
import { EngineBadge } from "./AiStatus";
import { useI18n } from "../i18n";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

/** A detected bill-of-materials / line-item grid rendered as a real table. */
export function DetectedTable({ ex }: { ex: Extraction }) {
  const { t, num } = useI18n();
  if (!ex.line_items || ex.line_items.length === 0) return null;
  const cols = Array.from(
    ex.line_items.reduce((set, li) => {
      Object.keys(li.fields).forEach((k) => set.add(k));
      return set;
    }, new Set<string>())
  );
  return (
    <div className="ex-block">
      <div className="ex-head">
        <span className="ex-title"><Icon name="grid" size={15} /> {t("Detected table")} · {num(ex.line_items.length)} {t("rows")}</span>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>{cols.map((c) => <th key={c}>{pretty(c)}</th>)}</tr>
          </thead>
          <tbody>
            {ex.line_items.map((li, i) => (
              <tr key={i}>
                {cols.map((c) => <td key={c}>{String(li.fields[c]?.value ?? "")}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Every line captured from the page — the full, verbatim transcript. */
export function FullText({ ex }: { ex: Extraction }) {
  const { t, num } = useI18n();
  const [open, setOpen] = useState(true);
  if (!ex.full_text || ex.full_text.length === 0) return null;
  const copy = () => navigator.clipboard?.writeText(ex.full_text.map((t) => t.text).join("\n"));
  return (
    <div className="ex-block">
      <div className="ex-head">
        <button className="ex-title as-btn" onClick={() => setOpen((o) => !o)}>
          <Icon name={open ? "x" : "file"} size={15} /> {t("Full document text")} · {num(ex.full_text.length)} {t("lines")}
        </button>
        <button className="mini-btn" onClick={copy}>{t("Copy all")}</button>
      </div>
      {open && (
        <div className="fulltext">
          {ex.full_text.map((t2, i) => (
            <div className="ft-line" key={i}>
              <span className="ft-text">{t2.text}</span>
              <span className={`ft-conf ${t2.confidence < 0.8 ? "low" : ""}`}>{num(Math.round(t2.confidence * 100))}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** QR / barcodes found on the page — snapshot + decoded value, shown separately. */
export function QRCodes({ ex }: { ex: Extraction }) {
  const { t, num } = useI18n();
  if (!ex.qr_codes || ex.qr_codes.length === 0) return null;
  const isUrl = (s: string) => /^https?:\/\//i.test(s);
  return (
    <div className="ex-block">
      <div className="ex-head">
        <span className="ex-title"><Icon name="grid" size={15} /> {t("QR / barcodes")} · {num(ex.qr_codes.length)}</span>
      </div>
      <div className="qr-grid">
        {ex.qr_codes.map((q, i) => (
          <div className="qr-card" key={i}>
            {q.image && <img src={q.image} alt="QR code" className="qr-img" />}
            <div className="qr-body">
              <div className="qr-label">{t("Decoded value")}</div>
              <div className="qr-data">{q.data}</div>
              <div className="qr-actions">
                <button className="mini-btn" onClick={() => navigator.clipboard?.writeText(q.data)}>{t("Copy")}</button>
                {isUrl(q.data) && <a className="mini-btn" href={q.data} target="_blank" rel="noreferrer">{t("Open")}</a>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Business-logic closure: a document is approved & secured. */
export function ApprovedScreen({
  result,
  sub,
  imageUrl,
  approver,
  onAnother,
  onBack,
}: {
  result: DocumentResult;
  sub: SubDocumentResult;
  imageUrl: string | null;
  approver: string;
  onAnother: () => void;
  onBack: () => void;
}) {
  const rulesPassed = sub.rule_results.filter((r) => r.passed).length;
  const ref = `I2D-${result.id.slice(0, 8).toUpperCase()}`;
  const when = new Date().toLocaleString();
  const fieldCount = Object.keys(sub.extraction.fields).length;

  function download() {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${ref}.json`;
    a.click();
  }

  return (
    <div className="approved">
      <div className="approved-hero">
        <div className="approved-check"><Icon name="check" size={44} /></div>
        <h2>Document approved &amp; secured</h2>
        <p>Validated against all business rules and cleared for downstream processing.</p>
        <div className="approved-ref">Reference <b>{ref}</b></div>
        <div className="approved-engine"><EngineBadge engine={sub.extraction.engine} /></div>
      </div>

      <div className="approved-body">
        <div className="approved-doc">
          {imageUrl ? <img src={imageUrl} alt="approved document" /> : <div className="ad-placeholder"><Icon name="file" size={54} /></div>}
          <div className="approved-stamp">
            <Icon name="shield" size={16} /> SECURED
          </div>
        </div>

        <div className="approved-side">
          <div className="approved-summary">
            <Row k="Document type" v={pretty(sub.extraction.doc_type)} />
            <Row k="Fields extracted" v={String(fieldCount)} />
            <Row k="Table rows" v={String(sub.extraction.line_items.length)} />
            <Row k="Rules passed" v={`${rulesPassed} / ${sub.rule_results.length}`} good />
            <Row k="Approved by" v={approver} />
            <Row k="Approved at" v={when} />
            <div className="ar-row"><span className="ar-k">Engine</span><span className="ar-v"><EngineBadge engine={sub.extraction.engine} /></span></div>
          </div>
          <div className="approved-actions">
            <button className="btn btn-primary" onClick={download}><Icon name="download" size={16} /> Download data (JSON)</button>
            <button className="btn" onClick={onAnother}>Process another document</button>
            <button className="btn btn-ghost" onClick={onBack}>← Back to document</button>
          </div>
          <ExportActions docId={result.id} />
        </div>
      </div>
    </div>
  );
}

function ExportActions({ docId }: { docId: string }) {
  const [targets, setTargets] = useState<ExportTarget[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { getExportTargets().then((t) => setTargets(t.targets)).catch(() => setTargets([])); }, []);

  async function push(target: ExportTarget) {
    setBusy(target.id); setErr(null); setMsg(null);
    try {
      const r = await exportScan(docId, target.id);
      setMsg(`${r.message}${r.reference ? ` (ref ${r.reference})` : ""}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="panel" style={{ marginTop: 4 }}>
      <div className="panel-head"><h3>Send to a connected system</h3></div>
      <div className="panel-body">
        {targets.length === 0 ? (
          <div className="muted" style={{ fontSize: 12.5 }}>
            No connected targets. Connect an ECM/ERP or set a webhook under <b>API &amp; Subscription</b>.
          </div>
        ) : (
          <div className="export-row">
            {targets.map((t) => (
              <button key={t.id} className="btn" onClick={() => push(t)} disabled={busy !== null}>
                {busy === t.id ? <span className="spinner" style={{ borderTopColor: "var(--teal)", borderColor: "rgba(16,163,127,.3)" }} /> : <Icon name="external" size={15} />} {t.name}
              </button>
            ))}
          </div>
        )}
        {msg && <div className="export-ok">✓ {msg}</div>}
        {err && <div className="alert" style={{ marginTop: 10 }}>⚠ {err}</div>}
      </div>
    </div>
  );
}

function Row({ k, v, good }: { k: string; v: string; good?: boolean }) {
  return (
    <div className="ar-row">
      <span className="ar-k">{k}</span>
      <span className={`ar-v ${good ? "good" : ""}`}>{v}</span>
    </div>
  );
}
