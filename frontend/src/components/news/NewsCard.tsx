import React from 'react';
import { Newspaper } from 'lucide-react';
import type { NewsArticle, NewsCrop, NewsLocation } from '../../types/api';
import { NewsImage } from './NewsImage';
import { formatRelativeDate, locationBadge } from './newsUtils';

interface NewsCardProps {
  article: NewsArticle;
  location: NewsLocation;
  crop?: NewsCrop | null;
  onOpen: (article: NewsArticle) => void;
}

export const NewsCard: React.FC<NewsCardProps> = ({ article, location, crop, onOpen }) => {
  const when = formatRelativeDate(article.published_at);
  const cropTerms = new Set(crop?.terms ?? []);
  const keywords = article.matched_keywords.filter((k) => !cropTerms.has(k)).slice(0, 3);

  return (
    // O botão do título cobre o card inteiro (after:inset-0): todo o card é clicável
    // e o nome acessível do botão é só a manchete.
    <article className="kp-news-card group relative flex flex-col overflow-hidden bg-surface-raised border border-line rounded-lg">
      <div className="aspect-video bg-surface-sunken border-b border-line">
        <NewsImage
          src={article.image_url}
          alt=""
          className="w-full h-full object-cover"
          fallback={
            <div className="w-full h-full flex items-center justify-center text-line-strong">
              <Newspaper className="w-10 h-10" aria-hidden="true" />
            </div>
          }
        />
      </div>

      <div className="flex flex-col flex-1 gap-2 p-4">
        <p className="kp-meta">
          {article.source_name}
          {when && (
            <>
              {' · '}
              <time dateTime={article.published_at ?? undefined}>{when}</time>
            </>
          )}
        </p>

        <h3 className="text-base font-semibold leading-snug text-ink line-clamp-2 group-hover:text-broto transition-colors">
          <button
            type="button"
            onClick={() => onOpen(article)}
            className="text-left cursor-pointer outline-none after:absolute after:inset-0"
          >
            {article.title}
          </button>
        </h3>

        {article.summary ? (
          <p className="text-sm text-ink-muted line-clamp-3">{article.summary}</p>
        ) : (
          <p className="text-sm italic text-ink-muted">Resumo indisponível nesta fonte</p>
        )}

        <div className="mt-auto pt-2 flex flex-wrap gap-1.5">
          <span className="kp-chip kp-chip-terra">
            {locationBadge(article, location)}
          </span>
          {article.crop_match && crop && (
            <span className="kp-chip kp-chip-broto">
              {crop.name}
            </span>
          )}
          {keywords.map((keyword) => (
            <span key={keyword} className="kp-chip font-medium">
              {keyword}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
};

export const NewsCardSkeleton: React.FC = () => (
  <div className="bg-surface-raised border border-line rounded-lg overflow-hidden animate-pulse" aria-hidden="true">
    <div className="aspect-video bg-surface-sunken" />
    <div className="p-4 space-y-3">
      <div className="h-2.5 w-1/3 bg-surface-sunken rounded" />
      <div className="h-3.5 w-11/12 bg-surface-sunken rounded" />
      <div className="h-3.5 w-2/3 bg-surface-sunken rounded" />
      <div className="h-2.5 w-full bg-surface-sunken rounded" />
      <div className="h-2.5 w-5/6 bg-surface-sunken rounded" />
    </div>
  </div>
);
