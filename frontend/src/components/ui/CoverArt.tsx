import React from 'react';

/** Até onde o solo se estende além da arte, para preencher painéis mais largos que ela. */
const SOIL_WIDTH = 1200;
const SEED_PITCH = 24;
const UNDER_STEM = [72, 96, 120];

const seedsFrom = (start: number) =>
  Array.from({ length: Math.ceil((SOIL_WIDTH - start) / SEED_PITCH) }, (_, index) => start + index * SEED_PITCH);

const SEED_ROWS = [
  { y: 224, xs: seedsFrom(24).filter((x) => !UNDER_STEM.includes(x)) },
  { y: 248, xs: seedsFrom(36) },
];

/**
 * Arte da capa do design system: o K-planta em escala de campo, nascendo do solo em direção ao sol.
 * Fica ancorada no canto inferior esquerdo. Com overflow-visible, o solo segue até a borda do painel.
 */
export const CoverArt: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 480 288" preserveAspectRatio="xMinYMax meet" className={className} aria-hidden="true">
    <rect className="fill-terra" x="0" y="192" width={SOIL_WIDTH} height="96" />
    <rect className="fill-broto-strong" x="88" y="40" width="32" height="184" rx="16" />
    <path className="fill-broto" d="M120 168 A 200 200 0 0 1 344 24 A 200 200 0 0 1 120 168 Z" />
    <path className="stroke-surface-raised" d="M140 152 Q 240 100 326 40" strokeWidth="4" strokeLinecap="round" fill="none" />
    <circle className="fill-sol" cx="424" cy="72" r="40" />
    <g className="fill-terra-soft">
      {SEED_ROWS.flatMap(({ y, xs }) => xs.map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="4" />))}
    </g>
  </svg>
);
