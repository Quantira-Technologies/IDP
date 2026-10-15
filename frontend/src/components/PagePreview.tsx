import { useState } from "react";
import { useI18n } from "../i18n";
import type { BoundingBox, Field, SubDocumentResult } from "../types";

type Area = { url: string; left: number; top: number; width: number; height: number };

/** Where an object-fit:contain picture actually sits inside its frame (in %). */
function pictureArea(img: HTMLImageElement): Area | null {
  const frame = img.parentElement;
  if (!frame || !img.naturalWidth || !img.naturalHeight || !frame.clientWidth || !frame.clientHeight) return null;
  const pic = img.naturalWidth / img.naturalHeight;
  const box = frame.clientWidth / frame.clientHeight;
  if (pic < box) {
    const width = (pic / box) * 100;
    return { url: img.src, left: (100 - width) / 2, top: 0, width, height: 100 };
  }
  const height = (box / pic) * 100;
  return { url: img.src, left: 0, top: (100 - height) / 2, width: 100, height };
}

/**
 * Renders a stand-in "page" and overlays each field's bounding box. Clicking a
 * box (or a field row) highlights the source location — the visual proof of the
 * "100% of fields traced to source" claim. In production this canvas is the real
 * rendered PDF page from PDF.js with the same normalized-coordinate overlay.
 */
export function PagePreview({
  sub,
  activeField,
  onPick,
  imageUrl,
  realFile,
}: {
  sub: SubDocumentResult;
  activeField: string | null;
  onPick: (name: string) => void;
  imageUrl?: string | null;
  /** An uploaded file (not a built-in demo), so never call its page "simulated". */
  realFile?: boolean;
}) {
  const { t } = useI18n();
  const [area, setArea] = useState<Area | null>(null);
  const measure = (img: HTMLImageElement | null) => {
    if (!img || !img.complete) return;
    const a = pictureArea(img);
    if (a && (!area || a.url !== area.url || Math.abs(a.left - area.left) > 0.01 || Math.abs(a.top - area.top) > 0.01)) setArea(a);
  };
  // Boxes are drawn over the picture itself, not the whole frame.
  const fitted = imageUrl ? (area && area.url === new URL(imageUrl, window.location.href).href ? area : null) : null;
  const layer = fitted
    ? { left: `${fitted.left}%`, top: `${fitted.top}%`, width: `${fitted.width}%`, height: `${fitted.height}%` }
    : { left: 0, top: 0, width: "100%", height: "100%" };
  const boxes: { name: string; bbox: BoundingBox; conf: number }[] = [];
  Object.values(sub.extraction.fields).forEach((f: Field) => {
    if (f.bbox) boxes.push({ name: f.name, bbox: f.bbox, conf: f.confidence });
  });
  sub.extraction.line_items.forEach((li, i) => {
    Object.values(li.fields).forEach((f) => {
      if (f.bbox) boxes.push({ name: `line${i + 1}.${f.name}`, bbox: f.bbox, conf: f.confidence });
    });
  });

  return (
    <div className={`preview ${imageUrl ? "has-img" : ""}`}>
      {imageUrl ? (
        <img src={imageUrl} alt={sub.doc_type} ref={measure} onLoad={(e) => measure(e.currentTarget)} />
      ) : realFile ? (
        <div className="sim-label">{t("Page preview not available for this file")}</div>
      ) : (
        <div className="sim-label">{t(sub.doc_type)} — {t("source page (simulated)")}</div>
      )}
      {boxes.length === 0 && (
        <div className="nobbox">{t("no bounding boxes returned for this document")}</div>
      )}
      {(!imageUrl || fitted) && (
      <div className="bbox-layer" style={layer}>
      {boxes.map((b) => {
        const active = activeField === b.name;
        const low = b.conf < 0.8;
        return (
          <div
            key={b.name}
            onClick={() => onPick(b.name)}
            title={`${b.name} (conf ${b.conf.toFixed(2)})`}
            className={`bbox ${low ? "low" : ""} ${active ? "active" : ""}`}
            style={{
              left: `${b.bbox.x * 100}%`,
              top: `${b.bbox.y * 100}%`,
              width: `${b.bbox.width * 100}%`,
              height: `${b.bbox.height * 100}%`,
            }}
          />
        );
      })}
      </div>
      )}
    </div>
  );
}
