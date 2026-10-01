import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import type { NavTab } from './components/Sidebar';
import { Header } from './components/Header';
import { PredictionView } from './components/views/PredictionView';
import { DirectSimulationView } from './components/views/DirectSimulationView';
import { ClimateView } from './components/views/ClimateView';
import { CropsCatalogView } from './components/views/CropsCatalogView';
import { HistoryView } from './components/views/HistoryView';
import type { PredictionHistoryItem } from './types/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('prediction');
  const [isOpenMobile, setIsOpenMobile] = useState(false);

  // History state persisted in localStorage
  const [history, setHistory] = useState<PredictionHistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('kiplanto_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const handleSaveHistory = (item: PredictionHistoryItem) => {
    setHistory((prev) => {
      const updated = [item, ...prev].slice(0, 50);
      try {
        localStorage.setItem('kiplanto_history', JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  const handleClearHistory = () => {
    setHistory([]);
    localStorage.removeItem('kiplanto_history');
  };

  const handleDeleteHistoryItem = (id: string) => {
    setHistory((prev) => {
      const updated = prev.filter((item) => item.id !== id);
      localStorage.setItem('kiplanto_history', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isOpenMobile={isOpenMobile}
        onToggleMobile={() => setIsOpenMobile(!isOpenMobile)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex-1 flex flex-col min-w-0">
        <Header
          activeTab={activeTab}
          onOpenMobileMenu={() => setIsOpenMobile(true)}
        />

        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          {activeTab === 'prediction' && (
            <PredictionView onSaveHistory={handleSaveHistory} />
          )}

          {activeTab === 'simulation' && (
            <DirectSimulationView onSaveHistory={handleSaveHistory} />
          )}

          {activeTab === 'climate' && <ClimateView />}

          {activeTab === 'catalog' && <CropsCatalogView />}

          {activeTab === 'history' && (
            <HistoryView
              history={history}
              onClearHistory={handleClearHistory}
              onDeleteItem={handleDeleteHistoryItem}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
