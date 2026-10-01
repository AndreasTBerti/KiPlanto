import React from 'react';
import {
  Sprout,
  SlidersHorizontal,
  CloudSun,
  BookOpen,
  History,
  X
} from 'lucide-react';

export type NavTab = 'prediction' | 'simulation' | 'climate' | 'catalog' | 'history';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isOpenMobile: boolean;
  onToggleMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile,
  onToggleMobile,
}) => {
  const navItems = [
    { id: 'prediction' as NavTab, label: 'Recomendação de Safra', icon: Sprout },
    { id: 'simulation' as NavTab, label: 'Simulação Direta', icon: SlidersHorizontal },
    { id: 'climate' as NavTab, label: 'Consulta Climática', icon: CloudSun },
    { id: 'catalog' as NavTab, label: 'Catálogo de Culturas', icon: BookOpen },
    { id: 'history' as NavTab, label: 'Histórico de Análises', icon: History },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          onClick={onToggleMobile}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Sprout className="w-5 h-5" />
            </div>
            <div>
              <span className="text-base font-semibold tracking-tight text-white block">KiPlanto</span>
              <span className="text-xs text-slate-400 font-mono">Recomendação Agrícola</span>
            </div>
          </div>
          <button
            onClick={onToggleMobile}
            className="lg:hidden text-slate-400 hover:text-white p-1 rounded-md"
            aria-label="Fechar menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  if (isOpenMobile) onToggleMobile();
                }}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white border border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
};
