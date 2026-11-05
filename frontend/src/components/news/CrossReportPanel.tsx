import React from 'react';
import { Ban, ClipboardList, Minus, Newspaper, Scale, TrendingDown, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ClassifiedArticle, CrossCandidate, CrossReport, OutlookSentiment } from '../../types/api';

/** Rótulo sempre escrito: a cor nunca é o único sinal do sentimento. */
const OUTLOOK_BADGE: Record<OutlookSentiment, { label: string; icon: LucideIcon; className: string }> = {
  positive: { label: 'Favorável', icon: TrendingUp, className: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' },
  negative: { label: 'Desfavorável', icon: TrendingDown, className: 'bg-rose-500/10 text-rose-300 border-rose-500/30' },
  mixed: { label: 'Dividida', icon: Scale, className: 'bg-amber-500/10 text-amber-300 border-amber-500/30' },
  neutral: { label: 'Sem sinal claro', icon: Minus, className: 'bg-slate-800 text-slate-300 border-slate-700' },
  no_news: { label: 'Sem notícias', icon: Newspaper, className: 'bg-slate-800 text-slate-400 border-slate-700' },
  unavailable: { label: 'Indisponível', icon: Ban, className: 'bg-slate-800 text-slate-400 border-slate-700' },
};

const MAX_HEADLINES = 2;

/** As manchetes que sustentam a leitura: as do mesmo sentido e do mesmo escopo vêm primeiro. */
function supportingArticles(candidate: CrossCandidate): ClassifiedArticle[] {
  const { sentiment, scope, articles } = candidate.outlook;
  const inScope = articles.filter((a) => a.regional === (scope === 'region'));
  const matching = inScope.filter((a) => a.sentiment === sentiment);
  return (matching.length > 0 ? matching : inScope).slice(0, MAX_HEADLINES);
}

interface CrossReportPanelProps {
  report: CrossReport;
  candidates: CrossCandidate[];
  onOpenArticle: (candidate: CrossCandidate, articleId: string) => void;
}

/** Report: cada cultura na ordem do modelo, com a leitura das notícias e a conclusão que junta as duas. */
export const CrossReportPanel: React.FC<CrossReportPanelProps> = ({ report, candidates, onOpenArticle }) => {
  const byModel = [...candidates].sort((a, b) => a.model_rank - b.model_rank);

  return (
    <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-bold text-white">
        <ClipboardList className="w-4 h-4 text-amber-400" aria-hidden="true" />
        Report: modelo e notícias
      </h3>

      <ol className="space-y-3">
        {byModel.map((candidate) => {
          const badge = OUTLOOK_BADGE[candidate.outlook.sentiment];
          const Icon = badge.icon;
          return (
            <li key={candidate.crop} className="space-y-1">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-mono text-xs text-slate-400">{candidate.model_rank}º</span>
                <span className="font-semibold text-slate-100">{candidate.name}</span>
                <span className="font-mono text-xs text-slate-400">{candidate.probability}%</span>
                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[10px] font-semibold ${badge.className}`}
                >
                  <Icon className="w-3 h-3" aria-hidden="true" />
                  {badge.label}
                </span>
              </div>
              <p className="text-xs leading-snug text-slate-300">{candidate.outlook.text}</p>
              {supportingArticles(candidate).map((article) => (
                <button
                  key={article.article_id}
                  type="button"
                  onClick={() => onOpenArticle(candidate, article.article_id)}
                  className="block w-full text-left text-xs leading-snug text-slate-400 underline decoration-slate-700 underline-offset-2 hover:text-amber-200 cursor-pointer"
                >
                  {article.title}
                </button>
              ))}
            </li>
          );
        })}
      </ol>

      <p className="pt-3 border-t border-slate-800 text-sm leading-snug font-medium text-slate-100">
        {report.conclusion}
      </p>
      <p className="text-[11px] leading-snug text-slate-400">{report.caveat}</p>
    </div>
  );
};
