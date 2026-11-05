import type { PrevisionInput, DirectPrevisionInput, PrevisionOutput, ClimateData } from '../types/api';
import type { CrossRecommendationInput, CrossRecommendationOutput, NewsQuery, NewsResponse } from '../types/api';
import { clearToken, getToken } from './session';

// URL base da API. Vazio (padrão) = mesma origem: no `npm run dev` o proxy do
// Vite encaminha /ai, /auth, /health e /news para http://localhost:8000 (ver vite.config.ts).
// Para usar outro servidor, defina VITE_API_URL em frontend/.env.local.
const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/+$/, '');

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/**
 * Mensagem de erro de uma resposta da API. O FastAPI devolve `detail` como
 * texto (404/502) ou como lista de erros de validação (422).
 */
export async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await res.json();
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item: { loc?: unknown[]; msg?: unknown }) => {
          const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : undefined;
          const msg = String(item?.msg ?? '').replace(/^Value error, /, '');
          return field && typeof field === 'string' ? `${field}: ${msg}` : msg;
        })
        .filter(Boolean);
      if (messages.length) return messages.join('; ');
    }
  } catch {
    // corpo não é JSON
  }
  return fallback;
}

let onUnauthorized: (() => void) | null = null;

/** Avisa o App quando a API recusa a sessão (expirou ou foi encerrada). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

/** Chamada autenticada: envia o token da sessão e trata a recusa em um só lugar. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(`${getApiBaseUrl()}${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    clearToken();
    onUnauthorized?.();
  }
  return res;
}

export async function checkApiHealth(): Promise<{ ok: boolean; message: string; latencyMs: number }> {
  const baseUrl = getApiBaseUrl();
  const start = performance.now();
  try {
    const res = await fetch(`${baseUrl}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(4000)
    });
    const latencyMs = Math.round(performance.now() - start);
    if (res.ok) {
      return { ok: true, message: 'Online', latencyMs };
    }
    return { ok: false, message: `Status HTTP ${res.status}`, latencyMs };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - start);
    const msg = err instanceof Error ? err.message : 'Falha na conexão';
    return { ok: false, message: msg, latencyMs };
  }
}

export async function predictCrop(data: PrevisionInput): Promise<PrevisionOutput> {
  const res = await apiFetch(`/ai/prevision`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Erro ao processar previsão'));
  }

  return res.json();
}

export async function predictCropDirect(data: DirectPrevisionInput): Promise<PrevisionOutput> {
  const res = await apiFetch(`/ai/prevision/direct`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Erro na simulação direta'));
  }

  return res.json();
}

/** Cruza o modelo com as notícias da região; pode levar vários segundos. */
export async function getCrossRecommendation(
  data: CrossRecommendationInput,
  signal?: AbortSignal,
): Promise<CrossRecommendationOutput> {
  const res = await apiFetch(`/ai/cross-recommendation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
    signal,
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Erro ao cruzar a recomendação com as notícias'));
  }

  return res.json();
}

export interface CityCoordinates {
  city: string;
  country?: string;
  latitude: number;
  longitude: number;
  timezone?: string;
  state?: string;
  uf?: string;
}

export async function getCityClimate(
  city: string,
  state?: string,
): Promise<{ status: string; coordinates: CityCoordinates; climate: ClimateData }> {
  const query = state ? `?state=${encodeURIComponent(state)}` : '';
  const res = await apiFetch(`/ai/climate/${encodeURIComponent(city)}${query}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, `Erro ao buscar clima para ${city}`));
  }

  return res.json();
}

export async function getSupportedCrops(): Promise<{ total_crops: number; crops: string[] }> {
  const res = await apiFetch(`/ai/crops`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) {
    throw new Error('Não foi possível obter lista de culturas');
  }

  return res.json();
}

/**
 * Notícias de colheita para a cidade/UF (GET /news). Com `crop` (classe do modelo),
 * as notícias que citam a cultura recomendada sobem no ranking.
 */
export async function getHarvestNews(query: NewsQuery, signal?: AbortSignal): Promise<NewsResponse> {
  const params = new URLSearchParams({ city: query.city.trim() });
  if (query.state) params.set('state', query.state);
  if (query.days) params.set('days', String(query.days));
  if (query.limit) params.set('limit', String(query.limit));
  if (query.crop) params.set('crop', query.crop);

  const res = await apiFetch(`/news?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    signal,
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Erro ao buscar notícias de colheita'));
  }

  return res.json();
}
