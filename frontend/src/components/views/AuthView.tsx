import React, { useState } from 'react';
import type { AuthUser } from '../../types/api';
import { login, register } from '../../services/auth';
import { Button } from '../ui/Button';
import { DayNightCoverArt } from '../ui/CoverArt';
import { Logo } from '../ui/Logo';
import { Notice } from '../ui/Notice';
import { ThemeToggle } from '../ui/ThemeToggle';

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
    <main className="min-h-screen grid lg:grid-cols-2">
      {/* Capa da marca */}
      <section className="hidden lg:flex flex-col sticky top-0 h-screen bg-surface-raised border-r border-line overflow-hidden">
        <div className="p-12 pb-8 space-y-6">
          <Logo className="h-10 w-auto" />
          <p className="display-xl text-ink max-w-lg">Dados do solo, a cultura certa.</p>
          <p className="max-w-md text-ink-muted">
            Informe as condições do talhão e veja a melhor aposta para plantar, com a pontuação e os fatores que levaram à escolha.
          </p>
        </div>
        <DayNightCoverArt className="block flex-1 min-h-0 w-full overflow-visible" />
      </section>

      {/* Formulário */}
      <div className="relative flex items-center justify-center p-6">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden space-y-3">
            <Logo className="h-9 w-auto" />
            <p className="text-sm text-ink-muted">Dados do solo, a cultura certa.</p>
          </div>

          <h1 className="title text-ink">{isRegister ? 'Crie sua conta' : 'Entre na sua conta'}</h1>

          <div className="kp-segment" role="group" aria-label="Entrar ou criar conta">
            {MODES.map(({ id, label }) => (
              <button key={id} type="button" onClick={() => selectMode(id)} aria-pressed={mode === id}>
                {label}
              </button>
            ))}
          </div>

          {notice && !error && <Notice tone="warn">{notice}</Notice>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div className="kp-field">
                <label htmlFor="auth-name" className="kp-field-label">Nome</label>
                <input
                  id="auth-name"
                  type="text"
                  autoComplete="name"
                  required
                  minLength={2}
                  maxLength={80}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="kp-input"
                />
              </div>
            )}

            <div className="kp-field">
              <label htmlFor="auth-email" className="kp-field-label">E-mail</label>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="kp-input"
              />
            </div>

            <div className="kp-field">
              <label htmlFor="auth-password" className="kp-field-label">Senha</label>
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
                className="kp-input"
              />
              {isRegister && (
                <p id="auth-password-hint" className="kp-field-help">Pelo menos 8 caracteres.</p>
              )}
            </div>

            {error && <Notice>{error}</Notice>}

            <Button type="submit" loading={submitting} className="w-full">
              {isRegister ? 'Criar conta' : 'Entrar'}
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
};
