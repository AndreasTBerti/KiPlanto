import React from 'react';
import { SlidersHorizontal, Newspaper, BookOpen, History, X } from 'lucide-react';
import { Logo } from './ui/Logo';
import { CulturaIcon, UmidadeIcon } from './ui/icons';

export type NavTab = 'prediction' | 'simulation' | 'climate' | 'news' | 'catalog' | 'history';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isOpenMobile: boolean;
  onToggleMobile: () => void;
}

const NAV_ITEMS: { id: NavTab; label: string; icon: React.ElementType }[] = [
  { id: 'prediction', label: 'Recomendação de safra', icon: CulturaIcon },
  { id: 'simulation', label: 'Simulação direta', icon: SlidersHorizontal },
  { id: 'climate', label: 'Consulta climática', icon: UmidadeIcon },
  { id: 'news', label: 'Notícias da colheita', icon: Newspaper },
  { id: 'catalog', label: 'Catálogo de culturas', icon: BookOpen },
  { id: 'history', label: 'Histórico de análises', icon: History },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile,
  onToggleMobile,
}) => (
  <>
    {/* Mobile Backdrop */}
    {isOpenMobile && (
      <div onClick={onToggleMobile} className="kp-backdrop fixed inset-0 z-40 lg:hidden" />
    )}

    {/* Sidebar Container */}
    <aside
      className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-surface-raised border-r border-line flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
        isOpenMobile ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <div className="h-16 flex items-center justify-between pl-5 pr-3 border-b border-line">
        <Logo className="h-8 w-auto" />
        <button onClick={onToggleMobile} className="kp-icon-btn lg:hidden" aria-label="Fechar menu">
          <X className="kp-icon" aria-hidden="true" />
        </button>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            aria-current={activeTab === id ? 'page' : undefined}
            onClick={() => {
              onSelectTab(id);
              if (isOpenMobile) onToggleMobile();
            }}
            className="kp-nav-item"
          >
            <Icon className="kp-icon" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </nav>

      <p className="px-5 py-4 border-t border-line text-[13px] leading-[18px] text-ink-muted">
        Dados do solo, a cultura certa.
      </p>
    </aside>
  </>
);
