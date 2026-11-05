import React from 'react';
import { Ban, Minus, Newspaper, Scale, TrendingDown, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ClassifiedArticle, CrossCandidate, CrossReport, OutlookSentiment } from '../../types/api';
import { toScore } from '../../utils/format';

/** Rótulo sempre escrito: a cor nunca é o único sinal do sentimento. */
const OUTLOOK_BADGE: Record<OutlookSentiment, { label: string; icon: LucideIcon; className: string }> = {
  positive: { label: 'Favorável', icon: TrendingUp, className: 'kp-chip-broto' },
  negative: { label: 'Desfavorável', icon: TrendingDown, className: 'kp-chip-alerta' },
  mixed: { label: 'Dividida', icon: Scale, className: 'kp-chip-sol' },
  neutral: { label: 'Sem sinal claro', icon: Minus, className: '' },
  no_news: { label: 'Sem notícias', icon: Newspaper, className: '' },
  unavailable: { label: 'Indisponível', icon: Ban, className: '' },
};

const MAX_HEADLINES = 2;

/** As manchetes que sustentam a leitura: as do mesmo sentido e do mesmo escopo vêm primeiro. */
function supportingArticles(candidate: CrossCandidate): ClassifiedArticle[] {
  const { sentiment, scope, articles } = candidate.outlook;
  const inScope = articles.filter((a) => a.regional === (scope === 'region'));
  const matching = inScope.filter((a) => a.sentiment === sentiment);
  return (matching.length > 0 ? matching : inScope).slice(0, MAX_HEADLINES);
}

interface ReportCandidateProps {
  candidate: CrossCandidate;
  /** O 1º lugar do modelo: nome maior, fundo de destaque e barra de pontuação. */
  featured?: boolean;
  onOpenArticle: (candidate: CrossCandidate, articleId: string) => void;
}

const ReportCandidate: React.FC<ReportCandidateProps> = ({ candidate, featured = false, onOpenArticle }) => {
  const badge = OUTLOOK_BADGE[candidate.outlook.sentiment];
  const Icon = badge.icon;
  const score = toScore(candidate.probability);

  return (
    <li className={`kp-report-item ${featured ? 'kp-report-first' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="kp-label">{candidate.model_rank}º lugar</span>
        <span className={`kp-chip ${badge.className}`}>
          <Icon className="w-3.5 h-3.5" aria-hidden="true" />
          {badge.label}
        </span>
      </div>

      {featured ? (
        <>
          <p className="title text-ink">{candidate.name}</p>
          <div className="kp-score">
            <div className="kp-score-bar" aria-hidden="true">
              <span style={{ width: `${score}%` }} />
            </div>
            <span className="kp-score-num">
              <span className="sr-only">Pontuação: </span>
              {score}
            </span>
          </div>
        </>
      ) : (
        <p className="flex items-baseline justify-between gap-2">
          <span className="font-semibold text-lg text-ink">{candidate.name}</span>
          <span className="kp-data text-ink-muted">
            <span className="sr-only">Pontuação: </span>
            {score}
          </span>
        </p>
      )}

      <p className="text-sm text-ink">{candidate.outlook.text}</p>

      {supportingArticles(candidate).map((article) => (
        <button
          key={article.article_id}
          type="button"
          onClick={() => onOpenArticle(candidate, article.article_id)}
          className="block w-full text-left text-[13px] leading-[18px] text-ink-muted underline underline-offset-2 hover:text-broto-strong cursor-pointer"
        >
          {article.title}
        </button>
      ))}
    </li>
  );
};

interface CrossReportPanelProps {
  report: CrossReport;
  candidates: CrossCandidate[];
  onOpenArticle: (candidate: CrossCandidate, articleId: string) => void;
}

/** Report: pódio das culturas na ordem do modelo, com a leitura das notícias e a conclusão que junta as duas. */
export const CrossReportPanel: React.FC<CrossReportPanelProps> = ({ report, candidates, onOpenArticle }) => {
  const [first, ...others] = [...candidates].sort((a, b) => a.model_rank - b.model_rank);

  return (
    <div className="space-y-3">
      <h3 className="kp-label">Report: modelo e notícias</h3>

      <ol className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {first && <ReportCandidate candidate={first} featured onOpenArticle={onOpenArticle} />}
        {others.map((candidate) => (
          <ReportCandidate key={candidate.crop} candidate={candidate} onOpenArticle={onOpenArticle} />
        ))}
      </ol>

      <p className="text-sm font-semibold text-ink">{report.conclusion}</p>
      <p className="text-[13px] leading-[18px] text-ink-muted">{report.caveat}</p>
    </div>
  );
};
