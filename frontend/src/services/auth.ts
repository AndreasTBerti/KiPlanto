import type { AuthUser } from '../types/api';
import { apiFetch, getApiBaseUrl, readErrorMessage } from './api';
import { clearToken, getToken, setToken } from './session';

/** Cadastro e login não usam apiFetch: nessas telas, um 401 é senha errada, não sessão expirada. */
async function requestSession(path: string, body: object, fallback: string): Promise<AuthUser> {
  let res: Response;
  try {
    res = await fetch(`${getApiBaseUrl()}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Não foi possível conectar ao servidor.');
  }
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, fallback));
  }
  const data: { token: string; user: AuthUser } = await res.json();
  setToken(data.token);
  return data.user;
}

export function login(email: string, password: string): Promise<AuthUser> {
  return requestSession('/auth/login', { email, password }, 'Não foi possível entrar.');
}

export function register(name: string, email: string, password: string): Promise<AuthUser> {
  return requestSession('/auth/register', { name, email, password }, 'Não foi possível criar a conta.');
}

/** A conta da sessão guardada; null se não há sessão válida. Falha de rede sobe como erro. */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  if (!getToken()) return null;
  const res = await apiFetch('/auth/me', { headers: { 'Accept': 'application/json' } });
  if (res.status === 401) return null;
  if (!res.ok) throw new Error('Não foi possível verificar a sessão.');
  return res.json();
}

/** Sai mesmo sem conseguir avisar o servidor: o token some deste navegador. */
export async function logout(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } catch {
    // sem rede: a sessão expira sozinha no servidor
  } finally {
    clearToken();
  }
}
