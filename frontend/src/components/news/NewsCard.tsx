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

const badgeBase = 'px-1.5 py-0.5 rounded-md border text-[10px] font-semibold';

export const NewsCard: React.FC<NewsCardProps> = ({ article, location, crop, onOpen }) => {
  const when = formatRelativeDate(article.published_at);
  const cropTerms = new Set(crop?.terms ?? []);
  const keywords = article.matched_keywords.filter((k) => !cropTerms.has(k)).slice(0, 3);

  return (
    // O botão do título cobre o card inteiro (after:inset-0): todo o card é clicável
    // e o nome acessível do botão é só a manchete.
    <article className="group relative flex flex-col overflow-hidden bg-slate-900/80 border border-slate-800 rounded-xl transition-colors hover:border-amber-500/40 focus-within:border-amber-500/60 focus-within:ring-2 focus-within:ring-amber-500/30">
      <div className="aspect-video bg-slate-950 border-b border-slate-800">
        <NewsImage
          src={article.image_url}
          alt=""
          className="w-full h-full object-cover"
          fallback={
            <div className="w-full h-full flex items-center justify-center text-slate-700">
              <Newspaper className="w-10 h-10" aria-hidden="true" />
            </div>
          }
        />
      </div>

      <div className="flex flex-col flex-1 gap-2 p-4">
        <p className="text-[11px] font-mono text-slate-400">
          {article.source_name}
          {when && (
            <>
              {' · '}
              <time dateTime={article.published_at ?? undefined}>{when}</time>
            </>
          )}
        </p>

        <h3 className="text-sm font-semibold leading-snug text-white line-clamp-2 group-hover:text-amber-200 transition-colors">
          <button
            type="button"
            onClick={() => onOpen(article)}
            className="text-left cursor-pointer focus:outline-hidden after:absolute after:inset-0"
          >
            {article.title}
          </button>
        </h3>

        {article.summary ? (
          <p className="text-xs leading-relaxed text-slate-400 line-clamp-3">{article.summary}</p>
        ) : (
          <p className="text-xs italic text-slate-500">Resumo indisponível nesta fonte</p>
        )}

        <div className="mt-auto pt-2 flex flex-wrap gap-1.5">
          <span className={`${badgeBase} bg-amber-500/10 text-amber-300 border-amber-500/30`}>
            {locationBadge(article, location)}
          </span>
          {article.crop_match && crop && (
            <span className={`${badgeBase} bg-emerald-500/10 text-emerald-300 border-emerald-500/30`}>
              {crop.name}
            </span>
          )}
          {keywords.map((keyword) => (
            <span key={keyword} className={`${badgeBase} bg-slate-950 text-slate-400 border-slate-800 font-medium`}>
              {keyword}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
};

export const NewsCardSkeleton: React.FC = () => (
  <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden animate-pulse" aria-hidden="true">
    <div className="aspect-video bg-slate-800/60" />
    <div className="p-4 space-y-3">
      <div className="h-2.5 w-1/3 bg-slate-800 rounded" />
      <div className="h-3.5 w-11/12 bg-slate-800 rounded" />
      <div className="h-3.5 w-2/3 bg-slate-800 rounded" />
      <div className="h-2.5 w-full bg-slate-800/70 rounded" />
      <div className="h-2.5 w-5/6 bg-slate-800/70 rounded" />
    </div>
  </div>
);
