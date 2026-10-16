import type { DocumentResult } from "./types";

const env = (import.meta as unknown as {
  env: { VITE_API_BASE?: string };
}).env;

const API_BASE = env.VITE_API_BASE || window.location.origin;
export const apiBase = API_BASE;

const TOKEN_KEY = "intel2doc_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

function headers(base: Record<string, string> = {}): Record<string, string> {
  const t = getToken();
  return t ? { ...base, Authorization: `Bearer ${t}` } : base;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: headers(init?.headers as Record<string, string>),
  });
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    setToken(null);
    window.dispatchEvent(new CustomEvent("intel2doc:unauthorized"));
    throw new Error("Session expired — please sign in again.");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

// ---------- Types ----------
export interface AuthUser {
  id: string;
  username: string;
  name: string;
  title: string;
  email: string;
  role: string;
  role_label: string;
  permissions: string[];
}
export interface AuthConfig {
  sso_enabled: boolean;
  sso_provider_label: string;
  auth_enabled: boolean;
  demo_users: { username: string; role: string }[];
}
export interface HealthInfo {
  status: string;
  extractor: string;
  auth_enabled: boolean;
  sso_enabled: boolean;
  ocr_available: boolean;
  workflows: string[];
  assets: string[];
  ollama?: {
    reachable: boolean;
    model_available: boolean | null;
    model: string;
    host?: string;
    authenticated?: boolean;
    error?: string;
  };
}
export interface RbacModule {
  id: string;
  label: string;
  icon: string;
  description: string;
  actions: { id: string; label: string }[];
}
export interface RbacRole {
  id: string;
  label: string;
  description: string;
  system?: boolean;
  permissions: string[];
}
export interface RbacConfig {
  modules: RbacModule[];
  roles: RbacRole[];
}
export interface Insight {
  title: string;
  detail: string;
  tone: "positive" | "warning" | "info";
}
export interface DashboardData {
  summary: Record<string, number>;
  timeseries: { date: string; total: number; auto: number; review: number }[];
  by_type: { type: string; count: number }[];
  by_workflow: { workflow: string; count: number }[];
  routing: { auto_approved: number; in_review: number };
  confidence_buckets: { bucket: string; count: number }[];
  top_failed_rules: { rule: string; failures: number }[];
  by_officer: {
    name: string;
    role: string;
    processed: number;
    corrections: number;
    avg_confidence: number;
  }[];
}

