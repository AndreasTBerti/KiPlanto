import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { CalendarDays, Newspaper, Search } from 'lucide-react';
import type { NewsArticle, NewsQuery, NewsResponse } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { getHarvestNews } from '../../services/api';
import { COMMON_CITIES } from '../../constants/cities';
import { CityPicker } from '../CityPicker';
import { NewsCard, NewsCardSkeleton } from '../news/NewsCard';
import { ArticleView } from '../news/ArticleView';
import { Button } from '../ui/Button';
import { Notice } from '../ui/Notice';
import { CulturaIcon } from '../ui/icons';
import type { NewsIntent } from '../news/newsUtils';
import {
  NEWS_DAY_OPTIONS,
  NEWS_DEFAULT_DAYS,
  NEWS_LIST_LIMIT,
  NEWS_WIDE_DAYS,
  errorMessage,
  formatTime,
  placeLabel,
  regionalCropHits,
  sourcesSummary,
} from '../news/newsUtils';

interface NewsViewProps {
  /** Busca (e artigo) vindos de outra tela, ex.: o card da Recomendação de Safra. */
  intent?: NewsIntent | null;
  /** Região e cultura da análise mais recente: é a busca ao abrir pela sidebar. */
  lastAnalysis: NewsQuery | null;
  onGoToAnalysis: () => void;
}

const CROP_OPTIONS = Object.entries(CROP_DICTIONARY)
  .map(([id, info]) => ({ id, name: info.namePt }))
  .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));

