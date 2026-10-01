import type { PrevisionInput, DirectPrevisionInput, PrevisionOutput, ClimateData } from '../types/api';

const DEFAULT_API_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  return localStorage.getItem('kiplanto_api_url') || DEFAULT_API_URL;
}

export function setApiBaseUrl(url: string): void {
  const sanitized = url.trim().replace(/\/$/, '');
  localStorage.setItem('kiplanto_api_url', sanitized);
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
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/ai/prevision`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    let errorDetail = 'Erro ao processar previsão';
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function predictCropDirect(data: DirectPrevisionInput): Promise<PrevisionOutput> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/ai/prevision/direct`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    let errorDetail = 'Erro na simulação direta';
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function getCityClimate(city: string): Promise<{ status: string; coordinates: Record<string, unknown>; climate: ClimateData }> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/ai/climate/${encodeURIComponent(city)}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) {
    let errorDetail = `Erro ao buscar clima para ${city}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function getSupportedCrops(): Promise<{ total_crops: number; crops: string[] }> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/ai/crops`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!res.ok) {
    throw new Error('Não foi possível obter lista de culturas');
  }

  return res.json();
}
