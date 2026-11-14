'use client';

import { createContext, useCallback, useContext, useEffect, useState, useSyncExternalStore } from 'react';
import { api } from './api';
import type { User } from '../types';

const subscribeToHydration = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;
// Keep sensitive forms disabled in server HTML until their handlers are attached.
export function useHydrated() {
  return useSyncExternalStore(subscribeToHydration, clientSnapshot, serverSnapshot);
}

export function useQuery<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [resolvedKey, setResolvedKey] = useState('');
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);
  const requestKey = `${path}#${version}`;
  useEffect(() => {
    let active = true;
    if (path) api<T>(path).then((value) => { if (active) { setData(value); setError(''); } }).catch((reason: Error) => { if (active) { setError(reason.message); setData(null); } }).finally(() => { if (active) setResolvedKey(requestKey); });
    return () => { active = false; };
  }, [path, version, requestKey]);
  return { data: resolvedKey === requestKey ? data : null, error: resolvedKey === requestKey ? error : '', loading: Boolean(path) && resolvedKey !== requestKey, reload };
}

type AuthValue = { user: User | null; loading: boolean; refresh: () => Promise<void> };
const AuthContext = createContext<AuthValue>({ user: null, loading: true, refresh: async () => {} });
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try { let result = await api<{ user: User | null }>('/auth/session'); if (!result.user) { try { await api('/auth/refresh', { method: 'POST' }); result = await api<{ user: User | null }>('/auth/session'); } catch { /* A visitor has no refresh cookie. */ } } setUser(result.user); } catch { setUser(null); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);
  return <AuthContext.Provider value={{ user, loading, refresh }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
