import React, { useState } from 'react';
import {
  Sparkles,
  CloudRain,
  Thermometer,
  Wind,
  Droplets,
  AlertCircle,
  CheckCircle2,
  Sliders,
  Info
} from 'lucide-react';
import type { PrevisionInput, PrevisionOutput, PredictionHistoryItem } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { predictCrop } from '../../services/api';
import { COMMON_CITIES } from '../../constants/cities';
import { CityPicker } from '../CityPicker';
import { RegionalNewsCard } from '../news/RegionalNewsCard';
import type { NewsIntent } from '../news/newsUtils';

interface PredictionViewProps {
  onSaveHistory: (item: PredictionHistoryItem) => void;
  /** Abre a aba de notícias a partir do card de notícias da região. */
  onOpenNews: (intent: NewsIntent) => void;
}

export const PredictionView: React.FC<PredictionViewProps> = ({ onSaveHistory, onOpenNews }) => {
  const [city, setCity] = useState('Tupã');
  const [uf, setUf] = useState('SP');
  const [nRatio, setNRatio] = useState<number>(60);
  const [pRatio, setPRatio] = useState<number>(45);
  const [kRatio, setKRatio] = useState<number>(50);
  const [ph, setPh] = useState<number>(6.5);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PrevisionOutput | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!city) {
      setError('Selecione o município na lista.');
      return;
    }

    setLoading(true);
    setError(null);

    const inputData: PrevisionInput = {
      city,
      state: uf,
      n_ratio: Number(nRatio),
      p_ratio: Number(pRatio),
      k_ratio: Number(kRatio),
      ph: Number(ph),
    };

    try {
      const response = await predictCrop(inputData);
      setResult(response);

      const historyItem: PredictionHistoryItem = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        city: response.city || inputData.city,
        uf: response.uf,
        inputs: {
          n: inputData.n_ratio,
          p: inputData.p_ratio,
          k: inputData.k_ratio,
          ph: inputData.ph,
        },
        result: response,
      };
      onSaveHistory(historyItem);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Falha ao processar a previsão.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const cropKey = result?.crop_recommendation?.toLowerCase() || '';
  const cropInfo = CROP_DICTIONARY[cropKey];
  const resolvedPlace = result
    ? `${result.city || city}${result.uf ? `/${result.uf}` : ''}`
    : '';

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input Form (5 cols) */}
        <div className="lg:col-span-5">
          <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
            {/* City + UF */}
            <div className="space-y-2">
              <span className="block text-xs font-semibold text-slate-300">Município</span>
              <CityPicker
                city={city}
                uf={uf}
                onChange={(nextCity, nextUf) => {
                  setCity(nextCity);
                  setUf(nextUf);
                }}
              />

              <div className="flex flex-wrap gap-1.5 pt-1">
                {COMMON_CITIES.map((c) => {
                  const isActive = city === c.name && uf === c.uf;
                  return (
                    <button
                      key={`${c.name}-${c.uf}`}
                      type="button"
                      onClick={() => {
                        setCity(c.name);
                        setUf(c.uf);
                      }}
                      title={`${c.name}/${c.uf}`}
                      className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors cursor-pointer ${
                        isActive
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {c.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Nutrients */}
            <div className="space-y-4 pt-2 border-t border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Nutrientes e pH</span>
                <Sliders className="w-3.5 h-3.5 text-slate-400" />
              </div>

              {/* N */}
              <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Nitrogênio (N)</span>
                  <span className="font-mono text-emerald-400 font-semibold">{nRatio} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="140"
                  step="1"
                  value={nRatio}
                  onChange={(e) => setNRatio(Number(e.target.value))}
                  aria-label="Nitrogênio (N) em mg/kg"
                  className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* P */}
              <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Fósforo (P)</span>
                  <span className="font-mono text-blue-400 font-semibold">{pRatio} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="145"
                  step="1"
                  value={pRatio}
                  onChange={(e) => setPRatio(Number(e.target.value))}
                  aria-label="Fósforo (P) em mg/kg"
                  className="w-full accent-blue-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* K */}
              <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Potássio (K)</span>
                  <span className="font-mono text-purple-400 font-semibold">{kRatio} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="205"
                  step="1"
                  value={kRatio}
                  onChange={(e) => setKRatio(Number(e.target.value))}
                  aria-label="Potássio (K) em mg/kg"
                  className="w-full accent-purple-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* pH */}
              <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">pH do Solo</span>
                  <span className="font-mono text-amber-400 font-semibold">{ph.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="3.5"
                  max="9.0"
                  step="0.1"
                  value={ph}
                  onChange={(e) => setPh(Number(e.target.value))}
                  aria-label="pH do solo"
                  aria-describedby="ph-note"
                  className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
                <p id="ph-note" className="text-[11px] text-slate-400 flex items-start gap-1.5 pt-0.5">
                  <Info className="w-3 h-3 mt-0.5 shrink-0" />
                  <span>Registrado no histórico, mas não usado pelo modelo atual (treinado sem pH).</span>
                </p>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Obter Recomendação</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Output / Prediction Results (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-start space-x-3">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Erro na Operação</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {result ? (
            <div className="space-y-4">
              {/* Notícias em destaque, cruzadas com o modelo (SPEC §6.4) */}
              {result.features && (
                <RegionalNewsCard
                  city={result.city || city}
                  uf={result.uf}
                  features={result.features}
                  onOpenNews={onOpenNews}
                />
              )}

              {/* Primary Output Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Recomendação · {resolvedPlace}
                    </span>
                  </div>
                  {result.confidence != null && (
                    <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                      {result.confidence}% Confiança
                    </span>
                  )}
                </div>

                <div className="py-5">
                  <span className="text-xs text-slate-400 font-medium">Cultura Indicada pelo Modelo</span>
                  <div className="flex items-baseline space-x-3 mt-1">
                    <h2 className="text-3xl font-extrabold text-white tracking-tight">
                      {cropInfo?.namePt || result.crop_recommendation}
                    </h2>
                    <span className="text-xs font-mono text-slate-400">({result.crop_recommendation})</span>
                  </div>

                  {cropInfo && (
                    <div className="mt-2 flex items-center space-x-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {cropInfo.category}
                      </span>
                      <p className="text-xs text-slate-400">{cropInfo.description}</p>
                    </div>
                  )}
                </div>

                {/* Top 3 Recommendation Bar Distribution */}
                {result.top_recommendations && result.top_recommendations.length > 0 && (
                  <div className="mt-2 pt-4 border-t border-slate-800 space-y-2">
                    <span className="text-xs font-medium text-slate-400 block">
                      Distribuição de Probabilidades
                    </span>
                    <div className="space-y-2">
                      {result.top_recommendations.map((rec) => {
                        const info = CROP_DICTIONARY[rec.crop.toLowerCase()];
                        return (
                          <div key={rec.crop} className="space-y-1">
                            <div className="flex justify-between text-xs">
                              <span className="text-slate-300 font-medium">
                                {info?.namePt || rec.crop}
                              </span>
                              <span className="font-mono text-slate-400">{rec.probability}%</span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-500 rounded-full"
                                style={{ width: `${rec.probability}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Values actually fed to the model */}
              {result.features && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-1">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Entradas do Modelo
                    </h3>
                    <span className="text-[11px] text-slate-400">valores usados na predição</span>
                  </div>
                  <dl className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                    {[
                      { label: 'Nitrogênio (N)', value: `${result.features.N} mg/kg` },
                      { label: 'Fósforo (P)', value: `${result.features.P} mg/kg` },
                      { label: 'Potássio (K)', value: `${result.features.K} mg/kg` },
                      { label: 'Temperatura média (7 dias)', value: `${result.features.temperature} °C` },
                      { label: 'Umidade média (7 dias)', value: `${result.features.humidity}%` },
                      { label: 'Chuva média mensal (12 meses)', value: `${result.features.rainfall} mm/mês` },
                    ].map((item) => (
                      <div key={item.label} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80">
                        <dt className="text-slate-400 text-[11px]">{item.label}</dt>
                        <dd className="font-mono text-white font-semibold mt-0.5">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {/* Current conditions (display only) */}
              {result.climate_data && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-1">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Condições Atuais ({resolvedPlace})
                    </h3>
                    <span className="text-[11px] text-slate-400">leitura do momento, só informativa</span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                      <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                        <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                        <span>Temperatura</span>
                      </div>
                      <div className="text-lg font-bold text-white font-mono">
                        {result.climate_data.temperature ?? '--'} °C
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                      <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                        <Droplets className="w-3.5 h-3.5 text-blue-400" />
                        <span>Umidade</span>
                      </div>
                      <div className="text-lg font-bold text-white font-mono">
                        {result.climate_data.humidity ?? '--'}%
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                      <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                        <CloudRain className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Precipitação</span>
                      </div>
                      <div className="text-lg font-bold text-white font-mono">
                        {result.climate_data.precipitation ?? 0} mm
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                      <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                        <Wind className="w-3.5 h-3.5 text-teal-400" />
                        <span>Vento</span>
                      </div>
                      <div className="text-lg font-bold text-white font-mono">
                        {result.climate_data.wind_speed ?? '--'} km/h
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800/80 border-dashed rounded-xl p-12 text-center text-slate-400">
              Preencha os parâmetros e clique em Obter Recomendação.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
