import type { BoundingBox, Field, SubDocumentResult } from "../types";

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
}: {
  sub: SubDocumentResult;
  activeField: string | null;
  onPick: (name: string) => void;
  imageUrl?: string | null;
}) {
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
        <img src={imageUrl} alt={sub.doc_type} />
      ) : (
        <div className="sim-label">{sub.doc_type} — source page (simulated)</div>
      )}
      {boxes.length === 0 && (
        <div className="nobbox">no bounding boxes returned for this document</div>
      )}
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
  );
}
