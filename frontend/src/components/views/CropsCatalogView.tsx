import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { CROP_DICTIONARY } from '../../types/api';

type CategoryFilter = 'Todas' | 'Frutas' | 'Grãos' | 'Leguminosas' | 'Fibras' | 'Comercial';

const CATEGORIES: CategoryFilter[] = ['Todas', 'Frutas', 'Grãos', 'Leguminosas', 'Fibras', 'Comercial'];

export const CropsCatalogView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('Todas');

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
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-4 justify-between">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar cultura..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-hidden focus:border-emerald-500 transition-colors"
          />
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-semibold'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Crops Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCrops.map(([key, info]) => (
          <div
            key={key}
            className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition-colors space-y-2 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-base font-bold text-white tracking-tight">
                  {info.namePt}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800 font-mono">
                  {key}
                </span>
              </div>
              <div className="mt-1">
                <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-500/20">
                  {info.category}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                {info.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
