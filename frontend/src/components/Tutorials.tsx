import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./Icons";

interface Step {
  id: string;
  permission: string | null;
  icon: string;
  title: string;
  body: string;
  target?: string; // data-tour key to spotlight (omit for a centered welcome)
  nav?: string;    // nav id to switch to before spotlighting
}

// Steps are gated by permission — a user only sees tutorials for what they can do.
// When a role gains a new module, its new step automatically appears for first-time users.
const STEPS: Step[] = [
  { id: "welcome", permission: null, icon: "logo", title: "Welcome to intel2doc", body: "A quick, guided tour of your workspace — tailored to your role. We'll point out each area as we go." },
  { id: "dashboard", permission: "dashboard.view", nav: "dashboard", target: "nav-dashboard", icon: "grid", title: "Your dashboard", body: "Start here for throughput, straight-through rate and confidence at a glance." },
  { id: "analyze", permission: "dashboard.analyze", nav: "dashboard", target: "analyze-btn", icon: "sparkle", title: "One-click insights", body: "Hit Analyze to generate AI insights over your operation." },
  { id: "documents", permission: "documents.view", nav: "documents", target: "nav-documents", icon: "file", title: "Documents", body: "Everything you scan lives here, private to you." },
  { id: "upload", permission: "documents.upload", nav: "documents", target: "dropzone", icon: "upload", title: "Scan anything", body: "Drop a file here — it's auto-cleaned and fully OCR'd, then routed by your business rules." },
  { id: "folders", permission: "documents.view", nav: "documents", target: "folders", icon: "folder", title: "Past scans & folders", body: "Organise consignments into folders, just like on your computer. They're private to you." },
  { id: "rules", permission: "business_rules.view", nav: "rules", target: "nav-rules", icon: "rules", title: "Business rules", body: "See (or configure) which document types are auto-approved, reviewed or rejected." },
  { id: "analytics", permission: "analytics.view", nav: "analytics", target: "nav-analytics", icon: "chart", title: "Trade analytics", body: "Origins, busiest lanes and extraction confidence by country." },
  { id: "subscription", permission: "subscription.view", nav: "subscription", target: "nav-subscription", icon: "plug", title: "API & ECM", body: "Generate API keys and connect ECM/ERP systems to push approved documents." },
  { id: "access", permission: "access_control.view", nav: "access", target: "nav-access", icon: "shield", title: "Access control", body: "Grant or revoke any capability for any role — changes apply instantly." },
  { id: "theme", permission: null, target: "theme-toggle", icon: "moon", title: "Light or dark", body: "Switch themes anytime — your choice is remembered." },
  { id: "replay", permission: null, target: "tutorials-btn", icon: "play", title: "Replay anytime", body: "Click here whenever you want to run this tour again. That's it — enjoy!" },
];

const SEEN_KEY = "intel2doc_seen_tutorials";
const isMobile = () => window.innerWidth <= 900;

function seenSet(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]")); } catch { return new Set(); }
}

