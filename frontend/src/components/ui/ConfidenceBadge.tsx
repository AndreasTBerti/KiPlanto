import React from 'react';
import { CONFIDENCE_LABELS, confidenceLevel } from '../../utils/format';

interface ConfidenceBadgeProps {
  /** Pontuação inteira de 0 a 100: a confiança do modelo na cultura. */
  score: number;
  /** Texto no lugar do nível, como "Milho 74". O nível continua no title. */
  children?: React.ReactNode;
}

/** Três níveis, sempre com a palavra escrita: a cor nunca é o único sinal. */
export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score, children }) => {
  const level = confidenceLevel(score);
  return (
    <span className={`kp-badge kp-badge-${level}`} title={CONFIDENCE_LABELS[level]}>
      {children ?? CONFIDENCE_LABELS[level]}
    </span>
  );
};
