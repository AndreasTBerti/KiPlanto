import React, { useState, useEffect } from 'react';
import {
  Search,
  Thermometer,
  Droplets,
  CloudRain,
  Wind,
  Compass,
  MapPin,
  Clock,
  AlertCircle
} from 'lucide-react';
import type { ClimateData } from '../../types/api';
import { getCityClimate } from '../../services/api';

export const ClimateView: React.FC = () => {
  const [cityInput, setCityInput] = useState('Tupã');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{
    coordinates: Record<string, unknown>;
    climate: ClimateData;
  } | null>(null);

  const fetchClimate = async (cityName: string) => {
    if (!cityName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getCityClimate(cityName.trim());
      setData(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Falha ao obter dados climáticos.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClimate('Tupã');
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchClimate(cityInput);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Search Input */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={cityInput}
              onChange={(e) => setCityInput(e.target.value)}
              placeholder="Nome do município..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-hidden focus:border-amber-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
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

      {data && data.climate && (
        <div className="space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
                <MapPin className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">
                  {String(data.coordinates?.city || data.climate.city || cityInput)}
                </h2>
                <div className="text-xs text-slate-400 font-mono flex items-center gap-3 mt-0.5">
                  <span>Lat: {String(data.coordinates?.latitude || data.climate.latitude)}</span>
                  <span>Long: {String(data.coordinates?.longitude || data.climate.longitude)}</span>
                </div>
              </div>
            </div>

            {data.climate.time && (
              <div className="text-xs text-slate-400 flex items-center gap-1.5 font-mono bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                <Clock className="w-3.5 h-3.5" />
                <span>{data.climate.time}</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Temperatura</span>
                <Thermometer className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {data.climate.temperature} °C
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Média 7d: {data.climate.temperature_forecast} °C
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Umidade</span>
                <Droplets className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {data.climate.humidity}%
              </div>
              <div className="text-xs text-slate-400 mt-1">Umidade relativa</div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Precipitação</span>
                <CloudRain className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {data.climate.precipitation ?? 0} mm
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Previsto 7d: {data.climate.preciptation_forecast} mm
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Vento</span>
                <Wind className="w-4 h-4 text-teal-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {data.climate.wind_speed} km/h
              </div>
              <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <Compass className="w-3 h-3 text-slate-400" />
                <span>{data.climate.wind_direction}°</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
