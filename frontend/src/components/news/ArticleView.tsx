import React, { useState } from 'react';
import { ArrowLeft, ExternalLink, Info } from 'lucide-react';
import type { NewsArticle, NewsCrop, NewsLocation } from '../../types/api';
import { Button } from '../ui/Button';
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
        className="w-full max-h-[28rem] object-cover rounded-lg border border-line bg-surface-sunken"
      />
      <figcaption className="text-[13px] leading-[18px] text-ink-muted">Imagem: {credit}</figcaption>
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
      <Button variant="secondary" size="sm" onClick={onBack} icon={<ArrowLeft className="w-4 h-4" aria-hidden="true" />}>
        Voltar às notícias
      </Button>

      <header className="space-y-4 pb-6 border-b border-line">
        <div className="flex items-start justify-between gap-3">
          <p className="kp-label">
            {kicker.join(' · ')}
            {longDate && (
              <>
                {' · '}
                <time dateTime={article.published_at ?? undefined}>{longDate}</time>
              </>
            )}
          </p>
          <span className="kp-chip kp-chip-terra shrink-0">
            {locationBadge(article, location)}
          </span>
        </div>
        <h1 className="font-display text-3xl md:text-[40px] md:leading-[44px] font-bold tracking-tight text-ink">{article.title}</h1>
      </header>

      <ArticleCover src={article.image_url} credit={article.source_name} />

      {article.summary ? (
        <p className="text-lg leading-relaxed text-ink">{article.summary}</p>
      ) : (
        <p className="text-sm italic text-ink-muted">Resumo indisponível nesta fonte.</p>
      )}

      <aside className="kp-card kp-card-compact space-y-1.5">
        <h2 className="kp-label flex items-center gap-1.5">
          <Info className="w-4 h-4 text-terra" aria-hidden="true" />
          Por que você está vendo isto
        </h2>
        <p className="text-sm text-ink">{reasons.join(' · ')}</p>
        <p className="text-[13px] leading-[18px] text-ink-muted">
          Pontuação de relevância: <span className="font-mono">{article.relevance_score}</span>
        </p>
      </aside>

      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="kp-btn kp-btn-primary"
      >
        <span>Ler matéria completa em {article.source_name}</span>
        <ExternalLink className="w-4 h-4" aria-hidden="true" />
        <span className="sr-only">(abre em nova aba)</span>
      </a>

      <p className="pt-4 border-t border-line text-[13px] leading-[18px] text-ink-muted">
        Conteúdo de terceiros. O KiPlanto exibe apenas título e resumo publicados no feed do veículo; todos os
        direitos pertencem a ele.
      </p>
    </article>
  );
};
