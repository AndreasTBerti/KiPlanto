import React, { useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { getTheme, setTheme } from '../../services/theme';

export const ThemeToggle: React.FC = () => {
  const [theme, setThemeState] = useState(getTheme);
  const next = theme === 'dark' ? 'light' : 'dark';
  const label = next === 'dark' ? 'Usar tema escuro' : 'Usar tema claro';

  return (
    <button
      type="button"
      className="kp-icon-btn"
      aria-label={label}
      title={label}
      onClick={() => {
        setTheme(next);
        setThemeState(next);
      }}
    >
      {next === 'dark' ? <Moon className="kp-icon" aria-hidden="true" /> : <Sun className="kp-icon" aria-hidden="true" />}
    </button>
  );
};
