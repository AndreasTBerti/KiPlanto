import React from 'react';
import { LogOut, Menu } from 'lucide-react';
import type { NavTab } from './Sidebar';
import { Button } from './ui/Button';
import { ThemeToggle } from './ui/ThemeToggle';

interface HeaderProps {
  activeTab: NavTab;
  onOpenMobileMenu: () => void;
  userName: string;
  onLogout: () => void;
}

const TAB_TITLES: Record<NavTab, string> = {
  prediction: 'Recomendação de safra',
  simulation: 'Simulação direta',
  climate: 'Consulta climática',
  news: 'Notícias da colheita',
  catalog: 'Catálogo de culturas',
  history: 'Histórico de análises',
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onOpenMobileMenu,
  userName,
  onLogout,
}) => (
  <header className="h-16 bg-surface border-b border-line px-2 sm:px-4 md:px-8 flex items-center justify-between gap-2 sm:gap-3 sticky top-0 z-30">
    <div className="flex items-center gap-2 min-w-0">
      <button onClick={onOpenMobileMenu} className="kp-icon-btn lg:hidden" aria-label="Abrir menu">
        <Menu className="kp-icon" aria-hidden="true" />
      </button>
      <h1 className="kp-page-title truncate">{TAB_TITLES[activeTab]}</h1>
    </div>
    <div className="flex items-center gap-2 shrink-0">
      <span className="hidden sm:block max-w-48 truncate text-sm text-ink-muted" title={userName}>
        {userName}
      </span>
      <ThemeToggle />
      <Button
        variant="secondary"
        size="sm"
        onClick={onLogout}
        aria-label="Sair"
        icon={<LogOut className="w-4 h-4" aria-hidden="true" />}
      >
        <span className="hidden sm:inline">Sair</span>
      </Button>
    </div>
  </header>
);
