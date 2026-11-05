import React, { useState } from 'react';
import { Trash2, Download, Search, MapPin, X } from 'lucide-react';
import type { PredictionHistoryItem } from '../../types/api';
import { CROP_DICTIONARY } from '../../types/api';
import { formatDateTime, formatNumber, toScore } from '../../utils/format';
import { Button } from '../ui/Button';
import { ConfidenceBadge } from '../ui/ConfidenceBadge';

interface HistoryViewProps {
  history: PredictionHistoryItem[];
  onClearHistory: () => void;
  onDeleteItem: (id: string) => void;
}

const cropName = (crop: string) => CROP_DICTIONARY[crop.toLowerCase()]?.namePt || crop;

export const HistoryView: React.FC<HistoryViewProps> = ({
  history,
  onClearHistory,
  onDeleteItem,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState<PredictionHistoryItem | null>(null);

  const placeLabel = (item: PredictionHistoryItem) => (item.uf ? `${item.city}/${item.uf}` : item.city);

  // Registros gravados depois da correção trazem rainfall_monthly_avg: neles a
  // chuva do modelo é mensal (mm/mês) e temperatura/umidade são médias de 7 dias.
  const selectedFeatures = selectedItem?.result.features;
  const selectedUsesCorrectedScales = selectedItem?.result.climate_data?.rainfall_monthly_avg != null;
  const selectedClimate = selectedItem?.result.climate_data;

  const filteredHistory = history.filter((item) => {
    const term = searchTerm.toLowerCase();
    return (
      placeLabel(item).toLowerCase().includes(term) ||
      cropName(item.result.crop_recommendation).toLowerCase().includes(term) ||
      item.result.crop_recommendation.toLowerCase().includes(term)
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
      <div className="kp-card kp-card-compact flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-5 h-5 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filtrar por município ou cultura"
            aria-label="Filtrar histórico"
            className="kp-input kp-input-with-icon"
          />
        </div>

        {history.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto sm:shrink-0">
            <Button variant="secondary" size="sm" className="py-2.5 whitespace-nowrap" onClick={handleExportJSON} icon={<Download className="kp-icon" aria-hidden="true" />}>
              Exportar JSON
            </Button>
            <Button variant="danger" size="sm" className="py-2.5 whitespace-nowrap" onClick={onClearHistory} icon={<Trash2 className="kp-icon" aria-hidden="true" />}>
              Limpar histórico
            </Button>
          </div>
        )}
      </div>

      {/* History Table */}
      {filteredHistory.length > 0 ? (
        <div className="bg-surface-raised border border-line rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="kp-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Município</th>
                  <th>Cultura recomendada</th>
                  <th>Solo (N-P-K)</th>
                  <th>Pontuação</th>
                  <th className="text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((item) => {
                  const score = item.result.confidence != null ? toScore(item.result.confidence) : null;
                  return (
                    <tr key={item.id}>
                      <td className="kp-data text-ink-muted whitespace-nowrap">{formatDateTime(item.timestamp)}</td>
                      <td className="font-semibold">
                        <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
                          <MapPin className="w-4 h-4 text-terra" aria-hidden="true" />
                          {placeLabel(item)}
                        </span>
                      </td>
                      <td className="font-semibold">{cropName(item.result.crop_recommendation)}</td>
                      <td className="kp-data text-ink-muted whitespace-nowrap">
                        {formatNumber(item.inputs.n)}-{formatNumber(item.inputs.p)}-{formatNumber(item.inputs.k)}
                      </td>
                      <td>
                        {score != null ? (
                          <span className="inline-flex items-center gap-2 whitespace-nowrap">
                            <span className="kp-data">{score}</span>
                            <ConfidenceBadge score={score} />
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setSelectedItem(item)}>
                            Ver detalhes
                          </Button>
                          <button
                            onClick={() => onDeleteItem(item.id)}
                            className="kp-icon-btn kp-icon-btn-danger"
                            aria-label={`Remover análise de ${placeLabel(item)}`}
                            title="Remover"
                          >
                            <Trash2 className="kp-icon" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="kp-empty">
          {history.length > 0 ? 'Nenhuma análise com esse filtro.' : 'Nenhuma análise no histórico ainda.'}
        </div>
      )}

      {/* Details Modal */}
      {selectedItem && (
        <div
          onClick={() => setSelectedItem(null)}
          className="kp-backdrop fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Detalhes da análise"
            className="kp-crop w-full max-w-lg max-h-full overflow-y-auto"
          >
            <div className="kp-crop-top">
              <span className="kp-crop-rank">{placeLabel(selectedItem)}</span>
              <button onClick={() => setSelectedItem(null)} className="kp-icon-btn" aria-label="Fechar detalhes">
                <X className="kp-icon" aria-hidden="true" />
              </button>
            </div>

            <h3 className="font-display text-3xl font-bold tracking-tight text-ink">
              {cropName(selectedItem.result.crop_recommendation)}
            </h3>

            {selectedItem.result.confidence != null && (
              <div className="kp-score">
                <div className="kp-score-bar" aria-hidden="true">
                  <span style={{ width: `${toScore(selectedItem.result.confidence)}%` }} />
                </div>
                <span className="kp-score-num">
                  <span className="sr-only">Pontuação: </span>
                  {toScore(selectedItem.result.confidence)}
                </span>
                <ConfidenceBadge score={toScore(selectedItem.result.confidence)} />
              </div>
            )}

            <ul className="kp-factors">
              <li>
                <span>Nitrogênio (N)</span>
                <span className="v">{formatNumber(selectedItem.inputs.n)}</span>
                <span className="r">mg/kg</span>
              </li>
              <li>
                <span>Fósforo (P)</span>
                <span className="v">{formatNumber(selectedItem.inputs.p)}</span>
                <span className="r">mg/kg</span>
              </li>
              <li>
                <span>Potássio (K)</span>
                <span className="v">{formatNumber(selectedItem.inputs.k)}</span>
                <span className="r">mg/kg</span>
              </li>
              <li>
                <span>pH (não usado pelo modelo)</span>
                <span className="v">{formatNumber(selectedItem.inputs.ph)}</span>
                <span className="r" />
              </li>
            </ul>

            {selectedFeatures ? (
              <div className="space-y-2">
                <h4 className="kp-label">Clima usado pelo modelo</h4>
                <ul className="kp-factors">
                  <li>
                    <span>{selectedUsesCorrectedScales ? 'Temperatura média' : 'Temperatura'}</span>
                    <span className="v">{formatNumber(selectedFeatures.temperature)}</span>
                    <span className="r">°C</span>
                  </li>
                  <li>
                    <span>{selectedUsesCorrectedScales ? 'Umidade média' : 'Umidade'}</span>
                    <span className="v">{formatNumber(selectedFeatures.humidity)}</span>
                    <span className="r">%</span>
                  </li>
                  <li>
                    <span>{selectedUsesCorrectedScales ? 'Chuva média mensal' : 'Chuva'}</span>
                    <span className="v">{formatNumber(selectedFeatures.rainfall)}</span>
                    <span className="r">{selectedUsesCorrectedScales ? 'mm/mês' : 'mm'}</span>
                  </li>
                </ul>
                {!selectedUsesCorrectedScales && (
                  <p className="kp-field-help">Registro anterior à correção das escalas de clima do modelo.</p>
                )}
              </div>
            ) : selectedClimate && (
              <div className="space-y-2">
                <h4 className="kp-label">Clima no momento da análise</h4>
                <ul className="kp-factors">
                  <li>
                    <span>Temperatura</span>
                    <span className="v">{formatNumber(selectedClimate.temperature)}</span>
                    <span className="r">°C</span>
                  </li>
                  <li>
                    <span>Umidade</span>
                    <span className="v">{formatNumber(selectedClimate.humidity)}</span>
                    <span className="r">%</span>
                  </li>
                  <li>
                    <span>Chuva</span>
                    <span className="v">{formatNumber(selectedClimate.precipitation ?? 0)}</span>
                    <span className="r">mm</span>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
