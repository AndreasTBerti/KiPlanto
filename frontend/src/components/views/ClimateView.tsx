import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Clock, MapPin, Wind } from 'lucide-react';
import type { ClimateData } from '../../types/api';
import { getCityClimate } from '../../services/api';
import type { CityCoordinates } from '../../services/api';
import { formatDateTime, formatNumber } from '../../utils/format';
import { CityPicker } from '../CityPicker';
import { Button } from '../ui/Button';
import { Notice } from '../ui/Notice';
import { ReadingTile } from '../ui/ReadingTile';
import { TemperaturaIcon, UmidadeIcon } from '../ui/icons';

const DEFAULT_CITY = 'Tupã';
const DEFAULT_UF = 'SP';

export const ClimateView: React.FC = () => {
  const [cityInput, setCityInput] = useState(DEFAULT_CITY);
  const [ufInput, setUfInput] = useState(DEFAULT_UF);
  // Começa carregando: a busca inicial é disparada pelo efeito abaixo.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{
    coordinates: CityCoordinates;
    climate: ClimateData;
  } | null>(null);

  // Só a resposta da busca mais recente é aplicada (evita resultado antigo
  // sobrescrevendo o novo e a dupla execução do StrictMode em dev).
  const latestRequest = useRef(0);

  // Todo setState fica nos callbacks da promise, nunca no corpo da função:
  // assim ela pode ser chamada dentro de um efeito sem render em cascata
  // (regra react/set-state-in-effect).
  const loadClimate = useCallback((cityName: string, uf: string) => {
    const requestId = ++latestRequest.current;
    const isLatest = () => requestId === latestRequest.current;
    getCityClimate(cityName, uf || undefined)
      .then((response) => {
        if (!isLatest()) return;
        setData(response);
        setError(null);
      })
      .catch((err: unknown) => {
        if (isLatest()) setError(err instanceof Error ? err.message : 'Falha ao obter dados climáticos.');
      })
      .finally(() => {
        if (isLatest()) setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadClimate(DEFAULT_CITY, DEFAULT_UF);
  }, [loadClimate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cityInput) return;
    setLoading(true);
    setError(null);
    loadClimate(cityInput, ufInput);
  };

  const climate = data?.climate;
  const coordinates = data?.coordinates;
  const placeName = coordinates?.city || climate?.city || cityInput;
  const placeState = coordinates?.state
    ? `${coordinates.state}${coordinates.uf ? ` (${coordinates.uf})` : ''}`
    : '';

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Search Input */}
      <form onSubmit={handleSearch} className="kp-card kp-card-compact flex flex-col sm:flex-row gap-3">
        <CityPicker
          city={cityInput}
          uf={ufInput}
          onChange={(nextCity, nextUf) => {
            setCityInput(nextCity);
            setUfInput(nextUf);
          }}
          className="flex-1 min-w-0"
        />
        <Button type="submit" loading={loading} disabled={!cityInput}>
          Buscar clima
        </Button>
      </form>

      {error && <Notice title="Não foi possível obter o clima">{error}</Notice>}

      {climate && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex items-start gap-3">
              <MapPin className="w-6 h-6 mt-1 text-terra shrink-0" aria-hidden="true" />
              <div>
                <h2 className="title text-ink">{placeName}</h2>
                <p className="text-sm text-ink-muted">
                  {placeState && <span>{placeState} · </span>}
                  <span className="font-mono">
                    {formatNumber(coordinates?.latitude ?? climate.latitude)}, {formatNumber(coordinates?.longitude ?? climate.longitude)}
                  </span>
                </p>
              </div>
            </div>

            {climate.time && (
              <p className="kp-meta flex items-center gap-1.5">
                <Clock className="w-4 h-4" aria-hidden="true" />
                {formatDateTime(climate.time)}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <ReadingTile
              icon={<TemperaturaIcon />}
              label="Temperatura"
              value={formatNumber(climate.temperature)}
              unit="°C"
              foot={`Média dos próximos 7 dias: ${formatNumber(climate.temperature_mean_7d)} °C`}
            />
            <ReadingTile
              icon={<UmidadeIcon />}
              label="Umidade"
              value={formatNumber(climate.humidity)}
              unit="%"
              foot={`Média dos próximos 7 dias: ${formatNumber(climate.humidity_mean_7d)} %`}
            />
            <ReadingTile
              icon={<UmidadeIcon />}
              label="Precipitação"
              value={formatNumber(climate.precipitation ?? 0)}
              unit="mm"
              foot={`Total previsto em 7 dias: ${formatNumber(climate.precipitation_total_7d)} mm`}
            />
            <ReadingTile
              icon={<Wind className="kp-icon" aria-hidden="true" />}
              label="Vento"
              value={formatNumber(climate.wind_speed)}
              unit="km/h"
              foot={`Direção: ${formatNumber(climate.wind_direction)}°`}
            />
          </div>

          {/* What the recommendation model receives for this city */}
          <section className="kp-card space-y-1">
            <h3 className="kp-card-title">Usado pelo modelo de recomendação</h3>
            <p className="text-sm text-ink-muted pb-3">Estes são os valores de clima que entram na recomendação para este município.</p>
            <ul className="kp-factors">
              <li>
                <span>Temperatura média (7 dias)</span>
                <span className="v">{formatNumber(climate.temperature_mean_7d)}</span>
                <span className="r">°C</span>
              </li>
              <li>
                <span>Umidade média (7 dias)</span>
                <span className="v">{formatNumber(climate.humidity_mean_7d)}</span>
                <span className="r">%</span>
              </li>
              <li>
                <span>Chuva média mensal (12 meses)</span>
                <span className="v">{formatNumber(climate.rainfall_monthly_avg)}</span>
                <span className="r">mm/mês</span>
              </li>
            </ul>
          </section>
        </div>
      )}
    </div>
  );
};
