import React, { useState } from 'react';
import {
  Trash2,
  Download,
  Search,
  MapPin
} from 'lucide-react';
import type { PredictionHistoryItem } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';

interface HistoryViewProps {
  history: PredictionHistoryItem[];
  onClearHistory: () => void;
  onDeleteItem: (id: string) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({
  history,
  onClearHistory,
  onDeleteItem,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState<PredictionHistoryItem | null>(null);

  const filteredHistory = history.filter((item) => {
    const cropName = CROP_DICTIONARY[item.result.crop_recomendation.toLowerCase()]?.namePt || item.result.crop_recomendation;
    return (
      item.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cropName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.result.crop_recomendation.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(history, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `kiplanto-historico-${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Search & Actions */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filtrar histórico..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-hidden focus:border-emerald-500 transition-colors"
          />
        </div>

        {history.length > 0 && (
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleExportJSON}
              className="flex items-center space-x-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 rounded-lg border border-slate-700 transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Exportar JSON</span>
            </button>
            <button
              onClick={onClearHistory}
              className="flex items-center space-x-1.5 text-xs bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 px-3 py-2 rounded-lg border border-rose-800/40 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Limpar</span>
            </button>
          </div>
        )}
      </div>

      {/* History Table */}
      {filteredHistory.length > 0 ? (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-mono bg-slate-950/40">
                  <th className="p-3.5 font-medium">Data</th>
                  <th className="p-3.5 font-medium">Município</th>
                  <th className="p-3.5 font-medium">Cultura Recomendada</th>
                  <th className="p-3.5 font-medium">Solo (N-P-K)</th>
                  <th className="p-3.5 font-medium">Confiança</th>
                  <th className="p-3.5 font-medium text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                {filteredHistory.map((item) => {
                  const cropInfo = CROP_DICTIONARY[item.result.crop_recomendation.toLowerCase()];
                  return (
                    <tr key={item.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-3.5 font-mono text-slate-400">
                        {new Date(item.timestamp).toLocaleString([], {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                      </td>
                      <td className="p-3.5 font-medium text-white flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        {item.city}
                      </td>
                      <td className="p-3.5">
                        <span className="font-semibold text-emerald-400">
                          {cropInfo?.namePt || item.result.crop_recomendation}
                        </span>
                        <span className="text-[10px] text-slate-400 ml-1 font-mono">
                          ({item.result.crop_recomendation})
                        </span>
                      </td>
                      <td className="p-3.5 font-mono text-slate-400">
                        N:{item.inputs.n} P:{item.inputs.p} K:{item.inputs.k}
                      </td>
                      <td className="p-3.5 font-mono">
                        {item.result.confidence ? (
                          <span className="text-emerald-400 font-medium">
                            {item.result.confidence}%
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                      <td className="p-3.5 text-right space-x-2">
                        <button
                          onClick={() => setSelectedItem(item)}
                          className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 border border-slate-700 cursor-pointer"
                        >
                          Detalhes
                        </button>
                        <button
                          onClick={() => onDeleteItem(item.id)}
                          className="text-xs text-rose-400 hover:text-rose-300 p-1 cursor-pointer"
                          title="Remover"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800/80 border-dashed rounded-xl p-12 text-center text-slate-400">
          Nenhum registro encontrado no histórico.
        </div>
      )}

      {/* Details Modal */}
      {selectedItem && (
        <div
          onClick={() => setSelectedItem(null)}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-xs z-50 flex items-center justify-center p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-semibold text-white">Detalhes da Análise</h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800 cursor-pointer"
              >
                Fechar
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400">Cultura Recomendada:</span>
                <div className="text-xl font-bold text-emerald-400 mt-0.5">
                  {CROP_DICTIONARY[selectedItem.result.crop_recomendation.toLowerCase()]?.namePt ||
                    selectedItem.result.crop_recomendation}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono">
                <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Município</span>
                  <span className="text-white">{selectedItem.city}</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Confiança</span>
                  <span className="text-emerald-400">{selectedItem.result.confidence || '--'}%</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Nitrogênio / Fósforo</span>
                  <span className="text-white">N: {selectedItem.inputs.n} | P: {selectedItem.inputs.p}</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Potássio / pH</span>
                  <span className="text-white">K: {selectedItem.inputs.k} | pH: {selectedItem.inputs.ph}</span>
                </div>
              </div>

              {selectedItem.result.climate_data && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1 font-mono">
                  <span className="text-slate-400 block text-[10px]">Telemetria Climática</span>
                  <div className="text-slate-300">
                    Temp: {selectedItem.result.climate_data.temperature} °C | Umidade: {selectedItem.result.climate_data.humidity}% | Chuva: {selectedItem.result.climate_data.precipitation ?? 0} mm
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
