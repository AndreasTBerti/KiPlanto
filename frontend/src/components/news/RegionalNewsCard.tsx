import React, { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, CalendarDays, Newspaper, Sprout } from 'lucide-react';
import type {
  CrossCandidate,
  CrossCandidateStatus,
  CrossRecommendationOutput,
  NewsArticle,
  NewsQuery,
  PrevisionOutput,
} from '../../types/api';
import { getCrossRecommendation } from '../../services/api';
import { CrossReportPanel } from './CrossReportPanel';
import { NewsImage } from './NewsImage';
import type { NewsIntent } from './newsUtils';
import {
  NEWS_DEFAULT_DAYS,
  NEWS_WIDE_DAYS,
  errorMessage,
  formatRelativeDate,
  locationBadge,
  placeLabel,
} from './newsUtils';

interface RegionalNewsCardProps {
  /** Cidade e UF já resolvidas pela API de recomendação. */
  city: string;
  uf?: string;
  /** Valores entregues ao modelo: a API recalcula as probabilidades de todas as culturas. */
  features: NonNullable<PrevisionOutput['features']>;
  onOpenNews: (intent: NewsIntent) => void;
}

type LoadState = { key: string; data?: CrossRecommendationOutput; error?: string; selected?: string };

const SECONDARY_HEADLINES = 3;

const badgeBase = 'px-1.5 py-0.5 rounded-md border text-[10px] font-semibold';

const STATUS_TEXT: Record<CrossCandidateStatus, string> = {
  news: 'text-emerald-300',
  alert: 'text-amber-300',
  generic_news: 'text-slate-400',
  no_news: 'text-slate-400',
  unavailable: 'text-slate-400',
};

const ArticleMeta: React.FC<{ article: NewsArticle }> = ({ article }) => {
  const when = formatRelativeDate(article.published_at);
  return (
    <span className="block text-[11px] font-mono text-slate-400">
      {article.source_name}
      {when ? ` · ${when}` : ''}
    </span>
  );
};

const CandidateTabs: React.FC<{
  candidates: CrossCandidate[];
  selected: CrossCandidate;
  onSelect: (crop: string) => void;
}> = ({ candidates, selected, onSelect }) => (
  <div className="flex flex-wrap gap-2" role="group" aria-label="Culturas próximas no modelo">
    {candidates.map((candidate) => {
      const isActive = candidate.crop === selected.crop;
      return (
        <button
          key={candidate.crop}
          type="button"
          onClick={() => onSelect(candidate.crop)}
          aria-pressed={isActive}
          className={`px-3 py-1.5 rounded-lg border text-xs text-left transition-colors cursor-pointer ${
            isActive
              ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-200'
              : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
          }`}
        >
          <span className="font-semibold">{candidate.name}</span>
          <span className="font-mono text-slate-400">
            {' '}
            {candidate.probability}% · {candidate.regional_news} na região
          </span>
        </button>
      );
    })}
  </div>
);

const LoadingNews: React.FC = () => (
  <div className="space-y-3" aria-label="Carregando notícias">
    <p className="text-xs text-slate-400">Lendo as notícias com IA. Isso pode levar alguns segundos.</p>
    <div className="space-y-3 animate-pulse">
      <div className="h-3 w-3/4 bg-slate-800 rounded" />
      <div className="aspect-video bg-slate-800/60 rounded-lg" />
      <div className="h-5 w-11/12 bg-slate-800 rounded" />
      <div className="h-3 w-full bg-slate-800/70 rounded" />
      <div className="h-3 w-5/6 bg-slate-800/70 rounded" />
    </div>
  </div>
);

/**
 * Notícias da região cruzadas com o modelo: sai no topo da coluna de resultado, em destaque.
 * Carrega em paralelo, sem bloquear a recomendação, que já está na tela.
 */
