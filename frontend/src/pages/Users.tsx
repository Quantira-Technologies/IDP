import { useEffect, useState } from "react";
import { listUsers, type AuthUser } from "../api";
import { PageHead } from "./Documents";

const pretty = (s: string) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function Users() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    listUsers().then(setUsers).catch((e) => setError(String(e.message || e)));
  }, []);
  return (
    <div className="page">
      <PageHead title="Users" subtitle="People and their role assignments" />
      {error && <div className="alert">⚠ {error}</div>}
      <div className="panel">
        <div className="panel-body">
          <table className="tbl">
            <thead><tr><th>Name</th><th>Title</th><th>Email</th><th>Role</th><th>Permissions</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="user-cell">
                      <span className="avatar sm">{u.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</span>
                      <b>{u.name}</b>
                    </div>
                  </td>
                  <td>{u.title}</td>
                  <td className="muted">{u.email}</td>
                  <td><span className="role-badge">{pretty(u.role)}</span></td>
                  <td>{u.permissions.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
