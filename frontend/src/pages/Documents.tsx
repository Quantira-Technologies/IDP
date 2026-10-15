import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  absoluteImageUrl, correctField, createFolder, deleteFolder, deleteScan,
  getScan, listFolders, listScans, moveScan, previewUpload, processUpload,
  type Folder, type ScanMeta,
} from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { DetectedTable, FullText, QRCodes, ApprovedScreen } from "../components/Extraction";
import { EngineBadge } from "../components/AiStatus";
import { FieldList } from "../components/FieldList";
import { Icon } from "../components/Icons";
import { PagePreview } from "../components/PagePreview";
import { Processing } from "../components/Processing";
import type { DocumentResult, SubDocumentResult } from "../types";

const MIN_ANIM_MS = 2600;

function docEmoji(name: string): string {
  const s = name.toLowerCase();
  if (s.includes("waybill") || s.includes("air")) return "✈️";
  if (s.includes("customs") || s.includes("declaration")) return "🛃";
  if (s.includes("origin") || s.includes("certificate")) return "📜";
  if (s.includes("purchase") || s.startsWith("po")) return "📦";
  if (s.includes("receipt") || s.includes("grn")) return "📥";
  if (s.includes("vendor") || s.includes("supplier")) return "🧾";
  if (s.includes("gst")) return "🪪";
  if (s.includes("bank") || s.includes("statement")) return "🏦";
  if (s.includes("invoice") || s.includes("bill") || /^\d/.test(s)) return "🧾";
  return "📄";
}
const pretty = (f: string) => f.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const when = (iso?: string) => (iso ? new Date(iso).toLocaleString() : "");

