import React, { useState } from 'react';
import { Loader2, Sprout } from 'lucide-react';
import type { AuthUser } from '../../types/api';
import { login, register } from '../../services/auth';

type Mode = 'login' | 'register';

interface AuthViewProps {
  /** Aviso vindo do App, como sessão expirada. */
  notice?: string | null;
  onAuthenticated: (user: AuthUser) => void;
}

const MODES: { id: Mode; label: string }[] = [
  { id: 'login', label: 'Entrar' },
  { id: 'register', label: 'Criar conta' },
];

const inputClass =
  'w-full px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 ' +
  'placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/60';

export const AuthView: React.FC<AuthViewProps> = ({ notice, onAuthenticated }) => {
  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === 'register';

  const selectMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = isRegister ? await register(name, email, password) : await login(email, password);
      onAuthenticated(user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Algo deu errado. Tente novamente.');
      setPassword('');
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex items-center justify-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <Sprout className="w-6 h-6 text-emerald-400" aria-hidden="true" />
          </div>
          <div>
            <p className="text-lg font-bold text-white leading-tight">KiPlanto</p>
            <p className="text-xs text-slate-400">Recomendação Agrícola</p>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 space-y-5">
          <div className="grid grid-cols-2 gap-1 p-1 rounded-lg bg-slate-950" role="group" aria-label="Entrar ou criar conta">
            {MODES.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => selectMode(id)}
                aria-pressed={mode === id}
                className={`py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                  mode === id ? 'bg-emerald-500/15 text-emerald-200' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {notice && !error && (
            <p className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200" role="status">
              {notice}
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div className="space-y-1.5">
                <label htmlFor="auth-name" className="block text-xs font-medium text-slate-300">Nome</label>
                <input
                  id="auth-name"
                  type="text"
                  autoComplete="name"
                  required
                  minLength={2}
                  maxLength={80}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputClass}
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="auth-email" className="block text-xs font-medium text-slate-300">E-mail</label>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="auth-password" className="block text-xs font-medium text-slate-300">Senha</label>
              <input
                id="auth-password"
                type="password"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                required
                minLength={isRegister ? 8 : undefined}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-describedby={isRegister ? 'auth-password-hint' : undefined}
                className={inputClass}
              />
              {isRegister && (
                <p id="auth-password-hint" className="text-[11px] text-slate-400">Pelo menos 8 caracteres.</p>
              )}
            </div>

            {error && (
              <p className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-200" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-500 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed transition-colors"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
              {isRegister ? 'Criar conta' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
};
