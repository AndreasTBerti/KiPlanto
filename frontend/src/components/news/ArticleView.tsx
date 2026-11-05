import React, { useState } from 'react';
import { ArrowLeft, ExternalLink, Info } from 'lucide-react';
import type { NewsArticle, NewsCrop, NewsLocation } from '../../types/api';
import { formatLongDate, locationBadge, relevanceReasons } from './newsUtils';

/** Capa com crédito. Sem imagem, ou se ela falhar ao carregar, o bloco inteiro some. */
const ArticleCover: React.FC<{ src?: string | null; credit: string }> = ({ src, credit }) => {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return null;
  return (
    <figure className="space-y-2">
      <img
        src={src}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="w-full max-h-[28rem] object-cover rounded-xl border border-slate-800 bg-slate-900"
      />
      <figcaption className="text-xs text-slate-500">Imagem: {credit}</figcaption>
    </figure>
  );
};

interface ArticleViewProps {
  article: NewsArticle;
  location: NewsLocation;
  crop?: NewsCrop | null;
  onBack: () => void;
}

/** Leitura em formato de artigo, só com o que o veículo publica no feed (SPEC §6.3, §8). */
export const ArticleView: React.FC<ArticleViewProps> = ({ article, location, crop, onBack }) => {
  const longDate = formatLongDate(article.published_at);
  const kicker = [article.source_name, location.state].filter(Boolean);
  const reasons = relevanceReasons(article, location, crop);

  return (
    <article className="max-w-3xl mx-auto space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-amber-300 transition-colors cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Voltar às notícias</span>
      </button>

      <header className="space-y-4 pb-6 border-b-2 border-slate-800">
        <div className="flex items-start justify-between gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-400">
            {kicker.join(' · ')}
            {longDate && (
              <>
                {' · '}
                <time dateTime={article.published_at ?? undefined}>{longDate}</time>
              </>
            )}
          </p>
          <span className="shrink-0 px-2 py-0.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-xs font-semibold text-amber-300">
            {locationBadge(article, location)}
          </span>
        </div>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight tracking-tight text-white">{article.title}</h1>
      </header>

      <ArticleCover src={article.image_url} credit={article.source_name} />

      {article.summary ? (
        <p className="text-lg leading-relaxed text-slate-200">{article.summary}</p>
      ) : (
        <p className="text-sm italic text-slate-500">Resumo indisponível nesta fonte.</p>
      )}

      <aside className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-1.5">
        <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-300">
          <Info className="w-3.5 h-3.5" />
          Por que você está vendo isto
        </h2>
        <p className="text-sm text-slate-300">{reasons.join(' · ')}</p>
        <p className="text-xs text-slate-500">Pontuação de relevância: {article.relevance_score}</p>
      </aside>

      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2.5 rounded-lg text-sm transition-colors"
      >
        <span>Ler matéria completa em {article.source_name}</span>
        <ExternalLink className="w-4 h-4" aria-hidden="true" />
        <span className="sr-only">(abre em nova aba)</span>
      </a>

      <p className="pt-4 border-t border-slate-800 text-xs leading-relaxed text-slate-500">
        Conteúdo de terceiros. O KiPlanto exibe apenas título e resumo publicados no feed do veículo; todos os
        direitos pertencem a ele.
      </p>
    </article>
  );
};
