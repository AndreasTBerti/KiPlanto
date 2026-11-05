import React, { useLayoutEffect, useRef, useState } from 'react';
import { RotateCcw, Wind } from 'lucide-react';
import type { PrevisionInput, PrevisionOutput, PredictionHistoryItem } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { predictCrop } from '../../services/api';
import { COMMON_CITIES } from '../../constants/cities';
import { formatNumber } from '../../utils/format';
import { CityPicker } from '../CityPicker';
import { RegionalNewsCard } from '../news/RegionalNewsCard';
import type { NewsIntent } from '../news/newsUtils';
import { Button } from '../ui/Button';
import { CoverArt } from '../ui/CoverArt';
import { CropCard } from '../ui/CropCard';
import { MarketCard } from '../ui/MarketCard';
import { Notice } from '../ui/Notice';
import { PhScale } from '../ui/PhScale';
import { ReadingField } from '../ui/ReadingField';
import { ReadingTile } from '../ui/ReadingTile';
import { CulturaIcon, PhIcon, SoloIcon, TemperaturaIcon, UmidadeIcon } from '../ui/icons';

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
  const resultsRef = useRef<HTMLDivElement>(null);

  // A tela troca entre formulário e resultado: volta ao topo e, no resultado, leva o foco
  // para ele, porque o botão que estava em foco deixou de existir.
  useLayoutEffect(() => {
    window.scrollTo({ top: 0 });
    resultsRef.current?.focus({ preventScroll: true });
  }, [result]);

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

  if (result) {
    const resolvedPlace = `${result.city || city}${result.uf ? `/${result.uf}` : ''}`;

    return (
      <div ref={resultsRef} tabIndex={-1} className="max-w-6xl mx-auto space-y-6 outline-none">
        {/* Condições atuais (só exibição) e ação para recomeçar */}
        <section className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            {result.climate_data && (
              <div className="space-y-1">
                <h2 className="kp-label">Condições atuais · {resolvedPlace}</h2>
                <p className="text-[13px] leading-[18px] text-ink-muted">Leitura do momento, só informativa</p>
              </div>
            )}
            <Button
              onClick={() => setResult(null)}
              icon={<RotateCcw className="kp-icon" aria-hidden="true" />}
              className="w-full sm:w-auto sm:ml-auto shrink-0"
            >
              Fazer outra análise
            </Button>
          </div>

          {result.climate_data && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <ReadingTile
                icon={<TemperaturaIcon />}
                label="Temperatura"
                value={formatNumber(result.climate_data.temperature)}
                unit="°C"
              />
              <ReadingTile
                icon={<UmidadeIcon />}
                label="Umidade"
                value={formatNumber(result.climate_data.humidity)}
                unit="%"
              />
              <ReadingTile
                icon={<UmidadeIcon />}
                label="Precipitação"
                value={formatNumber(result.climate_data.precipitation ?? 0)}
                unit="mm"
              />
              <ReadingTile
                icon={<Wind className="kp-icon" aria-hidden="true" />}
                label="Vento"
                value={formatNumber(result.climate_data.wind_speed)}
                unit="km/h"
              />
            </div>
          )}
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-5 space-y-6">
            <CropCard
              result={result}
              place={resolvedPlace}
              factorsNote="Valores entregues ao modelo. Temperatura e umidade: média de 7 dias. Chuva: média dos últimos 12 meses."
            />
            <MarketCard
              crop={result.crop_recommendation.toLowerCase()}
              cropName={CROP_DICTIONARY[result.crop_recommendation.toLowerCase()]?.namePt ?? result.crop_recommendation}
              city={result.city || city}
              uf={result.uf}
            />
          </div>

          {/* Notícias cruzadas com o modelo (SPEC §6.4) */}
          {result.features && (
            <div className="lg:col-span-7">
              <RegionalNewsCard
                city={result.city || city}
                uf={result.uf}
                features={result.features}
                onOpenNews={onOpenNews}
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input Form (5 cols) */}
        <div className="lg:col-span-5">
          <form onSubmit={handleSubmit} className="kp-card space-y-6">
            {/* City + UF */}
            <div className="space-y-3">
              <h2 className="kp-label">Município</h2>
              <CityPicker
                city={city}
                uf={uf}
                onChange={(nextCity, nextUf) => {
                  setCity(nextCity);
                  setUf(nextUf);
                }}
              />

              <div className="flex flex-wrap gap-1.5">
                {COMMON_CITIES.map((c) => (
                  <button
                    key={`${c.name}-${c.uf}`}
                    type="button"
                    onClick={() => {
                      setCity(c.name);
                      setUf(c.uf);
                    }}
                    title={`${c.name}/${c.uf}`}
                    aria-pressed={city === c.name && uf === c.uf}
                    className="kp-filter"
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Nutrients */}
            <div className="space-y-4 pt-6 border-t border-line">
              <h2 className="kp-label">Análise de solo</h2>

              <ReadingField
                label="Nitrogênio (N)"
                name="Nitrogênio (N)"
                icon={<SoloIcon />}
                unit="mg/kg"
                value={nRatio}
                onChange={setNRatio}
                min={0}
                max={140}
              />
              <ReadingField
                label="Fósforo (P)"
                name="Fósforo (P)"
                icon={<SoloIcon />}
                unit="mg/kg"
                value={pRatio}
                onChange={setPRatio}
                min={5}
                max={145}
              />
              <ReadingField
                label="Potássio (K)"
                name="Potássio (K)"
                icon={<SoloIcon />}
                unit="mg/kg"
                value={kRatio}
                onChange={setKRatio}
                min={5}
                max={205}
              />

              <ReadingField
                label={
                  <>
                    <span className="kp-keep">pH</span> do solo
                  </>
                }
                name="pH do solo"
                icon={<PhIcon />}
                value={ph}
                onChange={setPh}
                min={3.5}
                max={9}
                step={0.1}
                slider={false}
                help="Faixa aceita: 3,5 a 9. Fica registrado no histórico, mas o modelo atual foi treinado sem pH e não o usa."
              />
              <PhScale value={ph} />
            </div>

            <Button type="submit" loading={loading} icon={<CulturaIcon />} className="w-full">
              {loading ? 'Gerando recomendação' : 'Gerar recomendação'}
            </Button>
          </form>
        </div>

        {/* Right Column: apresentação da análise (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {error && <Notice title="Não foi possível gerar a recomendação">{error}</Notice>}

          <div className="kp-card p-0! overflow-hidden">
            <div className="p-6 space-y-2">
              <h2 className="title text-ink">Que planto?</h2>
              <p className="text-ink-muted">
                Informe o município e a análise de solo. O KiPlanto cruza esses dados com o clima da região e mostra a melhor aposta para estas condições.
              </p>
            </div>
            <CoverArt className="block w-full h-auto" />
          </div>
        </div>
      </div>
    </div>
  );
};
