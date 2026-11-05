import type {
  NewsArticle,
  NewsCrop,
  NewsLocation,
  NewsQuery,
  NewsResponse,
  NewsSourceFeed,
  PredictionHistoryItem,
} from '../../types/api';

/** Pedido para abrir a aba de notícias já com uma busca (e, opcionalmente, um artigo). */
export interface NewsIntent {
  query: NewsQuery;
  /** Resposta já carregada (ex.: pelo card da Recomendação): evita refazer a requisição. */
  response?: NewsResponse;
  articleId?: string;
}

/** A lista sempre pede o máximo da API. */
export const NEWS_LIST_LIMIT = 30;
export const NEWS_DEFAULT_DAYS = 30;
export const NEWS_WIDE_DAYS = 90;
export const NEWS_DAY_OPTIONS = [7, 30, 60, 90, 180];

export const NEWS_SOURCE_LABELS: Record<NewsSourceFeed, string> = {
  g1_estadual: 'g1 (estadual)',
  g1_agro: 'g1 Agronegócios',
  canal_rural: 'Canal Rural',
  portal_agronegocio: 'Portal do Agronegócio',
  globo_rural: 'Globo Rural',
  compre_rural: 'Compre Rural',
};

/** Busca da aba de notícias a partir da análise mais recente (a simulação manual não tem local). */
export function lastAnalysisQuery(history: PredictionHistoryItem[]): NewsQuery | null {
  const analysis = history.find((item) => item.uf && item.result.crop_recommendation);
  if (!analysis) return null;
  return {
    city: analysis.city,
    state: analysis.uf,
    crop: analysis.result.crop_recommendation?.toLowerCase(),
    days: NEWS_DEFAULT_DAYS,
  };
}

/** Notícias da cultura pedida que falam da região (cidade ou estado). */
export function regionalCropHits(articles: NewsArticle[]): number {
  return articles.filter((a) => a.crop_match && a.location_match !== 'outside').length;
}

export function placeLabel(location: Pick<NewsLocation, 'city' | 'uf'>): string {
  return location.uf ? `${location.city}/${location.uf}` : location.city;
}

/** Texto do badge de localização: cidade, UF, "Região" ou "Outras regiões". */
export function locationBadge(article: NewsArticle, location: NewsLocation): string {
  if (article.location_match === 'city') return location.city;
  if (article.location_match === 'state') return location.uf || location.state || 'Estado';
  if (article.location_match === 'outside') return 'Outras regiões';
  return 'Região';
}

function parseDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

const relativeFormat = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' });
const shortDateFormat = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' });
const shortDateWithYearFormat = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' });
const longDateFormat = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' });
const timeFormat = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' });

/** "há 3 h", "ontem", "há 2 dias" ou "21 out" (com ano se não for o ano corrente). */
export function formatRelativeDate(iso?: string | null, now: Date = new Date()): string | null {
  const date = parseDate(iso);
  if (!date) return null;
  const minutes = Math.round((now.getTime() - date.getTime()) / 60000);
  if (minutes < 60) return relativeFormat.format(-Math.max(minutes, 1), 'minute');
  const hours = Math.round(minutes / 60);
  if (hours < 24) return relativeFormat.format(-hours, 'hour');
  const days = Math.round(hours / 24);
  if (days < 7) return relativeFormat.format(-days, 'day');
  const format = date.getFullYear() === now.getFullYear() ? shortDateFormat : shortDateWithYearFormat;
  return format.format(date).replace(/\./g, '').replace(/ de /g, ' ');
}

/** "21 de outubro de 2026" */
export function formatLongDate(iso?: string | null): string | null {
  const date = parseDate(iso);
  return date ? longDateFormat.format(date) : null;
}

export function formatTime(iso?: string | null): string | null {
  const date = parseDate(iso);
  return date ? timeFormat.format(date) : null;
}

/** Motivos do box "Por que você está vendo isto". */
export function relevanceReasons(article: NewsArticle, location: NewsLocation, crop?: NewsCrop | null): string[] {
  const reasons: string[] = [];
  if (article.location_match === 'city') {
    reasons.push(`Menciona ${location.city}`);
  } else if (article.location_match === 'state') {
    reasons.push(`Menciona ${location.state || location.uf}`);
  } else if (article.location_match === 'outside') {
    reasons.push(`Não menciona ${placeLabel(location)}: vale pela cultura`);
  } else {
    reasons.push(`Publicada no feed regional do g1${location.state ? ` para ${location.state}` : ''}`);
  }
  if (article.matched_keywords.length) {
    reasons.push(`termos: ${article.matched_keywords.join(', ')}`);
  }
  if (article.crop_match && crop) {
    reasons.push(`cita ${crop.name}, a cultura recomendada pelo modelo`);
  }
  return reasons;
}

/** "3 de 4 fontes responderam (Canal Rural indisponível)" */
export function sourcesSummary(sources: NewsResponse['sources']): { text: string; partial: boolean } {
  const failed = sources.filter((s) => !s.ok);
  const base = `${sources.length - failed.length} de ${sources.length} fontes responderam`;
  if (!failed.length) return { text: base, partial: false };
  const names = failed.map((s) => NEWS_SOURCE_LABELS[s.source] ?? s.source).join(', ');
  return { text: `${base} (${names} ${failed.length > 1 ? 'indisponíveis' : 'indisponível'})`, partial: true };
}

export function errorMessage(err: unknown, fallback = 'Falha ao buscar notícias de colheita.'): string {
  return err instanceof Error && err.message ? err.message : fallback;
}
