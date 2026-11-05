import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'md' | 'sm';
  icon?: React.ReactNode;
  /** Troca o ícone por um indicador de carregamento e desabilita o botão. */
  loading?: boolean;
}

/** O primário aparece no máximo uma vez por tela. Rótulo começa com verbo, em caixa de frase. */
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  icon,
  loading = false,
  disabled,
  type = 'button',
  className = '',
  children,
  ...props
}) => (
  <button
    type={type}
    disabled={disabled || loading}
    className={`kp-btn kp-btn-${variant} ${size === 'sm' ? 'kp-btn-sm' : ''} ${className}`}
    {...props}
  >
    {loading ? <Loader2 className="kp-icon animate-spin" aria-hidden="true" /> : icon}
    {children}
  </button>
);
