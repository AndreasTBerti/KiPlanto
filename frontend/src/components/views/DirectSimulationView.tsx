import React, { useCallback, useState, useEffect } from 'react';
import { RotateCcw } from 'lucide-react';
import type { DirectPrevisionInput, PrevisionOutput, PredictionHistoryItem } from '../../types/api';
import { predictCropDirect } from '../../services/api';
import { Button } from '../ui/Button';
import { CropCard } from '../ui/CropCard';
import { Notice } from '../ui/Notice';
import { ReadingField } from '../ui/ReadingField';
import { SoloIcon, TemperaturaIcon, UmidadeIcon } from '../ui/icons';

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
  // Remonta os campos ao restaurar: descarta também o que estava digitado e inválido.
  const [resetCount, setResetCount] = useState(0);

  const runSimulation = useCallback(async () => {
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
          // Sem pH: a simulação não coleta pH e o modelo não usa essa variável.
          inputs: { n, p, k },
          result: response
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao processar simulação.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [n, p, k, temperature, humidity, rainfall, autoSimulate, onSaveHistory]);

  // runSimulation muda sempre que algum parâmetro muda: o efeito refaz a
  // simulação (com debounce de 250 ms) só no modo Tempo Real.
  useEffect(() => {
    if (!autoSimulate) return;
    const timer = setTimeout(() => {
      runSimulation();
    }, 250);
    return () => clearTimeout(timer);
  }, [autoSimulate, runSimulation]);

  const handleReset = () => {
    setN(80);
    setP(40);
    setK(40);
    setTemperature(24);
    setHumidity(65);
    setRainfall(120);
    setResetCount((count) => count + 1);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!autoSimulate) runSimulation();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="kp-label">Parâmetros da simulação</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-ink cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoSimulate}
              onChange={(e) => setAutoSimulate(e.target.checked)}
              className="w-4 h-4 cursor-pointer accent-broto"
            />
            Calcular em tempo real
          </label>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleReset}
            icon={<RotateCcw className="w-4 h-4" aria-hidden="true" />}
          >
            Restaurar valores
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: 6 campos (7 cols) */}
        <div className="lg:col-span-7">
          <form onSubmit={handleSubmit} className="kp-card space-y-6">
            <div key={resetCount} className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
              <ReadingField label="Nitrogênio (N)" name="Nitrogênio (N)" icon={<SoloIcon />} unit="mg/kg" value={n} onChange={setN} min={0} max={140} />
              <ReadingField label="Fósforo (P)" name="Fósforo (P)" icon={<SoloIcon />} unit="mg/kg" value={p} onChange={setP} min={5} max={145} />
              <ReadingField label="Potássio (K)" name="Potássio (K)" icon={<SoloIcon />} unit="mg/kg" value={k} onChange={setK} min={5} max={205} />
              <ReadingField label="Temperatura média" name="Temperatura média" icon={<TemperaturaIcon />} unit="°C" value={temperature} onChange={setTemperature} min={5} max={45} />
              <ReadingField label="Umidade média" name="Umidade média" icon={<UmidadeIcon />} unit="%" value={humidity} onChange={setHumidity} min={10} max={100} />
              <ReadingField label="Chuva média mensal" name="Chuva média mensal" icon={<UmidadeIcon />} unit="mm/mês" value={rainfall} onChange={setRainfall} min={10} max={300} />
            </div>

            {!autoSimulate && (
              <Button type="submit" loading={loading} className="w-full">
                Calcular predição
              </Button>
            )}
          </form>
        </div>

        {/* Right: Output (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {error && <Notice title="Não foi possível calcular a simulação">{error}</Notice>}

          {result ? (
            <CropCard result={result} busy={loading} />
          ) : (
            <div className="kp-empty">
              {loading ? 'Calculando a primeira simulação.' : 'Ajuste os valores para ver a recomendação.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
