import { useEffect, useState } from "react";
import { Icon } from "./Icons";

const STAGES = [
  { key: "detect", label: "Detecting document type…", done: "Document classified" },
  { key: "ocr", label: "Reading the page (OCR)…", done: "Text & layout extracted" },
  { key: "kv", label: "Making key–value pairs…", done: "Fields structured" },
  { key: "validate", label: "Validating business rules…", done: "Rules checked" },
  { key: "route", label: "Routing decision…", done: "Routed" },
];

/**
 * Full-bleed processing experience: a scan line sweeps the document top→bottom
 * while staged cues advance. Purely visual; the parent hides it once the real
 * result is ready (and a minimum display time has elapsed).
 */
export function Processing({ imageUrl, fileName }: { imageUrl: string | null; fileName: string }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setStage((s) => (s < STAGES.length - 1 ? s + 1 : s)), 780);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="proc">
      <div className="proc-doc">
        <div className={`proc-frame ${imageUrl ? "" : "noimg"}`}>
          {imageUrl ? <img src={imageUrl} alt={fileName} /> : <div className="proc-placeholder"><Icon name="file" size={54} /></div>}
          <div className="scanline" />
          <div className="scan-grid" />
          <div className="proc-badge">Analyzing</div>
        </div>
        <div className="proc-filename">{fileName}</div>
      </div>

      <div className="proc-side">
        <div className="proc-title">
          <span className="proc-spin"><Icon name="sparkle" size={18} /></span>
          Understanding your document
        </div>
        <div className="proc-stages">
          {STAGES.map((s, i) => (
            <div key={s.key} className={`proc-stage ${i < stage ? "done" : i === stage ? "active" : ""}`}>
              <span className="ps-dot">{i < stage ? <Icon name="check" size={14} /> : i + 1}</span>
              <span className="ps-label">{i < stage ? s.done : s.label}</span>
              {i === stage && <span className="ps-loader" />}
            </div>
          ))}
        </div>
        <div className="proc-hint">Six checks, one document — before it reaches you.</div>
      </div>
    </div>
  );
}
