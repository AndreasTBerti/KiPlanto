import React from 'react';
import { LogOut, Menu } from 'lucide-react';
import type { NavTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavTab;
  onOpenMobileMenu: () => void;
  userName: string;
  onLogout: () => void;
}

const TAB_TITLES: Record<NavTab, { title: string }> = {
  prediction: {
    title: 'Recomendação de Safra',
  },
  simulation: {
    title: 'Simulação Direta',
  },
  climate: {
    title: 'Consulta Climática',
  },
  news: {
    title: 'Notícias da Colheita',
  },
  catalog: {
    title: 'Catálogo de Culturas',
  },
  history: {
    title: 'Histórico de Análises',
  },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onOpenMobileMenu,
  userName,
  onLogout,
}) => {
  const current = TAB_TITLES[activeTab];

  return (
    <header className="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 cursor-pointer"
          aria-label="Abrir menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-base font-semibold text-white tracking-tight">{current.title}</h1>
      </div>
      <div className="flex items-center gap-3 min-w-0">
        <span className="hidden sm:block max-w-48 truncate text-sm text-slate-300" title={userName}>
          {userName}
        </span>
        <button
          type="button"
          onClick={onLogout}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:border-slate-700 cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
          Sair
        </button>
      </div>
    </header>
  );
};