// ---------- Auth ----------
export const getAuthConfig = () => req<AuthConfig>("/api/auth/config");
export const getHealth = () => req<HealthInfo>("/api/health");
export async function login(username: string, password: string): Promise<AuthUser> {
  const r = await req<{ token: string; user: AuthUser }>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  setToken(r.token);
  return r.user;
}
export async function ssoLogin(role?: string): Promise<AuthUser> {
  const r = await req<{ token: string; user: AuthUser }>("/api/auth/sso", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  setToken(r.token);
  return r.user;
}
export const getMe = () => req<AuthUser>("/api/auth/me");

// ---------- RBAC / Users ----------
export const getRbac = () => req<RbacConfig>("/api/rbac");
export const updateRolePermissions = (roleId: string, permissions: string[]) =>
  req<RbacRole>(`/api/rbac/roles/${roleId}/permissions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ permissions }),
  });
export const listUsers = () => req<AuthUser[]>("/api/users");

// ---------- Analytics ----------
export const getDashboard = () => req<DashboardData>("/api/analytics/overview");
export const runAnalyze = () =>
  req<{ insights: Insight[] }>("/api/analytics/analyze", { method: "POST" });

// ---------- Documents ----------
export const listAssets = () => req<string[]>("/api/assets");
export function assetImageUrl(name: string): string {
  return `${API_BASE}/api/assets/${encodeURIComponent(name)}/image`;
}
export function absoluteImageUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl) return null;
  return imageUrl.startsWith("http") ? imageUrl : `${API_BASE}${imageUrl}`;
}
export const processAsset = (name: string) =>
  req<DocumentResult>(`/api/assets/${encodeURIComponent(name)}`, { method: "POST" });
export const runWorkflowDemo = (workflow: string) =>
  req<DocumentResult>(`/api/demo/${workflow}`, { method: "POST" });

export async function processUpload(file: File): Promise<DocumentResult> {
  const form = new FormData();
  form.append("file", file);
  return req<DocumentResult>("/api/documents/process", { method: "POST", body: form });
}
/** Page-1 picture of a PDF / Word file (object URL), or null when none can be made. */
export async function previewUpload(file: File): Promise<string | null> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/documents/preview`, { method: "POST", body: form, headers: headers() });
  if (!res.ok) return null;
  return URL.createObjectURL(await res.blob());
}
export const correctField = (
  docId: string,
  subIndex: number,
  fieldName: string,
  newValue: unknown,
  approve: boolean
) =>
  req<DocumentResult>(`/api/documents/${docId}/correct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sub_index: subIndex, field_name: fieldName, new_value: newValue, approve }),
  });

// ---------- Past scans & folders ----------
export interface ScanMeta {
  id: string;
  source_name: string;
  doc_type: string;
  route: string;
  engine: string;
  approved: boolean;
  folder_id: string | null;
  created_at: string;
}
export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  count: number;
  created_at?: string;
}
export const listScans = (folderId?: string | null, all = false) => {
  const q = all ? "?all=true" : folderId ? `?folder_id=${encodeURIComponent(folderId)}` : "?folder_id=";
  return req<ScanMeta[]>(`/api/scans${q}`);
};
export const getScan = (id: string) => req<DocumentResult>(`/api/documents/${id}`);
export const deleteScan = (id: string) => req<{ ok: boolean }>(`/api/scans/${id}`, { method: "DELETE" });
export const moveScan = (id: string, folderId: string | null) =>
  req(`/api/scans/${id}/folder`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ folder_id: folderId }) });
export const listFolders = () => req<Folder[]>("/api/folders");
export const createFolder = (name: string, parentId: string | null) =>
  req<Folder>("/api/folders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, parent_id: parentId }) });
export const renameFolder = (id: string, name: string) =>
  req(`/api/folders/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
export const deleteFolder = (id: string) => req(`/api/folders/${id}`, { method: "DELETE" });

// ---------- Business rules ----------
export interface DocPolicy { doc_type: string; action: "auto_approve" | "review" | "reject"; note: string; }
export interface BusinessRules { min_confidence: number; auto_reject_unknown: boolean; policies: DocPolicy[]; }
export const getBusinessRules = () => req<BusinessRules>("/api/business-rules");
export const updateBusinessRules = (cfg: BusinessRules) =>
  req<BusinessRules>("/api/business-rules", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cfg) });

// ---------- Subscription / API / connectors ----------
export interface ApiKey { id: string; label: string; prefix: string; last4: string; created: string; active: boolean; secret?: string; }
export interface Connector { id: string; name: string; type: string; status: string; }
export interface Subscription {
  plan: { name: string; docs_per_month: number; docs_used: number; seats: number; renews: string };
  webhook_url: string;
  api_keys: ApiKey[];
  connectors: Connector[];
}
export const getSubscription = () => req<Subscription>("/api/subscription");
export const createApiKey = (label: string) =>
  req<ApiKey>("/api/subscription/keys", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label }) });
export const revokeApiKey = (id: string) => req<Subscription>(`/api/subscription/keys/${id}`, { method: "DELETE" });
export const updateConnector = (id: string, status: string) =>
  req<Subscription>(`/api/subscription/connectors/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
export const updateWebhook = (url: string) =>
  req<Subscription>("/api/subscription/webhook", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
export interface ExportTarget { id: string; name: string; type: string; }
export const getExportTargets = () => req<{ targets: ExportTarget[] }>("/api/subscription/targets");
export const exportScan = (id: string, target: string) =>
  req<{ ok: boolean; message: string; reference?: string; at: string }>(`/api/scans/${id}/export`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target }),
  });

// ---------- Analytics (geo) ----------
export interface GeoData {
  by_origin: { country: string; code: string; count: number }[];
  trade_lanes: { origin: string; origin_code: string; destination: string; destination_code?: string; count: number }[];
  confidence_by_country: { country: string; code: string; avg_confidence: number; docs: number }[];
  destinations: { country: string; count: number }[];
  lowest_confidence: { country: string; avg_confidence: number }[];
  highest_confidence: { country: string; avg_confidence: number }[];
}
export const getGeo = () => req<GeoData>("/api/analytics/geo");
export const analyzeGeo = () => req<{ insights: Insight[] }>("/api/analytics/geo/analyze", { method: "POST" });

// ---------- User guide ----------
export interface GuideSection { id: string; title: string; permission: string | null; body: string; }
export const getGuide = () => req<{ sections: GuideSection[]; can_edit: boolean }>("/api/guide");
export const updateGuideSection = (id: string, title: string, body: string) =>
  req<GuideSection>(`/api/guide/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, body }) });