export function Documents() {
  const { can, user } = useAuth();
  const { t, num } = useI18n();
  const [result, setResult] = useState<DocumentResult | null>(null);
  const [approved, setApproved] = useState(false);
  const [activeSub, setActiveSub] = useState(0);
  const [activeField, setActiveField] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [procName, setProcName] = useState<string | null>(null);
  const [procImg, setProcImg] = useState<string | null>(null);
  const [localImg, setLocalImg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const viewRun = useRef(0);

  const [folders, setFolders] = useState<Folder[]>([]);
  const [scans, setScans] = useState<ScanMeta[]>([]);
  const [activeFolder, setActiveFolder] = useState<string>("__all__"); // __all__ | __root__ | folderId
  const [newFolder, setNewFolder] = useState("");

  const refreshFolders = useCallback(() => { listFolders().then(setFolders).catch(() => setFolders([])); }, []);
  const refreshScans = useCallback(() => {
    const fid = activeFolder === "__all__" ? undefined : activeFolder === "__root__" ? null : activeFolder;
    listScans(fid, activeFolder === "__all__").then(setScans).catch(() => setScans([]));
  }, [activeFolder]);

  useEffect(() => { if (can("documents.view")) { refreshFolders(); } }, [can, refreshFolders]);
  useEffect(() => { if (can("documents.view")) { refreshScans(); } }, [can, refreshScans]);

  async function runProcessing(name: string, image: string | null, fn: () => Promise<DocumentResult>) {
    viewRun.current += 1;
    setError(null); setResult(null); setApproved(false); setProcName(name); setProcImg(image); setLocalImg(image);
    const started = Date.now();
    try {
      const r = await fn();
      await new Promise((res) => setTimeout(res, Math.max(0, MIN_ANIM_MS - (Date.now() - started))));
      setResult(r); setActiveSub(0); setActiveField(null);
      refreshScans(); refreshFolders();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setProcName(null);
    }
  }

  function startUpload(file: File) {
    const url = file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
    runProcessing(file.name, url, () => processUpload(file));
    if (url) return;
    // PDF / Word: show the page while it is being analysed.
    const run = viewRun.current;
    previewUpload(file)
      .then((u) => { if (u && viewRun.current === run) { setProcImg(u); setLocalImg(u); } })
      .catch(() => {});
  }
  function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    startUpload(file);
    e.target.value = "";
  }
  function onDropFile(file: File) {
    startUpload(file);
  }

  async function openScan(id: string) {
    viewRun.current += 1;
    setError(null); setApproved(false);
    try {
      const r = await getScan(id);
      setResult(r); setActiveSub(0); setActiveField(null);
      setLocalImg(absoluteImageUrl(r.image_url));
      if (r.approved) setApproved(true);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  async function removeScan(id: string) {
    try { await deleteScan(id); refreshScans(); refreshFolders(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }
  async function onMove(id: string, folderId: string) {
    try { await moveScan(id, folderId || null); refreshScans(); refreshFolders(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }
  async function addFolder() {
    const name = newFolder.trim();
    if (!name) return;
    try { await createFolder(name, null); setNewFolder(""); refreshFolders(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }
  async function removeFolder(id: string) {
    try { await deleteFolder(id); if (activeFolder === id) setActiveFolder("__all__"); refreshFolders(); refreshScans(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  async function onCorrect(fieldName: string, newValue: string, approve: boolean) {
    if (!result) return;
    try {
      const r = await correctField(result.id, activeSub, fieldName, newValue, approve);
      setResult(r);
      if (approve) { setApproved(true); refreshScans(); }
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  function reset() { setResult(null); setApproved(false); setActiveField(null); refreshScans(); }

  const sub: SubDocumentResult | undefined = result?.sub_documents[activeSub];
  const previewImage = result && result.sub_documents.length === 1 ? localImg || absoluteImageUrl(result.image_url) : null;
  const canUpload = can("documents.upload");
  const canCorrect = can("review.correct") || can("documents.edit");
  const canApprove = can("review.approve") || can("documents.approve");

  if (procName) {
    return (
      <div className="page">
        <PageHead title="Processing document" subtitle="Cleaning image → OCR → key–value → validate → route" />
        <div className="panel"><div className="panel-body"><Processing imageUrl={procImg} fileName={procName} /></div></div>
      </div>
    );
  }

  if (result && sub && approved) {
    return (
      <div className="page">
        <ApprovedScreen result={result} sub={sub} imageUrl={previewImage} approver={user?.name ?? "Reviewer"} onAnother={reset} onBack={() => setApproved(false)} />
      </div>
    );
  }

  if (result && sub) {
    return (
      <div className="page">
        <div className="page-head">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button className="icon-btn" onClick={reset} title={t("Back")}><Icon name="back" size={18} /></button>
            <div><h2>{t("Review & validate")}</h2><p>{t("Every field is traced to the page — correct anything, then approve.")}</p></div>
          </div>
          <div className="page-actions"><button className="btn btn-ghost" onClick={reset}>{t("← Back to documents")}</button></div>
        </div>
        {error && <div className="alert">⚠ {error}</div>}
        <div className="review">
          <div className="left-col">
            <div className="subtabs">
              {result.sub_documents.map((s, i) => (
                <button key={i} className={`tab ${i === activeSub ? "active" : ""}`} onClick={() => { setActiveSub(i); setActiveField(null); }}>
                  <span>{docEmoji(s.doc_type)}</span>{t(pretty(s.doc_type))}
                  <span className={`mark ${s.route === "auto_approved" ? "ok" : s.route === "rejected" ? "rej" : "warn"}`}>{s.route === "auto_approved" ? "✓" : s.route === "rejected" ? "✕" : "⚠"}</span>
                </button>
              ))}
            </div>
            <div className="panel">
              <div className="panel-head"><h3>{t("Source")} — {t(pretty(sub.doc_type))}</h3><EngineBadge engine={sub.extraction.engine} /></div>
              <div className="panel-body"><PagePreview sub={sub} activeField={activeField} onPick={setActiveField} imageUrl={previewImage} realFile={sub.engine !== "mock"} /></div>
            </div>
          </div>
          <div className="review-right">
            <div className="panel">
              <div className="panel-head"><h3>{t("Extracted data & checks")}</h3><span className="chip-label">{Object.keys(sub.extraction.fields).length} {t("fields")}</span></div>
              <div className="panel-body">
                <RouteBanner sub={sub} />
                <RuleResults sub={sub} />
                <FieldList sub={sub} activeField={activeField} onPick={setActiveField} onCorrect={canCorrect ? onCorrect : undefined} />
                {canApprove && sub.route !== "rejected" && (
                  <div className="approve-bar">
                    <button className="btn btn-primary" onClick={() => onCorrect(Object.keys(sub.extraction.fields)[0], String(sub.extraction.fields[Object.keys(sub.extraction.fields)[0]]?.value ?? ""), true)}>
                      <Icon name="shield" size={16} /> {t("Approve & secure")}
                    </button>
                    <span className="approve-hint">{t("Validates and moves the document to Approved.")}</span>
                  </div>
                )}
              </div>
            </div>
            <DetectedTable ex={sub.extraction} />
            <QRCodes ex={sub.extraction} />
            <FullText ex={sub.extraction} />
          </div>
        </div>
      </div>
    );
  }

  // ---- List: upload + past scans + folders ----
  return (
    <div className="page">
      <PageHead
        title="Documents"
        subtitle="Upload any document — it's cleaned, fully OCR'd, and saved to your past scans"
        actions={canUpload && (
          <>
            <button className="btn btn-primary" onClick={() => fileRef.current?.click()}><Icon name="upload" size={17} /> {t("Upload document")}</button>
            <input ref={fileRef} type="file" accept="image/*,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onUpload} hidden />
          </>
        )}
      />
      {error && <div className="alert">⚠ {error}</div>}
      {canUpload && (
        <div className="dropzone" data-tour="dropzone" onClick={() => fileRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onDropFile(f); }}>
          <div className="dz-icon"><Icon name="upload" size={30} /></div>
          <div className="dz-title">{t("Drop a document here or click to upload")}</div>
          <div className="dz-sub">{t("JPG, PNG, PDF or Word (DOCX) · auto-cleaned & fully OCR'd · QR codes captured separately")}</div>
        </div>
      )}

      <div className="section-title">{t("Past scans")}</div>
      <div className="docs-layout">
        <div className="folders" data-tour="folders">
          <div className="folders-head">
            <span className="folders-title">{t("Folders")}</span>
          </div>
          <button className={`folder ${activeFolder === "__all__" ? "active" : ""}`} onClick={() => setActiveFolder("__all__")}>
            <Icon name="grid" size={16} /> {t("All scans")} <span className="fcount">{num(scans.length)}</span>
          </button>
          <button className={`folder ${activeFolder === "__root__" ? "active" : ""}`} onClick={() => setActiveFolder("__root__")}>
            <Icon name="file" size={16} /> {t("Unfiled")}
          </button>
          {folders.map((f) => (
            <button key={f.id} className={`folder ${activeFolder === f.id ? "active" : ""}`} onClick={() => setActiveFolder(f.id)}>
              <Icon name="folder" size={16} /> {f.name} <span className="fcount">{num(f.count)}</span>
              <span className="fdel" onClick={(e) => { e.stopPropagation(); removeFolder(f.id); }} title={t("Delete folder")}><Icon name="trash" size={14} /></span>
            </button>
          ))}
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <input value={newFolder} onChange={(e) => setNewFolder(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addFolder()} placeholder={t("New folder")} style={{ flex: 1, padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 9, background: "var(--panel-2)", color: "var(--ink)", fontSize: 12.5 }} />
            <button className="icon-btn" onClick={addFolder} title={t("Create folder")}><Icon name="folderPlus" size={16} /></button>
          </div>
        </div>

        <div className="scan-list">
          {scans.length === 0 ? (
            <div className="empty"><Icon name="file" size={40} /><div style={{ marginTop: 10 }}>{t("No scans yet. Upload a document to get started.")}</div></div>
          ) : (
            scans.map((s) => (
              <div className="scan-row" key={s.id}>
                <span className="scan-emoji">{docEmoji(s.source_name || s.doc_type)}</span>
                <div className="scan-main" onClick={() => openScan(s.id)} style={{ cursor: "pointer" }}>
                  <div className="scan-name">{pretty(s.source_name || s.doc_type)}</div>
                  <div className="scan-meta">{t(pretty(s.doc_type))} · {when(s.created_at)}</div>
                </div>
                <span className={`scan-badge ${s.route}`}>{s.route === "auto_approved" ? (s.approved ? t("approved") : t("auto")) : s.route === "rejected" ? t("rejected") : t("review")}</span>
                <select value={s.folder_id ?? ""} onChange={(e) => onMove(s.id, e.target.value)} title="Move to folder"
                  style={{ padding: "6px 8px", border: "1px solid var(--line)", borderRadius: 8, background: "var(--panel-2)", color: "var(--ink)", fontSize: 12 }}>
                  <option value="">Unfiled</option>
                  {folders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
                <div className="scan-actions">
                  <button className="mini-btn" onClick={() => openScan(s.id)}>{t("Open")}</button>
                  <button className="icon-btn" onClick={() => removeScan(s.id)} title={t("Delete")} style={{ width: 32, height: 32 }}><Icon name="trash" size={15} /></button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export function PageHead({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <div className="page-head">
      <div><h2>{t(title)}</h2>{subtitle && <p>{t(subtitle)}</p>}</div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

function RouteBanner({ sub }: { sub: SubDocumentResult }) {
  const { t, num } = useI18n();
  const rejected = sub.route === "rejected";
  const ok = sub.route === "auto_approved";
  const cls = rejected ? "reject" : ok ? "ok" : "warn";
  return (
    <div className={`route ${cls}`}>
      <div className="r-top">
        <span className="r-badge">{ok ? `✓ ${t("Auto-approved")}` : rejected ? `✕ ${t("Rejected by policy")}` : `⚠ ${t("Needs review")}`}</span>
        <span className="r-meta">{t("min confidence")} {num((sub.min_confidence * 100).toFixed(0))}% · {t("engine")} {sub.engine}</span>
      </div>
      {sub.route_reasons.length > 0 && <ul>{sub.route_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
    </div>
  );
}

function RuleResults({ sub }: { sub: SubDocumentResult }) {
  const { t } = useI18n();
  if (sub.rule_results.length === 0) return null;
  return (
    <div className="rules">
      {sub.rule_results.map((r) => (
        <div className={`rule ${r.passed ? "pass" : "fail"}`} key={r.rule_id}>
          <span className="status">{r.passed ? "✓" : "✕"}</span>
          <span className="desc">{t(r.description)}<span className="detail">{r.detail}</span></span>
          <span className="sev">{t(r.severity)}</span>
        </div>
      ))}
    </div>
  );
}
