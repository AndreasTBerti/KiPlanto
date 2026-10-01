import React, { useState, useEffect } from 'react';
import {
  Thermometer,
  Droplets,
  CloudRain,
  RotateCcw,
  Zap,
  AlertCircle
} from 'lucide-react';
import type { DirectPrevisionInput, PrevisionOutput, PredictionHistoryItem } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { predictCropDirect } from '../../services/api';

interface DirectSimulationViewProps {
  onSaveHistory: (item: PredictionHistoryItem) => void;
}

export const DirectSimulationView: React.FC<DirectSimulationViewProps> = ({ onSaveHistory }) => {
  const [n, setN] = useState<number>(80);
  const [p, setP] = useState<number>(40);
  const [k, setK] = useState<number>(40);
  const [temperature, setTemperature] = useState<number>(24);
  const [humidity, setHumidity] = useState<number>(65);
  const [rainfall, setRainfall] = useState<number>(120);

  const [loading, setLoading] = useState(false);
  const [autoSimulate, setAutoSimulate] = useState(true);
  const [result, setResult] = useState<PrevisionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: DirectPrevisionInput = {
        n: Number(n),
        p: Number(p),
        k: Number(k),
        temperature: Number(temperature),
        humidity: Number(humidity),
        rainfall: Number(rainfall),
      };
      const response = await predictCropDirect(payload);
      setResult(response);

      if (!autoSimulate) {
        onSaveHistory({
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          city: 'Simulação Manual',
          inputs: { n, p, k, ph: 6.5 },
          result: response
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao processar simulação.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoSimulate) {
      const timer = setTimeout(() => {
        runSimulation();
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [n, p, k, temperature, humidity, rainfall, autoSimulate]);

  const handleReset = () => {
    setN(80);
    setP(40);
    setK(40);
    setTemperature(24);
    setHumidity(65);
    setRainfall(120);
  };

  const cropKey = result?.crop_recomendation?.toLowerCase() || '';
  const cropInfo = CROP_DICTIONARY[cropKey];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Ajuste de Parâmetros
        </span>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoSimulate}
              onChange={(e) => setAutoSimulate(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
            <span className="flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Tempo Real
            </span>
          </label>

          <button
            onClick={handleReset}
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white px-2.5 py-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Resetar</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: 6 Sliders (7 cols) */}
        <div className="lg:col-span-7">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* N */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Nitrogênio (N)</span>
                  <span className="font-mono text-emerald-400 font-bold">{n} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="140"
                  value={n}
                  onChange={(e) => setN(Number(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* P */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Fósforo (P)</span>
                  <span className="font-mono text-blue-400 font-bold">{p} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="145"
                  value={p}
                  onChange={(e) => setP(Number(e.target.value))}
                  className="w-full accent-blue-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* K */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Potássio (K)</span>
                  <span className="font-mono text-purple-400 font-bold">{k} mg/kg</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="205"
                  value={k}
                  onChange={(e) => setK(Number(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Temperature */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium flex items-center gap-1">
                    <Thermometer className="w-3 h-3 text-amber-400" />
                    Temperatura
                  </span>
                  <span className="font-mono text-amber-400 font-bold">{temperature} °C</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="45"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Humidity */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium flex items-center gap-1">
                    <Droplets className="w-3 h-3 text-cyan-400" />
                    Umidade
                  </span>
                  <span className="font-mono text-cyan-400 font-bold">{humidity}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={humidity}
                  onChange={(e) => setHumidity(Number(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Rainfall */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium flex items-center gap-1">
                    <CloudRain className="w-3 h-3 text-teal-400" />
                    Precipitação
                  </span>
                  <span className="font-mono text-teal-400 font-bold">{rainfall} mm</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="300"
                  value={rainfall}
                  onChange={(e) => setRainfall(Number(e.target.value))}
                  className="w-full accent-teal-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>
            </div>

            {!autoSimulate && (
              <button
                onClick={runSimulation}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg text-sm transition-colors cursor-pointer"
              >
                <span>Calcular Predição</span>
              </button>
            )}
          </div>
        </div>

        {/* Right: Output (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {error && (
            <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-start space-x-3">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Erro</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Resultado
              </span>
              {loading ? (
                <span className="text-xs text-blue-400 flex items-center gap-1">
                  <div className="w-3 h-3 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                  Calculando...
                </span>
              ) : result?.confidence ? (
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                  {result.confidence}% Confiança
                </span>
              ) : null}
            </div>

            {result ? (
              <div className="space-y-4">
                <div>
                  <span className="text-xs text-slate-400 font-medium">Recomendação Ótima</span>
                  <h2 className="text-2xl font-extrabold text-white mt-1">
                    {cropInfo?.namePt || result.crop_recomendation}
                  </h2>
                  <span className="text-xs font-mono text-slate-400">({result.crop_recomendation})</span>
                  {cropInfo && (
                    <p className="text-xs text-slate-400 mt-2">{cropInfo.description}</p>
                  )}
                </div>

                {result.top_recommendations && result.top_recommendations.length > 0 && (
                  <div className="pt-4 border-t border-slate-800 space-y-2.5">
                    <span className="text-xs font-semibold text-slate-400">
                      Distribuição de Probabilidades
                    </span>
                    <div className="space-y-2">
                      {result.top_recommendations.map((rec) => {
                        const info = CROP_DICTIONARY[rec.crop.toLowerCase()];
                        return (
                          <div key={rec.crop} className="space-y-1">
                            <div className="flex justify-between text-xs">
                              <span className="text-slate-300 font-medium">{info?.namePt || rec.crop}</span>
                              <span className="font-mono text-slate-400">{rec.probability}%</span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500 rounded-full"
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
            ) : (
              <div className="text-center py-8 text-xs text-slate-400">
                Ajuste os controles deslizantes para visualizar a previsão.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
