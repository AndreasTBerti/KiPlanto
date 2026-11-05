import React from 'react';
import { formatNumber } from '../../utils/format';

const NEUTRAL_MIN = 6.5;
const NEUTRAL_MAX = 7.5;

/** Régua de pH de 0 a 14 com a faixa neutra destacada e um marcador na leitura atual. */
export const PhScale: React.FC<{ value: number }> = ({ value }) => {
  const reading = formatNumber(value, 1);
  const zone = value < NEUTRAL_MIN ? 'ácido' : value > NEUTRAL_MAX ? 'alcalino' : 'neutro';

  return (
    <div className="kp-ph" role="img" aria-label={`pH ${reading}, ${zone}`}>
      <div className="kp-ph-track">
        <span className="kp-ph-acid" />
        <span className="kp-ph-ideal" />
        <span className="kp-ph-alk" />
        <i className="kp-ph-marker" style={{ left: `${(value / 14) * 100}%` }} />
      </div>
      <div className="kp-ph-scale">
        <span>0</span>
        <span>3,5</span>
        <span>7</span>
        <span>10,5</span>
        <span>14</span>
      </div>
      <div className="kp-ph-legend">
        <span>
          <i style={{ background: 'var(--terra)' }} />
          Ácido
        </span>
        <span>
          <i style={{ background: 'var(--broto)' }} />
          Neutro {formatNumber(NEUTRAL_MIN)}–{formatNumber(NEUTRAL_MAX)}
        </span>
        <span>
          <i style={{ background: 'var(--sol)' }} />
          Alcalino
        </span>
      </div>
    </div>
  );
};
