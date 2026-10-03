import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  getMe,
  getToken,
  login as apiLogin,
  setToken,
  ssoLogin as apiSso,
  type AuthUser,
} from "./api";

interface AuthCtx {
  user: AuthUser | null;
  ready: boolean;
  login: (u: string, p: string) => Promise<void>;
  sso: (role?: string) => Promise<void>;
  logout: () => void;
  can: (perm: string) => boolean;
  canAny: (perms: string[]) => boolean;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await getMe());
    } catch {
      setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
    const onUnauth = () => setUser(null);
    window.addEventListener("intel2doc:unauthorized", onUnauth);
    return () => window.removeEventListener("intel2doc:unauthorized", onUnauth);
  }, [refresh]);

  const login = useCallback(async (u: string, p: string) => {
    setUser(await apiLogin(u, p));
  }, []);

  const sso = useCallback(async (role?: string) => {
    setUser(await apiSso(role));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const can = useCallback(
    (perm: string) => !!user && user.permissions.includes(perm),
    [user]
  );
  const canAny = useCallback(
    (perms: string[]) => !!user && perms.some((p) => user.permissions.includes(p)),
    [user]
  );

  return (
    <Ctx.Provider value={{ user, ready, login, sso, logout, can, canAny, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
