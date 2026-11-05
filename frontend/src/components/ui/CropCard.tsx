import React from 'react';
import { Loader2 } from 'lucide-react';
import type { PrevisionOutput } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { formatNumber, toScore } from '../../utils/format';
import { CulturaIcon } from './icons';
import { ConfidenceBadge } from './ConfidenceBadge';

interface CropCardProps {
  result: PrevisionOutput;
  /** Município da análise, junto da posição no topo do cartão. */
  place?: string;
  /** Um novo cálculo está em andamento. */
  busy?: boolean;
  /** De onde vêm os fatores, como a janela das médias de clima. */
  factorsNote?: string;
}

/** O resultado do KiPlanto. É o único cartão com sombra: é o que a pessoa veio buscar. */
export const CropCard: React.FC<CropCardProps> = ({ result, place, busy = false, factorsNote }) => {
  const info = CROP_DICTIONARY[result.crop_recommendation.toLowerCase()];
  const score = result.confidence != null ? toScore(result.confidence) : null;
  const { features } = result;

  const factors = features
    ? [
        { name: 'Nitrogênio (N)', value: features.N, unit: 'mg/kg' },
        { name: 'Fósforo (P)', value: features.P, unit: 'mg/kg' },
        { name: 'Potássio (K)', value: features.K, unit: 'mg/kg' },
        { name: 'Temperatura média', value: features.temperature, unit: '°C' },
        { name: 'Umidade média', value: features.humidity, unit: '%' },
        { name: 'Chuva média mensal', value: features.rainfall, unit: 'mm/mês' },
      ]
    : [];

  const alternatives = (result.top_recommendations ?? [])
    .filter((rec) => rec.crop !== result.crop_recommendation)
    .map((rec) => ({
      crop: rec.crop,
      name: CROP_DICTIONARY[rec.crop.toLowerCase()]?.namePt ?? rec.crop,
      score: toScore(rec.probability),
    }))
    .filter((rec) => rec.score > 0);

  return (
    <article className="kp-crop">
      <div className="kp-crop-top">
        <span className="kp-crop-rank">1ª recomendação{place ? ` · ${place}` : ''}</span>
        {busy ? (
          <span className="inline-flex items-center gap-1 text-sm text-ink-muted" role="status">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            Calculando
          </span>
        ) : (
          score != null && <ConfidenceBadge score={score} />
        )}
      </div>

      <div className="space-y-2">
        <h2 className="kp-crop-name">
          <CulturaIcon className="kp-icon" />
          {info?.namePt ?? result.crop_recommendation}
        </h2>
        {info && <p className="text-sm text-ink-muted">{info.description}</p>}
      </div>

      {score != null && (
        <div className="space-y-1">
          <div className="kp-score">
            <div className="kp-score-bar" aria-hidden="true">
              <span style={{ width: `${score}%` }} />
            </div>
            <span className="kp-score-num">
              <span className="sr-only">Pontuação: </span>
              {score}
            </span>
          </div>
          <p className="text-[13px] leading-[18px] text-ink-muted">Pontuação: confiança do modelo nesta cultura, de 0 a 100. Alta a partir de 70, média a partir de 40.</p>
        </div>
      )}

      {factors.length > 0 && (
        <div className="space-y-2">
          <ul className="kp-factors">
            {factors.map((factor) => (
              <li key={factor.name}>
                <span>{factor.name}</span>
                <span className="v">{formatNumber(factor.value)}</span>
                <span className="r">{factor.unit}</span>
              </li>
            ))}
          </ul>
          {factorsNote && <p className="text-[13px] leading-[18px] text-ink-muted">{factorsNote}</p>}
        </div>
      )}

      {alternatives.length > 0 && (
        <div className="kp-alt">
          Outras opções do modelo:
          {alternatives.map((alternative) => (
            <ConfidenceBadge key={alternative.crop} score={alternative.score}>
              {alternative.name} {alternative.score}
            </ConfidenceBadge>
          ))}
        </div>
      )}
    </article>
  );
};
