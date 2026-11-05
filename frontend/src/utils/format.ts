const numberFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2, useGrouping: false });

/** Vírgula decimal e sem casas desnecessárias: 6,4. Sem valor, "--". */
export function formatNumber(value: number | null | undefined, minimumFractionDigits = 0): string {
  if (value == null) return '--';
  if (minimumFractionDigits === 0) return numberFormat.format(value);
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits,
    maximumFractionDigits: Math.max(minimumFractionDigits, 2),
    useGrouping: false,
  });
}

const groupedFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const moneyFormat = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Inteiro com separador de milhar: 22.145.776. Sem valor, "--". */
export function formatGrouped(value: number | null | undefined): string {
  return value == null ? '--' : groupedFormat.format(value);
}

/** Valor em reais com centavos, sem o símbolo: 1,09. Sem valor, "--". */
export function formatMoney(value: number | null | undefined): string {
  return value == null ? '--' : moneyFormat.format(value);
}

/** Aceita "6,4" e "6.4". Texto que não é número vira null. */
export function parseNumber(text: string): number | null {
  const normalized = text.trim().replace(',', '.');
  if (normalized === '') return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

const dateTimeFormat = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

/** "05/11/2026, 14:30". Data que não é possível ler volta como veio. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateTimeFormat.format(date);
}

/** Pontuação inteira de 0 a 100, sem "%". */
export function toScore(probability: number): number {
  return Math.round(Math.min(100, Math.max(0, probability)));
}

export type ConfidenceLevel = 'alta' | 'media' | 'baixa';

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  alta: 'Confiança alta',
  media: 'Confiança média',
  baixa: 'Confiança baixa',
};

/** Alta 70–100 · Média 40–69 · Baixa 0–39. */
export function confidenceLevel(score: number): ConfidenceLevel {
  if (score >= 70) return 'alta';
  if (score >= 40) return 'media';
  return 'baixa';
}