export const RegionalNewsCard: React.FC<RegionalNewsCardProps> = ({ city, uf, features, onOpenNews }) => {
  const requestKey = JSON.stringify([city, uf ?? '', features]);
  const [state, setState] = useState<LoadState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { N: n, P: p, K: k, temperature, humidity, rainfall } = features;
    getCrossRecommendation({ city, state: uf, n, p, k, temperature, humidity, rainfall }, controller.signal)
      .then((data) => setState({ key: requestKey, data }))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setState({ key: requestKey, error: errorMessage(err) });
      });
    return () => controller.abort();
  }, [requestKey, city, uf, features]);

  // Carregando enquanto o resultado guardado não for desta análise.
  const loading = state?.key !== requestKey;
  const data = loading ? undefined : state?.data;
  const selected = data?.candidates.find((c) => c.crop === state?.selected) ?? data?.candidates[0];
  const news = selected?.news;
  const place = news?.location ?? { city, uf };
  const query: NewsQuery = { city, state: uf, crop: selected?.crop, days: NEWS_DEFAULT_DAYS };
  const [lead, ...others] = news?.articles ?? [];
  const secondary = others.slice(0, SECONDARY_HEADLINES);

  const selectCandidate = (crop: string) => {
    setState((current) => (current ? { ...current, selected: crop } : current));
  };

  const openReportArticle = (candidate: CrossCandidate, articleId: string) => {
    if (!candidate.news) return;
    onOpenNews({
      query: { city, state: uf, crop: candidate.crop, days: NEWS_DEFAULT_DAYS },
      response: candidate.news,
      articleId,
    });
  };

  return (
    <section className="bg-slate-900/90 border border-amber-500/30 rounded-xl p-6 space-y-4" aria-busy={loading}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-bold text-white">
          <Newspaper className="w-5 h-5 text-amber-400" aria-hidden="true" />
          Notícias de {placeLabel(place)}
        </h2>
        {news && news.total > 0 && (
          <span className="text-[11px] font-mono text-slate-400">
            {news.total} {news.total === 1 ? 'notícia' : 'notícias'} · {NEWS_DEFAULT_DAYS} dias
          </span>
        )}
      </div>

      {loading && <LoadingNews />}

      {!loading && state?.error && (
        <p className="text-sm text-slate-400">Não foi possível cruzar com as notícias agora ({state.error}).</p>
      )}

      {data && selected && (
        <>
          <p className="flex items-start gap-2 text-sm leading-snug text-slate-200">
            <Sprout className="w-4 h-4 mt-0.5 shrink-0 text-emerald-400" aria-hidden="true" />
            {data.explanation}
          </p>

          <CrossReportPanel report={data.report} candidates={data.candidates} onOpenArticle={openReportArticle} />

          {data.candidates.length > 1 && (
            <CandidateTabs candidates={data.candidates} selected={selected} onSelect={selectCandidate} />
          )}

          <p className={`text-xs ${STATUS_TEXT[selected.status]}`}>
            <span className="font-semibold">{selected.name}:</span> {selected.summary}
            {selected.status === 'no_news' && lead ? ' Veja o mais próximo:' : ''}
          </p>

          {news && selected.alerts.length > 0 && (
            <ul className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1.5">
              {selected.alerts.slice(0, 2).map((alert) => (
                <li key={alert.article_id}>
                  <button
                    type="button"
                    onClick={() => onOpenNews({ query, response: news, articleId: alert.article_id })}
                    className="flex items-start gap-2 text-left text-xs text-amber-200 hover:text-amber-100 cursor-pointer"
                  >
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                    <span>
                      <span className="font-semibold">{alert.terms.join(', ')}:</span> {alert.title}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {news && lead && (
            <button
              type="button"
              onClick={() => onOpenNews({ query, response: news, articleId: lead.id })}
              className="group block w-full text-left cursor-pointer"
            >
              <div className="aspect-video overflow-hidden rounded-lg bg-slate-950 border border-slate-800">
                <NewsImage
                  src={lead.image_url}
                  alt=""
                  className="w-full h-full object-cover"
                  fallback={
                    <div className="w-full h-full flex items-center justify-center text-slate-700">
                      <Newspaper className="w-12 h-12" aria-hidden="true" />
                    </div>
                  }
                />
              </div>
              <span className="block mt-3">
                <ArticleMeta article={lead} />
              </span>
              <span className="block mt-1 text-xl font-bold leading-snug text-white group-hover:text-amber-200 transition-colors">
                {lead.title}
              </span>
              {lead.summary && (
                <span className="block mt-2 text-sm leading-relaxed text-slate-300 line-clamp-3">{lead.summary}</span>
              )}
              <span className="mt-2 flex flex-wrap gap-1.5">
                <span className={`${badgeBase} bg-amber-500/10 text-amber-300 border-amber-500/30`}>
                  {locationBadge(lead, news.location)}
                </span>
                {lead.crop_match && (
                  <span className={`${badgeBase} bg-emerald-500/10 text-emerald-300 border-emerald-500/30`}>
                    {selected.name}
                  </span>
                )}
              </span>
            </button>
          )}

          {news && secondary.length > 0 && (
            <ul className="divide-y divide-slate-800/80 border-t border-slate-800/80">
              {secondary.map((article) => (
                <li key={article.id}>
                  <button
                    type="button"
                    onClick={() => onOpenNews({ query, response: news, articleId: article.id })}
                    className="group w-full text-left py-2.5 cursor-pointer"
                  >
                    <ArticleMeta article={article} />
                    <span className="block text-sm font-medium leading-snug text-slate-100 line-clamp-2 group-hover:text-amber-200 transition-colors">
                      {article.title}
                    </span>
                    <span className="mt-1.5 flex flex-wrap gap-1.5">
                      <span className={`${badgeBase} bg-amber-500/10 text-amber-300 border-amber-500/30`}>
                        {locationBadge(article, news.location)}
                      </span>
                      {article.crop_match && (
                        <span className={`${badgeBase} bg-emerald-500/10 text-emerald-300 border-emerald-500/30`}>
                          {selected.name}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {data.also_cited.length > 0 && (
            <p className="text-xs text-slate-400">
              <span className="font-semibold text-slate-300">Também citadas na região:</span>{' '}
              {data.also_cited
                .map((c) => `${c.name} (${c.mentions} notícias, ${c.probability}% no modelo)`)
                .join(' · ')}
            </p>
          )}

          {news && !lead && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate-400">
                Nenhuma notícia para {placeLabel(news.location)} nos últimos {NEWS_DEFAULT_DAYS} dias.
              </p>
              <button
                type="button"
                onClick={() => onOpenNews({ query: { ...query, days: NEWS_WIDE_DAYS } })}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-300 hover:text-amber-200 cursor-pointer"
              >
                <CalendarDays className="w-3.5 h-3.5" aria-hidden="true" />
                Ampliar para {NEWS_WIDE_DAYS} dias
              </button>
            </div>
          )}

          {news && lead && (
            <button
              type="button"
              onClick={() => onOpenNews({ query, response: news })}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-300 hover:text-amber-200 cursor-pointer"
            >
              Ver todas as notícias de {selected.name}
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}
        </>
      )}
    </section>
  );
};
