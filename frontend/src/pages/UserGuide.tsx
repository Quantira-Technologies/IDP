import { useEffect, useState } from "react";
import { getGuide, updateGuideSection, type GuideSection } from "../api";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

export function UserGuide() {
  const [sections, setSections] = useState<GuideSection[]>([]);
  const [canEdit, setCanEdit] = useState(false);
  const [active, setActive] = useState(0);
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getGuide().then((g) => { setSections(g.sections); setCanEdit(g.can_edit); }).catch((e) => setError(String(e.message || e)));
  }, []);

  const current = sections[active];

  function startEdit() {
    if (!current) return;
    setDraftTitle(current.title); setDraftBody(current.body); setEditing(true);
  }
  async function save() {
    if (!current) return;
    try {
      const updated = await updateGuideSection(current.id, draftTitle, draftBody);
      setSections((s) => s.map((x) => (x.id === current.id ? { ...x, ...updated } : x)));
      setEditing(false);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  return (
    <div className="page">
      <PageHead
        title="User Guide"
        subtitle="How to work in intel2doc — tailored to what you can access"
        actions={canEdit && current && !editing && <button className="btn" onClick={startEdit}><Icon name="book" size={16} /> Edit section</button>}
      />
      {error && <div className="alert">⚠ {error}</div>}

      <div className="guide">
        <div className="guide-toc">
          {sections.map((s, i) => (
            <button key={s.id} className={i === active ? "active" : ""} onClick={() => { setActive(i); setEditing(false); }}>{s.title}</button>
          ))}
        </div>
        <div className="guide-body">
          {current && !editing && (
            <>
              <h3>{current.title}</h3>
              <p style={{ whiteSpace: "pre-wrap" }} dangerouslySetInnerHTML={{ __html: bold(current.body) }} />
            </>
          )}
          {current && editing && (
            <div className="guide-edit">
              <input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} style={{ width: "100%", padding: "10px 12px", border: "1px solid var(--line)", borderRadius: 10, marginBottom: 10, background: "var(--panel-2)", color: "var(--ink)", fontWeight: 700 }} />
              <textarea value={draftBody} onChange={(e) => setDraftBody(e.target.value)} />
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button className="btn btn-primary" onClick={save}>Save</button>
                <button className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Minimal **bold** rendering; content is authored by admins only.
function bold(s: string): string {
  return s
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
}
