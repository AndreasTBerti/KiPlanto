import React, { useEffect, useState } from 'react';
import type { MarketLevel, MarketOutput } from '../../types/api';
import { getCropMarket } from '../../services/api';
import { formatGrouped, formatMoney } from '../../utils/format';

interface MarketCardProps {
  /** Classe do modelo (ex.: maize). */
  crop: string;
  cropName: string;
  city: string;
  uf?: string;
}

type LoadState = { key: string; data?: MarketOutput; error?: string };

const METRIC_ROWS = (unit: MarketOutput['unit']) => [
  {
    label: unit === 'fruto' ? 'Produção por hectare (frutos/ha)' : 'Produção por hectare (kg/ha)',
    value: (level: MarketLevel) => formatGrouped(level.yield_per_ha),
  },
  {
    label: unit === 'fruto' ? 'Preço recebido (R$/fruto)' : 'Preço recebido (R$/kg)',
    value: (level: MarketLevel) => formatMoney(level.price),
  },
  {
    label: 'Receita bruta por hectare (R$/ha)',
    value: (level: MarketLevel) => formatGrouped(level.revenue_per_ha),
  },
  {
    label: 'Área colhida (ha)',
    value: (level: MarketLevel) => formatGrouped(level.harvested_area_ha),
  },
  {
    label: unit === 'fruto' ? 'Produção total (mil frutos)' : 'Produção total (t)',
    value: (level: MarketLevel) => formatGrouped(level.production),
  },
];

const Metric: React.FC<{ label: string; value: string; unit: string }> = ({ label, value, unit }) => (
  <div className="kp-metric">
    <span className="kp-label">{label}</span>
    <span className="kp-metric-value">{value}</span>
    <span className="kp-meta">{unit}</span>
  </div>
);

/** Preço e produtividade da cultura indicada. Carrega à parte, sem atrasar a recomendação. */
export const MarketCard: React.FC<MarketCardProps> = ({ crop, cropName, city, uf }) => {
  const requestKey = JSON.stringify([crop, city, uf ?? '']);
  const [state, setState] = useState<LoadState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getCropMarket({ crop, city, state: uf }, controller.signal)
      .then((data) => setState({ key: requestKey, data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ key: requestKey, error: err instanceof Error ? err.message : 'Falha ao consultar o IBGE.' });
      });
    return () => controller.abort();
  }, [requestKey, crop, city, uf]);

  const loading = state?.key !== requestKey;
  const data = loading ? undefined : state?.data;
  const error = loading ? undefined : state?.error;
  const main = data?.levels[0];

  return (
    <section className="kp-card space-y-4" aria-busy={loading}>
      <h3 className="kp-card-title">Preço e produtividade · {cropName}</h3>

      {loading && (
        <div className="space-y-3 animate-pulse" aria-label="Carregando preço e produtividade">
          <div className="h-12 bg-surface-sunken rounded-md" />
          <div className="h-24 bg-surface-sunken rounded-md" />
        </div>
      )}

      {error && <p className="text-sm text-ink-muted">Não foi possível consultar o IBGE agora. Tente outra análise em instantes.</p>}

      {data && !main && (
        <p className="text-sm text-ink-muted">
          {data.product
            ? `O IBGE não registra produção de ${cropName} nos últimos 3 anos.`
            : `O IBGE não acompanha ${cropName} nesta pesquisa, então não há preço nem produção por hectare para mostrar.`}
        </p>
      )}

      {data && main && (
        <>
          {main.scope !== 'city' && (
            <p className="text-sm text-ink-muted">
              {city} não registra produção de {cropName} nos últimos 3 anos. Os destaques são {main.scope === 'country' ? 'do Brasil' : `de ${main.name}`}.
            </p>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pb-4 border-b border-line">
            <Metric
              label="Produção"
              value={formatGrouped(main.yield_per_ha)}
              unit={data.unit === 'fruto' ? 'frutos/ha' : 'kg/ha'}
            />
            <Metric
              label="Preço"
              value={main.price != null ? `R$ ${formatMoney(main.price)}` : '--'}
              unit={data.unit === 'fruto' ? 'por fruto' : 'por kg'}
            />
            <Metric
              label="Receita bruta"
              value={main.revenue_per_ha != null ? `R$ ${formatGrouped(main.revenue_per_ha)}` : '--'}
              unit="por hectare"
            />
          </div>

          <div className="overflow-x-auto">
            <table className="kp-table kp-table-compact">
              <thead>
                <tr>
                  <th scope="col"><span className="sr-only">Indicador</span></th>
                  {data.levels.map((level) => (
                    <th key={level.scope} scope="col" className="text-right">{level.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {METRIC_ROWS(data.unit).map((row) => (
                  <tr key={row.label}>
                    <th scope="row">{row.label}</th>
                    {data.levels.map((level) => (
                      <td key={level.scope} className="kp-data text-right whitespace-nowrap">{row.value(level)}</td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <th scope="row">Ano do dado</th>
                  {data.levels.map((level) => (
                    <td key={level.scope} className="kp-data text-right text-ink-muted">{level.year}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          <div className="kp-field-help space-y-1">
            {data.approximate && (
              <p>O IBGE não separa esta variedade: os números são de {data.product}.</p>
            )}
            <p>
              Médias do que já foi produzido, não garantia de safra. O preço é o valor da produção dividido pela quantidade, não a cotação do dia. A receita não desconta custos.
            </p>
            <p>
              Fonte:{' '}
              <a href={data.source_url} target="_blank" rel="noopener noreferrer" className="kp-link">
                {data.source}
                <span className="sr-only"> (abre em nova aba)</span>
              </a>
            </p>
          </div>
        </>
      )}
    </section>
  );
};
