import type { PredictionHistoryItem } from '../types/api';

// Antes do login havia um único histórico por navegador: a primeira conta a entrar fica com ele.
const LEGACY_HISTORY_KEY = 'kiplanto_history';
export const HISTORY_LIMIT = 50;

/**
 * Normaliza um registro lido do localStorage.
 * Registros gravados antes da correção de grafia só têm `result.crop_recomendation`;
 * o valor é copiado para `crop_recommendation`. Registros sem cultura são descartados.
 */
function migrateItem(raw: unknown): PredictionHistoryItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const item = raw as PredictionHistoryItem;
  if (!item.result || typeof item.result !== 'object') return null;
  if (!item.inputs || typeof item.inputs !== 'object') return null;

  const crop = item.result.crop_recommendation ?? item.result.crop_recomendation;
  if (typeof crop !== 'string' || !crop) return null;

  return { ...item, result: { ...item.result, crop_recommendation: crop } };
}

function historyKey(userId: number): string {
  return `${LEGACY_HISTORY_KEY}:${userId}`;
}

function adoptLegacyHistory(userId: number): void {
  const legacy = localStorage.getItem(LEGACY_HISTORY_KEY);
  if (legacy === null) return;
  if (localStorage.getItem(historyKey(userId)) === null) {
    localStorage.setItem(historyKey(userId), legacy);
  }
  localStorage.removeItem(LEGACY_HISTORY_KEY);
}

export function loadHistory(userId: number): PredictionHistoryItem[] {
  try {
    adoptLegacyHistory(userId);
    const saved = localStorage.getItem(historyKey(userId));
    const parsed: unknown = saved ? JSON.parse(saved) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(migrateItem)
      .filter((item): item is PredictionHistoryItem => item !== null)
      .slice(0, HISTORY_LIMIT);
  } catch {
    return [];
  }
}

export function saveHistory(userId: number, items: PredictionHistoryItem[]): void {
  try {
    localStorage.setItem(historyKey(userId), JSON.stringify(items));
  } catch {
    // Armazenamento cheio ou bloqueado: o histórico segue em memória.
  }
}

export function clearHistory(userId: number): void {
  try {
    localStorage.removeItem(historyKey(userId));
  } catch {
    // ignora
  }
}
