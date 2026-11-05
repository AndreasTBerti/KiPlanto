const THEME_KEY = 'kiplanto_theme';

export type Theme = 'light' | 'dark';

/** O tema salvo já foi aplicado por um script no index.html, antes da primeira pintura. */
export function getTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

export function setTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Sem localStorage o tema vale só até recarregar a página.
  }
}
