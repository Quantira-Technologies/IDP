import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { Icon } from "../components/Icons";
import { AiStatusPill } from "../components/AiStatus";
import { Tutorials } from "../components/Tutorials";
import { getTheme, toggleTheme, type Theme } from "../theme";
import { Dashboard } from "../pages/Dashboard";
import { Documents } from "../pages/Documents";
import { Analytics } from "../pages/Analytics";
import { AccessControl } from "../pages/AccessControl";
import { Users } from "../pages/Users";
import { BusinessRules } from "../pages/BusinessRules";
import { Subscription } from "../pages/Subscription";
import { UserGuide } from "../pages/UserGuide";

interface NavItem { id: string; label: string; icon: string; perm: string; render: () => React.ReactNode; }

const NAV: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "grid", perm: "dashboard.view", render: () => <Dashboard /> },
  { id: "documents", label: "Documents", icon: "file", perm: "documents.view", render: () => <Documents /> },
  { id: "analytics", label: "Analytics", icon: "chart", perm: "analytics.view", render: () => <Analytics /> },
  { id: "rules", label: "Business Rules", icon: "rules", perm: "business_rules.view", render: () => <BusinessRules /> },
  { id: "subscription", label: "API & Subscription", icon: "plug", perm: "subscription.view", render: () => <Subscription /> },
  { id: "users", label: "Users", icon: "users", perm: "users.view", render: () => <Users /> },
  { id: "access", label: "Access Control", icon: "shield", perm: "access_control.view", render: () => <AccessControl /> },
  { id: "guide", label: "User Guide", icon: "book", perm: "user_guide.view", render: () => <UserGuide /> },
];

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function AppShell() {
  const { user, logout, can } = useAuth();
  const { t, lang, toggle: toggleLang } = useI18n();
  const items = useMemo(() => NAV.filter((n) => can(n.perm)), [can]);
  const navIds = useMemo(() => items.map((i) => i.id), [items]);
  const [active, setActive] = useState(items[0]?.id ?? "dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(localStorage.getItem("intel2doc_nav_collapsed") === "1");
  const [theme, setThemeState] = useState<Theme>(getTheme());
  const [tutorialSignal, setTutorialSignal] = useState(0);

  useEffect(() => {
    if (!items.find((i) => i.id === active) && items[0]) setActive(items[0].id);
  }, [items, active]);

  const onNav = useCallback((id: string) => setActive(id), []);
  const onDrawer = useCallback((o: boolean) => setMobileOpen(o), []);

  // BUG-003: trap the browser Back button so it can't break app routing.
  // Re-push a history entry on every popstate, keeping the user inside the app.
  useEffect(() => {
    window.history.pushState(null, "", window.location.href);
    const onPop = () => window.history.pushState(null, "", window.location.href);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // BUG-002: let KPI cards (and other views) navigate via a decoupled event.
  useEffect(() => {
    const onNavEvent = (e: Event) => {
      const id = (e as CustomEvent<string>).detail;
      if (id) setActive(id);
    };
    window.addEventListener("intel2doc:nav", onNavEvent as EventListener);
    return () => window.removeEventListener("intel2doc:nav", onNavEvent as EventListener);
  }, []);

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("intel2doc_nav_collapsed", next ? "1" : "0");
  }
  function onTheme() { setThemeState(toggleTheme()); }

  const current = items.find((i) => i.id === active) ?? items[0];

  return (
    <div className={`shell ${mobileOpen ? "nav-open" : ""} ${collapsed ? "collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="side-brand">
          <span className="side-mark"><Icon name="logo" size={22} /></span>
          <span className="side-name">intel<span className="accent">2</span>doc</span>
          <button className="collapse-btn only-desktop" onClick={toggleCollapse} title={t("Collapse sidebar")} aria-label={t("Collapse sidebar")}>
            <Icon name={collapsed ? "chevron" : "back"} size={16} />
          </button>
          <button className="side-close" onClick={() => setMobileOpen(false)} aria-label={t("Close menu")}><Icon name="x" size={18} /></button>
        </div>
        <nav className="side-nav">
          {items.map((n) => (
            <button key={n.id} data-tour={`nav-${n.id}`} className={`side-link ${active === n.id ? "active" : ""}`} onClick={() => { setActive(n.id); setMobileOpen(false); }} title={t(n.label)}>
              <Icon name={n.icon} size={19} />
              <span>{t(n.label)}</span>
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="side-org"><span className="org-dot" /><span>{t("Saudi Customs · Workspace")}</span></div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="icon-btn only-mobile" onClick={() => setMobileOpen(true)} aria-label={t("Open menu")}><Icon name="menu" size={20} /></button>
          <div className="crumb">
            <span className="crumb-app">intel2doc</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-page">{t(current?.label ?? "")}</span>
          </div>
          <div className="topbar-spacer" />
          <AiStatusPill />
          <button className="icon-btn" data-tour="tutorials-btn" onClick={() => setTutorialSignal((s) => s + 1)} title={t("Tutorials")}><Icon name="play" size={18} /></button>
          <div className="theme-toggle lang-toggle" role="group" aria-label={t("Language")}>
            <button className={lang === "en" ? "on" : ""} onClick={() => lang !== "en" && toggleLang()} title="English">EN</button>
            <button className={lang === "ar" ? "on" : ""} onClick={() => lang !== "ar" && toggleLang()} title="العربية">ع</button>
          </div>
          <div className="theme-toggle" data-tour="theme-toggle" role="group" aria-label={t("Language")}>
            <button className={theme === "light" ? "on" : ""} onClick={() => theme !== "light" && onTheme()} title={t("Light")}><Icon name="sun" size={15} /></button>
            <button className={theme === "dark" ? "on" : ""} onClick={() => theme !== "dark" && onTheme()} title={t("Dark")}><Icon name="moon" size={15} /></button>
          </div>
          <button className="icon-btn" aria-label={t("Notifications")}><Icon name="bell" size={19} /></button>
          <div className="user-menu">
            <button className="user-btn" onClick={() => setMenuOpen((o) => !o)}>
              <span className="avatar">{user?.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</span>
              <span className="user-meta">
                <span className="user-name">{user?.name}</span>
                <span className="user-role">{user?.role_label}</span>
              </span>
            </button>
            {menuOpen && (
              <>
                <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
                <div className="menu-pop">
                  <div className="menu-head">
                    <div className="avatar lg">{user?.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</div>
                    <div>
                      <div className="menu-name">{user?.name}</div>
                      <div className="menu-sub">{user?.title}</div>
                      <span className="role-badge sm">{pretty(user?.role ?? "")}</span>
                    </div>
                  </div>
                  <div className="menu-sep" />
                  <div className="menu-perms">{user?.permissions.length} {t("permissions")}</div>
                  <button className="menu-item" onClick={() => { setMenuOpen(false); setTutorialSignal((s) => s + 1); }}><Icon name="play" size={17} /> {t("Replay tutorial")}</button>
                  <button className="menu-item danger" onClick={logout}><Icon name="logout" size={17} /> {t("Sign out")}</button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="content">{current?.render()}</main>
      </div>

      {mobileOpen && <div className="nav-scrim" onClick={() => setMobileOpen(false)} />}
      <Tutorials
        permissions={user?.permissions ?? []}
        openSignal={tutorialSignal}
        navIds={navIds}
        onNav={onNav}
        onDrawer={onDrawer}
      />
    </div>
  );
}
