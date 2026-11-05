import React from 'react';

type IconProps = React.SVGProps<SVGSVGElement>;

/** Os sete ícones da marca: linha, 24 × 24, traço 1,75, pontas arredondadas, em currentColor. */
const BrandIcon: React.FC<IconProps> = ({ className = 'kp-icon', children, ...props }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.75"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    className={className}
    {...props}
  >
    {children}
  </svg>
);

export const CulturaIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M12 21v-9" />
    <path d="M12 12c0-4 3-7 7-7 0 4-3 7-7 7z" />
    <path d="M12 14c0-3-2.5-5.5-6-5.5 0 3 2.5 5.5 6 5.5z" />
  </BrandIcon>
);

export const PhIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z" />
    <path d="M9 14h2M9 17h4" />
  </BrandIcon>
);

export const UmidadeIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M7 15a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 1.5A3.5 3.5 0 0 1 17 15" />
    <path d="M8 18v2M12 17v3M16 18v2" />
  </BrandIcon>
);

export const TemperaturaIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M10 4a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z" />
    <path d="M12 10v6" />
  </BrandIcon>
);

export const SoloIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M3 9h18" />
    <path d="M3 14h18" />
    <path d="M3 19h18" />
    <circle cx="7" cy="16.5" r=".6" fill="currentColor" />
    <circle cx="15" cy="11.5" r=".6" fill="currentColor" />
    <path d="M12 9V5M12 5c0-1.5 1.5-2.5 3-2.5 0 1.5-1.5 2.5-3 2.5z" />
  </BrandIcon>
);

export const LuzIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
  </BrandIcon>
);

export const SensorIcon: React.FC<IconProps> = (props) => (
  <BrandIcon {...props}>
    <path d="M5 19c2-6 5-9 7-9s5 3 7 9" />
    <path d="M12 10V4" />
    <path d="M8.5 6.5a5 5 0 0 1 7 0" />
    <path d="M6 4a8.5 8.5 0 0 1 12 0" />
  </BrandIcon>
);