export const NewsView: React.FC<NewsViewProps> = ({ intent, lastAnalysis, onGoToAnalysis }) => {
  const initialQuery = intent?.query ?? lastAnalysis;
  const preloaded = intent?.response;

  // Campos do formulário
  const [cityInput, setCityInput] = useState(initialQuery?.city ?? '');
  const [ufInput, setUfInput] = useState(initialQuery?.state ?? 'SP');
  const [daysInput, setDaysInput] = useState(initialQuery?.days ?? NEWS_DEFAULT_DAYS);
  const [cropInput, setCropInput] = useState(initialQuery?.crop ?? '');

  // Última busca executada e seu resultado
  const [query, setQuery] = useState<NewsQuery | null>(initialQuery);
  const [data, setData] = useState<NewsResponse | null>(preloaded ?? null);
  const [loading, setLoading] = useState(Boolean(initialQuery) && !preloaded);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(intent?.articleId ?? null);

  const abortRef = useRef<AbortController | null>(null);
  const listScrollY = useRef(0);

  // Busca inicial (só quando há análise e a tela não recebeu uma resposta pronta).
  useEffect(() => {
    if (preloaded || !initialQuery) return;
    const controller = new AbortController();
    abortRef.current = controller;
    getHarvestNews({ ...initialQuery, limit: NEWS_LIST_LIMIT }, controller.signal)
      .then((response) => setData(response))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [initialQuery, preloaded]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // Abrir artigo rola para o topo; "Voltar" restaura a rolagem da lista.
  useLayoutEffect(() => {
    window.scrollTo({ top: selectedId ? 0 : listScrollY.current });
  }, [selectedId]);

  const runSearch = async (next: NewsQuery) => {
    if (!next.city) {
      setError('Selecione o município na lista.');
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setQuery(next);
    setLoading(true);
    setError(null);
    setSelectedId(null);
    listScrollY.current = 0;
    try {
      const response = await getHarvestNews({ ...next, limit: NEWS_LIST_LIMIT }, controller.signal);
      setData(response);
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      setError(errorMessage(err));
      setData(null);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  const formQuery = (overrides: Partial<NewsQuery> = {}): NewsQuery => ({
    city: cityInput,
    state: ufInput,
    days: daysInput,
    crop: cropInput || undefined,
    ...overrides,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(formQuery());
  };

  const handlePickCity = (name: string, uf: string) => {
    setCityInput(name);
    setUfInput(uf);
    runSearch(formQuery({ city: name, state: uf }));
  };

  const handleWiden = () => {
    if (!query) return;
    setDaysInput(NEWS_WIDE_DAYS);
    runSearch({ ...query, days: NEWS_WIDE_DAYS });
  };

  const openArticle = (article: NewsArticle) => {
    listScrollY.current = window.scrollY;
    setSelectedId(article.id);
  };

  const selected = data?.articles.find((a) => a.id === selectedId) ?? null;

  if (selected && data) {
    return (
      <ArticleView
        article={selected}
        location={data.location}
        crop={data.crop}
        onBack={() => setSelectedId(null)}
      />
    );
  }

  const shownDays = query?.days ?? NEWS_DEFAULT_DAYS;
  const sources = data ? sourcesSummary(data.sources) : null;
  const updatedAt = data ? formatTime(data.generated_at) : null;
  const cropHits = data ? regionalCropHits(data.articles) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Busca */}
      <div className="kp-card kp-card-compact space-y-3">
        <form onSubmit={handleSubmit} className="flex flex-wrap gap-3">
          <CityPicker
            city={cityInput}
            uf={ufInput}
            onChange={(nextCity, nextUf) => {
              setCityInput(nextCity);
              setUfInput(nextUf);
            }}
            className="flex-1 min-w-[16rem]"
          />

          <label className="w-40">
            <span className="sr-only">Período</span>
            <select
              value={daysInput}
              onChange={(e) => setDaysInput(Number(e.target.value))}
              className="kp-input"
            >
              {NEWS_DAY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  Últimos {d} dias
                </option>
              ))}
            </select>
          </label>

          <label className="w-48">
            <span className="sr-only">Cultura</span>
            <select value={cropInput} onChange={(e) => setCropInput(e.target.value)} className="kp-input">
              <option value="">Todas as culturas</option>
              {CROP_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  Cultura: {c.name}
                </option>
              ))}
            </select>
          </label>

          <Button
            type="submit"
            loading={loading}
            disabled={!cityInput}
            icon={<Search className="kp-icon" aria-hidden="true" />}
          >
            Buscar notícias
          </Button>
        </form>

        <div className="flex flex-wrap gap-1.5">
          {COMMON_CITIES.map((c) => (
            <button
              key={`${c.name}-${c.uf}`}
              type="button"
              onClick={() => handlePickCity(c.name, c.uf)}
              aria-pressed={cityInput === c.name && ufInput === c.uf}
              className="kp-filter"
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {/* Sem análise ainda: as notícias partem da região e da cultura indicada */}
      {!query && !loading && (
        <div className="kp-empty space-y-4">
          <Newspaper className="w-8 h-8 text-terra mx-auto" aria-hidden="true" />
          <p>
            Faça uma análise para ver as notícias da sua região e da cultura indicada, ou escolha um município acima.
          </p>
          <Button variant="secondary" onClick={onGoToAnalysis} icon={<CulturaIcon />}>
            Fazer análise
          </Button>
        </div>
      )}

      {/* Cabeçalho do resultado */}
      {data && !loading && (
        <div className="space-y-1">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="kp-card-title">
              {data.crop ? `Notícias de ${data.crop.name}` : 'Notícias de colheita'} · {data.location.city}
              {data.location.state ? `, ${data.location.state}` : ''}
            </h2>
            <span className="kp-meta">
              {data.total} {data.total === 1 ? 'resultado' : 'resultados'} · {shownDays} dias
            </span>
          </div>
          {data.crop && data.articles.length > 0 && (
            <p className={`text-sm ${cropHits > 0 ? 'text-broto' : 'text-ink-muted'}`}>
              {cropHits > 0
                ? `${cropHits === 1 ? '1 notícia' : `${cropHits} notícias`} sobre ${data.crop.name} na região.`
                : `Nada sobre ${data.crop.name} em ${placeLabel(data.location)} neste período. Veja o mais próximo:`}
            </p>
          )}
        </div>
      )}

      {error && <Notice title="Não foi possível buscar as notícias">{error}</Notice>}

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy="true" aria-label="Carregando notícias">
          <NewsCardSkeleton />
          <NewsCardSkeleton />
          <NewsCardSkeleton />
        </div>
      )}

      {!loading && data && data.articles.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.articles.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              location={data.location}
              crop={data.crop}
              onOpen={openArticle}
            />
          ))}
        </div>
      )}

      {!loading && data && data.articles.length === 0 && (
        <div className="kp-empty space-y-4">
          <Newspaper className="w-8 h-8 text-terra mx-auto" aria-hidden="true" />
          <p>
            Nenhuma notícia {data.crop ? `de ${data.crop.name}` : 'de colheita'} para {placeLabel(data.location)} nos últimos {shownDays} dias.
          </p>
          {shownDays < NEWS_WIDE_DAYS && (
            <Button variant="secondary" onClick={handleWiden} icon={<CalendarDays className="kp-icon" aria-hidden="true" />}>
              Ampliar para {NEWS_WIDE_DAYS} dias
            </Button>
          )}
        </div>
      )}

      {!loading && sources && (
        <p className={`text-[13px] leading-[18px] ${sources.partial ? 'text-terra' : 'text-ink-muted'}`}>
          Fontes: {sources.text}
          {updatedAt && <span className="text-ink-muted"> · coletado às {updatedAt}</span>}
        </p>
      )}
    </div>
  );
};