export function Tutorials({
  permissions, openSignal, navIds, onNav, onDrawer,
}: {
  permissions: string[];
  openSignal: number;
  navIds: string[];
  onNav: (id: string) => void;
  onDrawer: (open: boolean) => void;
}) {
  const perms = useMemo(() => new Set(permissions), [permissions]);
  const steps = useMemo(
    () => STEPS.filter((s) => (s.permission === null || perms.has(s.permission)) && (!s.nav || navIds.includes(s.nav))),
    [perms, navIds]
  );

  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [ready, setReady] = useState(false);
  const tipRef = useRef<HTMLDivElement>(null);
  const autoOpened = useRef(false);
  const [pos, setPos] = useState<{ top: number; left: number; place: "above" | "below" }>({ top: 0, left: 0, place: "below" });

  // Auto-open ONCE on first login if there are unseen steps for this role.
  useEffect(() => {
    if (autoOpened.current || steps.length === 0) return;
    const seen = seenSet();
    if (steps.some((s) => !seen.has(s.id))) { autoOpened.current = true; setIdx(0); setOpen(true); }
  }, [steps]);

  // Manual re-open via the Tutorials button.
  useEffect(() => { if (openSignal > 0) { setIdx(0); setOpen(true); } }, [openSignal]);

  const step = steps[Math.min(idx, steps.length - 1)];

  // Navigate + locate the target element for the current step.
  useEffect(() => {
    if (!open || !step) return;
    let cancelled = false;
    setReady(false);
    setRect(null);

    const isNavTarget = step.target?.startsWith("nav-");
    if (step.nav) onNav(step.nav);
    onDrawer(!!(isNavTarget && isMobile()));

    if (!step.target) { setReady(true); return; }

    let tries = 0;
    const tick = () => {
      if (cancelled) return;
      const el = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (el) {
        el.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
        setTimeout(() => { if (!cancelled) { setRect(el.getBoundingClientRect()); setReady(true); } }, 240);
      } else if (tries++ < 10) {
        setTimeout(tick, 120);
      } else {
        setReady(true); // give up -> show as a centered card
      }
    };
    setTimeout(tick, step.nav ? 240 : 60);
    return () => { cancelled = true; };
  }, [open, idx, step, onNav, onDrawer]);

  // Keep the spotlight glued to the element on scroll/resize.
  useEffect(() => {
    if (!open || !step?.target) return;
    const on = () => {
      const el = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (el) setRect(el.getBoundingClientRect());
    };
    window.addEventListener("resize", on);
    window.addEventListener("scroll", on, true);
    return () => { window.removeEventListener("resize", on); window.removeEventListener("scroll", on, true); };
  }, [open, step]);

  // Position the coachmark near the spotlight.
  useLayoutEffect(() => {
    if (!rect) return;
    const tipH = tipRef.current?.offsetHeight ?? 170;
    const tipW = tipRef.current?.offsetWidth ?? 384;
    const spaceBelow = window.innerHeight - rect.bottom;
    const place: "above" | "below" = spaceBelow > tipH + 24 ? "below" : "above";
    const top = place === "below" ? rect.bottom + 14 : Math.max(12, rect.top - tipH - 14);
    const left = Math.min(Math.max(12, rect.left + rect.width / 2 - tipW / 2), window.innerWidth - tipW - 12);
    setPos({ top, left, place });
  }, [rect, idx]);

  function finish() {
    const seen = seenSet();
    steps.forEach((s) => seen.add(s.id));
    localStorage.setItem(SEEN_KEY, JSON.stringify([...seen]));
    onDrawer(false);
    setOpen(false);
  }

  if (!open || steps.length === 0 || !step) return null;
  const last = idx >= steps.length - 1;
  const centered = !step.target || (ready && !rect);

  const Coach = (
    <div className={`tour-tip ${centered ? "" : "floating"}`} ref={tipRef} style={centered ? undefined : { top: pos.top, left: pos.left }}>
      <div className="tour-tip-hero">
        <div className="tut-step-ic"><Icon name={step.icon} size={22} /></div>
        <h3>{step.title}</h3>
        <p>{step.body}</p>
      </div>
      <div className="tut-foot">
        <div className="tut-dots">{steps.map((s, i) => <span key={s.id} className={`tut-dot ${i === idx ? "on" : ""}`} />)}</div>
        <div style={{ flex: 1 }} />
        <button className="btn btn-ghost" onClick={finish}>Skip</button>
        {idx > 0 && <button className="btn" onClick={() => setIdx((i) => i - 1)}>Back</button>}
        <button className="btn btn-primary" onClick={() => (last ? finish() : setIdx((i) => i + 1))}>{last ? "Done" : "Next"}</button>
      </div>
    </div>
  );

  if (centered) {
    return <div className="tut-scrim">{Coach}</div>;
  }

  return (
    <>
      <div className="tour-overlay" />
      {rect && (
        <div className="tour-highlight" style={{ top: rect.top - 6, left: rect.left - 6, width: rect.width + 12, height: rect.height + 12 }} />
      )}
      {Coach}
    </>
  );
}
