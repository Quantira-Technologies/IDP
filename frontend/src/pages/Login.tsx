import React, { useEffect, useState } from "react";
import { getAuthConfig, type AuthConfig } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { Icon } from "../components/Icons";

export function Login() {
  const { login, sso } = useAuth();
  const { t, lang, toggle: toggleLang } = useI18n();
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAuthConfig().then(setCfg).catch(() => setCfg(null));
  }, []);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy("login");
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("Sign in failed"));
    } finally {
      setBusy(null);
    }
  }

  async function onSso() {
    setBusy("sso");
    setError(null);
    try {
      await sso("customs_officer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "SSO failed");
    } finally {
      setBusy(null);
    }
  }

  function quickFill(u: string) {
    setUsername(u);
    setPassword(
      {
        admin: "Admin@123",
        tenantadmin: "Tenant@123",
        director: "Director@123",
        manager: "Manager@123",
        officer: "Officer@123",
      }[u] || ""
    );
  }

  return (
    <div className="login">
      <button type="button" className="login-lang" onClick={toggleLang} title={t("Language")}>
        <Icon name="globe" size={16} /> {lang === "ar" ? "English" : "العربية"}
      </button>
      <div className="login-brand">
        <div className="lb-orbits" aria-hidden="true">
          <span /><span /><span />
        </div>
        <div className="lb-content">
          <div className="lb-logo">
            <span className="lb-mark"><Icon name="logo" size={26} /></span>
            intel<span className="accent">2</span>doc
          </div>
          <h1>{t("Every document, understood.")}</h1>
          <p>
            {t("Enterprise document intelligence for customs & trade — classify, extract, validate and route any invoice, certificate or declaration, with every field traced to its source.")}
          </p>
          <ul className="lb-points">
            <li><Icon name="check" size={18} /> {t("OCR for any uploaded document — Arabic & English")}</li>
            <li><Icon name="check" size={18} /> {t("Business-rule validation, not just data capture")}</li>
            <li><Icon name="check" size={18} /> {t("Role-based access, audit-ready by design")}</li>
          </ul>
        </div>
        <div className="lb-foot">{t("Secure workspace · Saudi Customs")}</div>
      </div>

      <div className="login-form-wrap">
        <form className="login-card" onSubmit={onLogin}>
          <h2>{t("Sign in")}</h2>
          <p className="muted">{t("Access your intel2doc workspace")}</p>

          {error && <div className="alert" style={{ margin: "0 0 14px" }}>⚠ {error}</div>}

          <label className="fld">
            <span>{t("Username")}</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. officer" autoFocus />
          </label>
          <label className="fld">
            <span>{t("Password")}</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </label>

          <button className="btn btn-primary btn-block" type="submit" disabled={busy !== null}>
            {busy === "login" ? <span className="spinner" /> : t("Sign in")}
          </button>

          {cfg?.sso_enabled && (
            <>
              <div className="divider"><span>{t("or")}</span></div>
              <button type="button" className="btn btn-sso btn-block" onClick={onSso} disabled={busy !== null}>
                {busy === "sso" ? <span className="spinner" /> : <><Icon name="shield" size={18} /> {t("Continue with")} {cfg.sso_provider_label}</>}
              </button>
            </>
          )}

          <div className="demo-users">
            <span className="demo-label">{t("Demo accounts (click to fill):")}</span>
            <div className="demo-chips">
              {(cfg?.demo_users ?? []).map((u) => (
                <button type="button" key={u.username} className="demo-chip" onClick={() => quickFill(u.username)}>
                  <b>{u.role}</b>
                  <span>{u.username}</span>
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
