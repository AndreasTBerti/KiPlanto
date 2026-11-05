import React, { useEffect, useRef, useState } from 'react';

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

const Seeds: React.FC = () => (
  <g className="fill-terra-soft">
    {SEED_ROWS.flatMap(({ y, xs }) => xs.map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="4" />))}
  </g>
);

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
    <Seeds />
  </svg>
);

/** Centro da roda de dia e noite, abaixo do horizonte. Sol e lua ficam em pontas opostas dela. */
const PIVOT = { x: 424, y: 252 };

/** Estrelas de quatro pontas: x, y e tamanho. As além de x = 480 só aparecem em painéis largos. */
const STARS = [
  { x: 392, y: 16, size: 7 },
  { x: 476, y: 18, size: 5 },
  { x: 516, y: 84, size: 8 },
  { x: 352, y: 124, size: 4 },
  { x: 496, y: 142, size: 5 },
  { x: 536, y: 30, size: 6 },
  { x: 214, y: 10, size: 5 },
  { x: 44, y: 62, size: 6 },
];

const starPath = ({ x, y, size }: { x: number; y: number; size: number }) =>
  `M${x} ${y - size} Q${x} ${y} ${x + size} ${y} Q${x} ${y} ${x} ${y + size} Q${x} ${y} ${x - size} ${y} Q${x} ${y} ${x} ${y - size} Z`;

const rotations = (...degrees: number[]): Keyframe[] => degrees.map((degree) => ({ transform: `rotate(${degree}deg)` }));

/** A troca de tema como um gesto só: a planta sente o vento, a onda corre pelo solo e o novo astro chega com um brilho. */
const playThemeChange = (svg: SVGSVGElement): Animation[] => {
  const played: Animation[] = [];
  const play = (selector: string, keyframes: Keyframe[], options: KeyframeAnimationOptions) => {
    const element = svg.querySelector(selector);
    if (element) played.push(element.animate(keyframes, options));
  };

  play('.kp-cover-stem', rotations(0, 1.6, -0.9, 0.35, 0), { duration: 950, easing: 'ease-out' });
  // A folha vem logo depois da haste e balança mais: é o peso na ponta do caule.
  play('.kp-cover-leaf-sway', rotations(0, -5.5, 3.4, -1.6, 0.6, 0), { duration: 1150, delay: 50, easing: 'ease-out' });
  play(
    '.kp-cover-halo',
    [
      { opacity: 0.55, transform: 'scale(1)' },
      { opacity: 0, transform: 'scale(1.75)' },
    ],
    { duration: 650, delay: 560, easing: 'ease-out' },
  );

  // A onda corre da direita para a esquerda, o caminho do astro por baixo da terra.
  svg.querySelectorAll<SVGCircleElement>('.kp-cover-seeds circle').forEach((seed) => {
    const x = Number(seed.getAttribute('cx'));
    if (x > 720) return;
    played.push(
      seed.animate(
        [
          { transform: 'translateY(0) scale(1)' },
          { transform: 'translateY(-6px) scale(1.4)' },
          { transform: 'translateY(0) scale(1)' },
        ],
        { duration: 380, delay: (720 - x) * 0.75, easing: 'ease-in-out' },
      ),
    );
  });

  return played;
};

/**
 * A capa da tela de entrada, viva: ao trocar o tema, sol e lua giram na mesma roda, sempre no mesmo
 * sentido, e a lua sobe passando atrás da folha. À noite a folha repousa um pouco mais baixa e o céu
 * ganha estrelas. O solo vem depois dos astros e funciona como horizonte. O movimento contínuo e as
 * transições ficam em components.css.
 */
export const DayNightCoverArt: React.FC<{ className?: string }> = ({ className }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [halfTurns, setHalfTurns] = useState(() => (document.documentElement.dataset.theme === 'dark' ? 1 : 0));

  useEffect(() => {
    const root = document.documentElement;
    let theme = root.dataset.theme;
    let played: Animation[] = [];
    let fadeTimer: number | undefined;

    const observer = new MutationObserver(() => {
      if (root.dataset.theme === theme) return;
      theme = root.dataset.theme;
      setHalfTurns((turns) => turns + 1);

      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !svgRef.current) return;
      played.forEach((animation) => animation.cancel());
      played = playThemeChange(svgRef.current);

      // As cores da tela acompanham o céu só durante a troca, sem deixar os controles lentos depois.
      root.classList.add('kp-theme-fading');
      window.clearTimeout(fadeTimer);
      fadeTimer = window.setTimeout(() => root.classList.remove('kp-theme-fading'), 550);
    });
    observer.observe(root, { attributes: true, attributeFilter: ['data-theme'] });

    return () => {
      observer.disconnect();
      played.forEach((animation) => animation.cancel());
      window.clearTimeout(fadeTimer);
      root.classList.remove('kp-theme-fading');
    };
  }, []);

  return (
    <svg ref={svgRef} viewBox="0 0 480 288" preserveAspectRatio="xMinYMax meet" className={className} aria-hidden="true">
      <g>
        {STARS.map((star, index) => (
          <g key={`${star.x}-${star.y}`} className="kp-cover-star" style={{ '--i': index } as React.CSSProperties}>
            <path d={starPath(star)} />
          </g>
        ))}
      </g>

      <circle className="kp-cover-halo" cx="424" cy="72" r="40" opacity="0" />

      <g className="kp-cover-wheel" style={{ transform: `rotate(${halfTurns * 180}deg)` }}>
        <circle className="fill-sol" cx="424" cy="72" r="40" />
        <g transform={`rotate(180 ${PIVOT.x} ${PIVOT.y})`}>
          <path className="kp-cover-moon" d="M438 34.5 A 40 40 0 1 0 438 109.5 A 40 40 0 0 1 438 34.5 Z" />
        </g>
      </g>

      <rect className="fill-terra" x="0" y="192" width={SOIL_WIDTH} height="96" />

      <g className="kp-cover-stem">
        <rect className="fill-broto-strong" x="88" y="40" width="32" height="184" rx="16" />
        {/* Três camadas com a mesma base: repouso de dia ou de noite, o balanço da troca e a brisa contínua. */}
        <g className="kp-cover-leaf-rest">
          <g className="kp-cover-leaf-sway">
            <g className="kp-cover-leaf-breeze">
              <path className="fill-broto" d="M120 168 A 200 200 0 0 1 344 24 A 200 200 0 0 1 120 168 Z" />
              <path className="stroke-surface-raised" d="M140 152 Q 240 100 326 40" strokeWidth="4" strokeLinecap="round" fill="none" />
            </g>
          </g>
        </g>
      </g>

      <g className="kp-cover-seeds">
        <Seeds />
      </g>
    </svg>
  );
};
