import { useState } from "react";
import type { Field, SubDocumentResult } from "../types";
import { useI18n } from "../i18n";

/** Editable list of extracted fields with per-field confidence + correction. */
export function FieldList({
  sub,
  activeField,
  onPick,
  onCorrect,
}: {
  sub: SubDocumentResult;
  activeField: string | null;
  onPick: (name: string) => void;
  onCorrect?: (fieldName: string, newValue: string, approve: boolean) => void;
}) {
  const { t, num } = useI18n();
  return (
    <div>
      {Object.values(sub.extraction.fields).length > 0 && (
        <div className="field-group-title">{t("Header fields")}</div>
      )}
      {Object.values(sub.extraction.fields).map((f) => (
        <FieldRow
          key={f.name}
          field={f}
          active={activeField === f.name}
          onPick={() => onPick(f.name)}
          onCorrect={onCorrect ? (v, approve) => onCorrect(f.name, v, approve) : undefined}
        />
      ))}

      {sub.extraction.line_items.length > 0 && (
        <div className="field-group-title">{t("Line items")}</div>
      )}
      {sub.extraction.line_items.map((li, i) => (
        <div className="lineitem" key={i}>
          <div className="li-label">{t("Line")} {num(i + 1)}</div>
          {Object.values(li.fields).map((f) => (
            <FieldRow
              key={f.name}
              field={f}
              readOnly
              active={activeField === `line${i + 1}.${f.name}`}
              onPick={() => onPick(`line${i + 1}.${f.name}`)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function FieldRow({
  field,
  active,
  readOnly,
  onPick,
  onCorrect,
}: {
  field: Field;
  active: boolean;
  readOnly?: boolean;
  onPick: () => void;
  onCorrect?: (newValue: string, approve: boolean) => void;
}) {
  const { t, num } = useI18n();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(field.value ?? ""));
  const low = field.confidence < 0.8;
  const pct = Math.round(field.confidence * 100);

  return (
    <div className={`field ${active ? "active" : ""}`} onClick={onPick}>
      <div className="fname">{field.name}</div>
      {editing ? (
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          autoFocus
        />
      ) : (
        <div className="fval">
          {String(field.value ?? "—")}
          {field.corrected && <span className="fixed">✓ {t("fixed")}</span>}
        </div>
      )}
      <span className={`conf ${low ? "low" : ""}`} title={`confidence ${pct}%`}>
        <span className="bar">
          <i style={{ width: `${pct}%` }} />
        </span>
        <span className="pct">{num(pct)}%</span>
      </span>
      {!readOnly &&
        onCorrect &&
        (editing ? (
          <button
            className="mini-btn"
            onClick={(e) => {
              e.stopPropagation();
              onCorrect(draft, false);
              setEditing(false);
            }}
          >
            {t("Save")}
          </button>
        ) : (
          <button
            className="mini-btn"
            onClick={(e) => {
              e.stopPropagation();
              setEditing(true);
            }}
          >
            {t("Edit")}
          </button>
        ))}
    </div>
  );
}
