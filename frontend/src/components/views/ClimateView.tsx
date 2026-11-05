import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Thermometer,
  Droplets,
  CloudRain,
  Wind,
  Compass,
  MapPin,
  Clock,
  AlertCircle,
  Cpu
} from 'lucide-react';
import type { ClimateData } from '../../types/api';
import { getCityClimate } from '../../services/api';
import type { CityCoordinates } from '../../services/api';
import { CityPicker } from '../CityPicker';

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
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <CityPicker
            city={cityInput}
            uf={ufInput}
            onChange={(nextCity, nextUf) => {
              setCityInput(nextCity);
              setUfInput(nextUf);
            }}
            accent="amber"
            className="flex-1 min-w-0"
          />
          <button
            type="submit"
            disabled={loading || !cityInput}
            className="bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <span>Buscar Clima</span>
            )}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-start space-x-3">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block">Erro</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {climate && (
        <div className="space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
                <MapPin className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">
                  {placeName}
                  {placeState && <span className="text-sm font-normal text-slate-400">, {placeState}</span>}
                </h2>
                <div className="text-xs text-slate-400 font-mono flex items-center gap-3 mt-0.5">
                  <span>Lat: {coordinates?.latitude ?? climate.latitude}</span>
                  <span>Long: {coordinates?.longitude ?? climate.longitude}</span>
                </div>
              </div>
            </div>

            {climate.time && (
              <div className="text-xs text-slate-400 flex items-center gap-1.5 font-mono bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                <Clock className="w-3.5 h-3.5" />
                <span>{climate.time}</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Temperatura agora</span>
                <Thermometer className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {climate.temperature ?? '--'} °C
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Média dos próximos 7 dias: {climate.temperature_mean_7d ?? '--'} °C
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Umidade agora</span>
                <Droplets className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {climate.humidity ?? '--'}%
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Média dos próximos 7 dias: {climate.humidity_mean_7d ?? '--'}%
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Precipitação agora</span>
                <CloudRain className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {climate.precipitation ?? 0} mm
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Total previsto em 7 dias: {climate.precipitation_total_7d ?? '--'} mm
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Vento agora</span>
                <Wind className="w-4 h-4 text-teal-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {climate.wind_speed ?? '--'} km/h
              </div>
              <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <Compass className="w-3 h-3 text-slate-400" />
                <span>{climate.wind_direction ?? '--'}°</span>
              </div>
            </div>
          </div>

          {/* What the recommendation model receives for this city */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              <span>Usado pelo modelo de recomendação</span>
            </div>
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80">
                <dt className="text-slate-400 text-[11px]">Temperatura média (7 dias)</dt>
                <dd className="font-mono text-white font-semibold mt-0.5">{climate.temperature_mean_7d ?? '--'} °C</dd>
              </div>
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80">
                <dt className="text-slate-400 text-[11px]">Umidade média (7 dias)</dt>
                <dd className="font-mono text-white font-semibold mt-0.5">{climate.humidity_mean_7d ?? '--'}%</dd>
              </div>
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80">
                <dt className="text-slate-400 text-[11px]">Chuva média mensal (últimos 12 meses)</dt>
                <dd className="font-mono text-white font-semibold mt-0.5">{climate.rainfall_monthly_avg ?? '--'} mm/mês</dd>
              </div>
            </dl>
          </div>
        </div>
      )}
    </div>
  );
};
