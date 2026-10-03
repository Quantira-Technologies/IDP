import { useEffect, useMemo, useState } from "react";
import { getRbac, updateRolePermissions, type RbacConfig } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icons";
import { PageHead } from "./Documents";

export function AccessControl() {
  const { can, refresh } = useAuth();
  const canManage = can("access_control.manage");
  const [cfg, setCfg] = useState<RbacConfig | null>(null);
  const [roleId, setRoleId] = useState<string>("");
  const [draft, setDraft] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRbac()
      .then((c) => {
        setCfg(c);
        const first = c.roles[0]?.id ?? "";
        setRoleId(first);
        setDraft(new Set(c.roles.find((r) => r.id === first)?.permissions ?? []));
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  const role = useMemo(() => cfg?.roles.find((r) => r.id === roleId), [cfg, roleId]);
  const original = useMemo(() => new Set(role?.permissions ?? []), [role]);
  const dirty = useMemo(() => {
    if (!role) return false;
    if (draft.size !== original.size) return true;
    for (const p of draft) if (!original.has(p)) return true;
    return false;
  }, [draft, original, role]);

  function selectRole(id: string) {
    setRoleId(id);
    setDraft(new Set(cfg?.roles.find((r) => r.id === id)?.permissions ?? []));
    setToast(null);
  }

  function toggle(perm: string) {
    if (!canManage) return;
    setDraft((d) => {
      const n = new Set(d);
      n.has(perm) ? n.delete(perm) : n.add(perm);
      return n;
    });
  }

  function toggleModule(moduleId: string, actionIds: string[], on: boolean) {
    if (!canManage) return;
    setDraft((d) => {
      const n = new Set(d);
      actionIds.forEach((a) => {
        const p = `${moduleId}.${a}`;
        on ? n.add(p) : n.delete(p);
      });
      return n;
    });
  }

  async function save() {
    if (!role) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateRolePermissions(role.id, Array.from(draft));
      setCfg((c) => c && { ...c, roles: c.roles.map((r) => (r.id === role.id ? { ...r, permissions: updated.permissions } : r)) });
      setDraft(new Set(updated.permissions));
      setToast("Permissions saved");
      refresh(); // refresh my own permissions in case I edited my role
      setTimeout(() => setToast(null), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  if (!cfg) return <div className="page"><PageHead title="Access Control" /><div className="alert" style={{ display: error ? "block" : "none" }}>⚠ {error}</div></div>;

  return (
    <div className="page">
      <PageHead
        title="Access Control"
        subtitle="Roles, modules & permissions — grant or revoke access with a click"
        actions={
          canManage &&
          role && (
            <button className="btn btn-primary" onClick={save} disabled={!dirty || saving}>
              {saving ? <span className="spinner" /> : dirty ? "Save changes" : "Saved"}
            </button>
          )
        }
      />
      {!canManage && <div className="note-bar"><Icon name="shield" size={16} /> You have view-only access. Ask a Platform Admin to change permissions.</div>}
      {toast && <div className="toast-ok">✓ {toast}</div>}
      {error && <div className="alert">⚠ {error}</div>}

      <div className="ac-layout">
        <div className="ac-roles">
          <div className="ac-roles-title">Roles</div>
          {cfg.roles.map((r) => (
            <button key={r.id} className={`ac-role ${r.id === roleId ? "active" : ""}`} onClick={() => selectRole(r.id)}>
              <div className="ac-role-top">
                <span className="ac-role-name">{r.label}</span>
                {r.system && <span className="badge-sys">system</span>}
              </div>
              <div className="ac-role-desc">{r.description}</div>
              <div className="ac-role-count">{r.permissions.length} permissions</div>
            </button>
          ))}
        </div>

        <div className="ac-matrix">
          {cfg.modules.map((m) => {
            const actionIds = m.actions.map((a) => a.id);
            const activeCount = actionIds.filter((a) => draft.has(`${m.id}.${a}`)).length;
            const allOn = activeCount === actionIds.length;
            return (
              <div className="ac-module" key={m.id}>
                <div className="ac-module-head">
                  <div className="ac-mod-ic"><Icon name={m.icon} size={18} /></div>
                  <div style={{ flex: 1 }}>
                    <div className="ac-mod-name">{m.label}</div>
                    <div className="ac-mod-desc">{m.description}</div>
                  </div>
                  {canManage && (
                    <button className="mini-btn" onClick={() => toggleModule(m.id, actionIds, !allOn)}>
                      {allOn ? "Clear all" : "Grant all"}
                    </button>
                  )}
                </div>
                <div className="ac-actions">
                  {m.actions.map((a) => {
                    const perm = `${m.id}.${a.id}`;
                    const on = draft.has(perm);
                    return (
                      <button key={a.id} className={`perm ${on ? "on" : ""} ${canManage ? "" : "ro"}`} onClick={() => toggle(perm)}>
                        <span className="perm-box">{on && <Icon name="check" size={12} />}</span>
                        {a.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
