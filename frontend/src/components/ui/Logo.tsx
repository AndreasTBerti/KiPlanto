import React from 'react';

/** Assinatura horizontal. O tema decide a versão: colorida no claro, reverse no escuro. */
export const Logo: React.FC<{ className?: string }> = ({ className = 'h-8 w-auto' }) => (
  <>
    <img src="/brand/kiplanto-logo.svg" alt="KiPlanto" className={`kp-logo-color ${className}`} />
    <img src="/brand/kiplanto-logo-reverse.svg" alt="KiPlanto" className={`kp-logo-reverse ${className}`} />
  </>
);
