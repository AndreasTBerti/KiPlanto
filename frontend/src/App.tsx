import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import type { NavTab } from './components/Sidebar';
import { Header } from './components/Header';
import { AuthView } from './components/views/AuthView';
import { PredictionView } from './components/views/PredictionView';
import { DirectSimulationView } from './components/views/DirectSimulationView';
import { ClimateView } from './components/views/ClimateView';
import { CropsCatalogView } from './components/views/CropsCatalogView';
import { HistoryView } from './components/views/HistoryView';
import { NewsView } from './components/views/NewsView';
import { lastAnalysisQuery } from './components/news/newsUtils';
import type { NewsIntent } from './components/news/newsUtils';
import type { AuthUser, PredictionHistoryItem } from './types/api';
import { setUnauthorizedHandler } from './services/api';
import { fetchCurrentUser, logout } from './services/auth';
import { clearHistory, HISTORY_LIMIT, loadHistory, saveHistory } from './services/history';
import { getToken } from './services/session';

const Workspace: React.FC<{ user: AuthUser; onLogout: () => void }> = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState<NavTab>('prediction');
  const [isOpenMobile, setIsOpenMobile] = useState(false);

  // Busca/artigo que a aba de notícias deve abrir (vinda do card da Recomendação).
  // O id força a remontagem do NewsView a cada novo pedido.
  const [newsIntent, setNewsIntent] = useState<{ id: number; intent: NewsIntent } | null>(null);

  const handleSelectTab = useCallback((tab: NavTab) => {
    setNewsIntent(null); // pela sidebar, a aba de notícias abre com a última análise
    setActiveTab(tab);
  }, []);

  const handleOpenNews = useCallback((intent: NewsIntent) => {
    setNewsIntent({ id: Date.now(), intent });
    setActiveTab('news');
  }, []);

  // Histórico de cada conta, persistido no localStorage (com migração de registros antigos).
  const [history, setHistory] = useState<PredictionHistoryItem[]>(() => loadHistory(user.id));
  const lastAnalysis = useMemo(() => lastAnalysisQuery(history), [history]);

  // useCallback: as views usam esses handlers em dependências de efeitos.
  const handleSaveHistory = useCallback((item: PredictionHistoryItem) => {
    setHistory((prev) => {
      const updated = [item, ...prev].slice(0, HISTORY_LIMIT);
      saveHistory(user.id, updated);
      return updated;
    });
  }, [user.id]);

  const handleClearHistory = useCallback(() => {
    setHistory([]);
    clearHistory(user.id);
  }, [user.id]);

  const handleDeleteHistoryItem = useCallback((id: string) => {
    setHistory((prev) => {
      const updated = prev.filter((item) => item.id !== id);
      saveHistory(user.id, updated);
      return updated;
    });
  }, [user.id]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        isOpenMobile={isOpenMobile}
        onToggleMobile={() => setIsOpenMobile(!isOpenMobile)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex-1 flex flex-col min-w-0">
        <Header
          activeTab={activeTab}
          onOpenMobileMenu={() => setIsOpenMobile(true)}
          userName={user.name}
          onLogout={onLogout}
        />

        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          {activeTab === 'prediction' && (
            <PredictionView onSaveHistory={handleSaveHistory} onOpenNews={handleOpenNews} />
          )}

          {activeTab === 'simulation' && (
            <DirectSimulationView onSaveHistory={handleSaveHistory} />
          )}

          {activeTab === 'climate' && <ClimateView />}

          {activeTab === 'news' && (
            <NewsView
              key={newsIntent?.id ?? 'default'}
              intent={newsIntent?.intent}
              lastAnalysis={lastAnalysis}
              onGoToAnalysis={() => handleSelectTab('prediction')}
            />
          )}

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

export const App: React.FC = () => {
  const [user, setUser] = useState<AuthUser | null>(null);
  // Só há o que verificar se o navegador guardou uma sessão.
  const [checking, setChecking] = useState(() => getToken() !== null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setNotice('Sua sessão expirou. Entre novamente.');
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    if (!checking) return;
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setNotice('Não foi possível conectar ao servidor. Tente entrar novamente.'))
      .finally(() => setChecking(false));
  }, [checking]);

  const handleAuthenticated = useCallback((authenticated: AuthUser) => {
    setNotice(null);
    setUser(authenticated);
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    setNotice(null);
    void logout();
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" role="status" aria-label="Verificando a sessão">
        <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" aria-hidden="true" />
      </div>
    );
  }

  if (!user) {
    return <AuthView notice={notice} onAuthenticated={handleAuthenticated} />;
  }

  // key: outra conta começa do zero, sem herdar a tela nem o histórico da anterior.
  return <Workspace key={user.id} user={user} onLogout={handleLogout} />;
};

export default App;
