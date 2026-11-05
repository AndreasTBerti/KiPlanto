import React, { useEffect, useState } from 'react';
import { CheckCircle2, Search } from 'lucide-react';
import { CROP_DICTIONARY } from '../../types/api';
import type { CropCategory } from '../../types/api';
import { getSupportedCrops } from '../../services/api';
import { Notice } from '../ui/Notice';

type CategoryFilter = 'Todas' | CropCategory;

const CATEGORIES: CategoryFilter[] = ['Todas', 'Frutas', 'Grãos', 'Leguminosas', 'Fibras', 'Comercial'];

type ModelCheck =
  | { status: 'loading' }
  | { status: 'ok'; crops: string[] }
  | { status: 'error' };

export const CropsCatalogView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('Todas');
  const [modelCheck, setModelCheck] = useState<ModelCheck>({ status: 'loading' });

  // O catálogo é um dicionário local; aqui ele é conferido com as classes que
  // o modelo realmente conhece (GET /ai/crops), para acusar divergências se o
  // modelo for retreinado com outras culturas.
  useEffect(() => {
    let active = true;
    getSupportedCrops()
      .then((response) => {
        if (active) setModelCheck({ status: 'ok', crops: response.crops.map((c) => c.toLowerCase()) });
      })
      .catch(() => {
        if (active) setModelCheck({ status: 'error' });
      });
    return () => {
      active = false;
    };
  }, []);

  const modelCrops = modelCheck.status === 'ok' ? new Set(modelCheck.crops) : null;
  const missingInCatalog = modelCheck.status === 'ok'
    ? modelCheck.crops.filter((crop) => !CROP_DICTIONARY[crop])
    : [];
  const missingInModel = modelCrops
    ? Object.keys(CROP_DICTIONARY).filter((crop) => !modelCrops.has(crop))
    : [];

  const cropEntries = Object.entries(CROP_DICTIONARY);

  const filteredCrops = cropEntries.filter(([key, info]) => {
    const matchesSearch =
      info.namePt.toLowerCase().includes(searchTerm.toLowerCase()) ||
      key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      info.description.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory =
      selectedCategory === 'Todas' || info.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Filters & Search Row */}
      <div className="kp-card kp-card-compact flex flex-col md:flex-row md:items-center gap-3 justify-between">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar cultura"
            aria-label="Buscar cultura"
            className="kp-input kp-input-with-icon"
          />
        </div>

        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtrar por categoria">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              aria-pressed={selectedCategory === cat}
              className="kp-filter"
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Consistency with the model */}
      {modelCheck.status === 'loading' && (
        <p className="text-sm text-ink-muted">Conferindo o catálogo com as culturas do modelo.</p>
      )}

      {modelCheck.status === 'error' && (
        <Notice tone="neutral">Não foi possível conferir com o modelo (API indisponível). Exibindo o catálogo local.</Notice>
      )}

      {modelCheck.status === 'ok' && missingInCatalog.length === 0 && missingInModel.length === 0 && (
        <p className="text-sm text-broto flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
          <span>Catálogo confere com as {modelCheck.crops.length} culturas do modelo.</span>
        </p>
      )}

      {(missingInCatalog.length > 0 || missingInModel.length > 0) && (
        <Notice tone="warn" title="Catálogo e modelo divergem">
          {missingInCatalog.length > 0 && (
            <p>
              O modelo recomenda culturas sem descrição no catálogo:{' '}
              <span className="font-mono">{missingInCatalog.join(', ')}</span>
            </p>
          )}
          {missingInModel.length > 0 && (
            <p>
              Culturas do catálogo que o modelo não conhece:{' '}
              <span className="font-mono">{missingInModel.join(', ')}</span>
            </p>
          )}
        </Notice>
      )}

      {/* Crops Grid */}
      {filteredCrops.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCrops.map(([key, info]) => (
            <div key={key} className="kp-card kp-card-compact space-y-2">
              <h2 className="font-display text-xl font-bold leading-7 tracking-tight text-ink">{info.namePt}</h2>
              <div className="flex flex-wrap gap-1.5">
                <span className="kp-chip kp-chip-broto">{info.category}</span>
                <span className="kp-chip font-mono font-medium">{key}</span>
                {modelCrops && !modelCrops.has(key) && (
                  <span className="kp-chip kp-chip-terra">Fora do modelo</span>
                )}
              </div>
              <p className="text-sm text-ink-muted">{info.description}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="kp-empty">Nenhuma cultura encontrada. Tente outro nome ou categoria.</div>
      )}
    </div>
  );
};
