import React from 'react';
import { Menu } from 'lucide-react';
import type { NavTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavTab;
  onOpenMobileMenu: () => void;
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
    </header>
  );
};
