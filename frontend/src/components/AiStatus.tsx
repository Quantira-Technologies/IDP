import { useEffect, useRef, useState } from "react";
import { getHealth, type HealthInfo } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "./Icons";

type Kind = "ai" | "fallback" | "ocr" | "sample";

/** Interpret a backend engine string into a friendly kind + label. */
export function classifyEngine(engine: string): { kind: Kind; model?: string } {
  const e = (engine || "").toLowerCase();
  if (e.includes("fallback") || e.includes("returned no fields")) return { kind: "fallback" };
  if (e.startsWith("ollama")) {
    const model = engine.split(":").slice(1).join(":").trim() || undefined;
    return { kind: "ai", model };
  }
  if (e.startsWith("ocr")) return { kind: "ocr" };
  if (e.includes("mock")) return { kind: "sample" };
  return { kind: "ocr" };
}

/** Per-document badge shown on the review / approved screens. */
export function EngineBadge({ engine }: { engine: string }) {
  const { t } = useI18n();
  const { kind, model } = classifyEngine(engine);
  const meta: Record<Kind, { label: string; icon: string }> = {
    ai: { label: model ? `${t("AI")} · ${model}` : t("AI extracted"), icon: "sparkle" },
    fallback: { label: t("AI fallback · OCR"), icon: "bell" },
    ocr: { label: t("OCR"), icon: "search" },
    sample: { label: t("Sample data"), icon: "file" },
  };
  const m = meta[kind];
  return (
    <span className={`engine-badge eb-${kind}`} title={engine}>
      {kind === "ai" && <span className="eb-dot" />}
      <Icon name={m.icon} size={13} />
      {m.label}
    </span>
  );
}

/** Global AI connectivity pill for the top bar (only shown when an AI engine is selected). */
export function AiStatusPill() {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = () => getHealth().then((h) => alive && setHealth(h)).catch(() => alive && setHealth(null));
    tick();
    timer.current = window.setInterval(tick, 30000);
    return () => {
      alive = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, []);

  const isAiEngine = health?.extractor === "ollama" || health?.extractor === "ollama_text";
  if (!health || !isAiEngine) return null;

  const o = health.ollama;
  const connected = !!o?.reachable;
  const model = o?.model ?? "";
  const title = connected
    ? `${t("AI connected")} — ${model} @ ${o?.host ?? ""}`
    : `${t("AI offline — using OCR fallback")}${o?.error ? ` (${o.error})` : ""}`;

  return (
    <span className={`ai-pill ${connected ? "ai-on" : "ai-off"}`} title={title}>
      <span className="ai-pill-dot" />
      <Icon name="sparkle" size={14} />
      <span className="ai-pill-text">{connected ? t("AI connected") : t("AI offline")}</span>
    </span>
  );
}
