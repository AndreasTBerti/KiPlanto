import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ChevronDown, MapPin } from 'lucide-react';
import { BR_UFS } from '../constants/brStates';
import MUNICIPIOS from '../constants/municipios.json';

const CITIES_BY_UF: Record<string, string[]> = MUNICIPIOS;

/** Minúsculas e sem acentos: "tupa" encontra "Tupã". */
function fold(text: string): string {
  return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

interface CityPickerProps {
  city: string;
  uf: string;
  /** `city` vem vazio quando a nova UF não tem um município com o nome atual. */
  onChange: (city: string, uf: string) => void;
  className?: string;
}

/**
 * UF + município da lista oficial do IBGE. O texto digitado só filtra a lista:
 * o valor só muda ao escolher uma opção, então não há como enviar cidade inexistente.
 */
export const CityPicker: React.FC<CityPickerProps> = ({ city, uf, onChange, className = '' }) => {
  const listId = useId();
  const [query, setQuery] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const cities = useMemo(() => CITIES_BY_UF[uf] ?? [], [uf]);
  const options = useMemo(() => {
    if (!query) return cities;
    const wanted = fold(query.trim());
    return cities.filter((name) => fold(name).includes(wanted));
  }, [cities, query]);

  useEffect(() => {
    if (open) listRef.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' });
  }, [open, activeIndex]);

  const close = () => {
    // Texto que não virou seleção é descartado: o campo volta ao último município válido.
    setQuery(null);
    setOpen(false);
  };

  const pick = (name: string) => {
    onChange(name, uf);
    close();
  };

  const openList = () => {
    setActiveIndex(Math.max(cities.indexOf(city), 0));
    setOpen(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) {
        openList();
      } else if (options.length) {
        const step = e.key === 'ArrowDown' ? 1 : -1;
        setActiveIndex((activeIndex + step + options.length) % options.length);
      }
    } else if (e.key === 'Enter' && open) {
      // Com a lista aberta, Enter escolhe a opção em vez de enviar o formulário.
      e.preventDefault();
      if (options[activeIndex]) pick(options[activeIndex]);
    } else if (e.key === 'Escape') {
      close();
    }
  };

  return (
    <div className={`flex gap-2 ${className}`}>
      <select
        value={uf}
        onChange={(e) => {
          const nextUf = e.target.value;
          onChange(CITIES_BY_UF[nextUf]?.includes(city) ? city : '', nextUf);
          close();
        }}
        aria-label="UF do município"
        className="kp-input w-auto shrink-0"
      >
        {BR_UFS.map((state) => (
          <option key={state.uf} value={state.uf} title={state.name}>
            {state.uf}
          </option>
        ))}
      </select>

      <div className="relative flex-1 min-w-0">
        <MapPin className="w-5 h-5 text-terra absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
        <input
          type="text"
          role="combobox"
          aria-label="Município"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && options[activeIndex] ? `${listId}-${activeIndex}` : undefined}
          autoComplete="off"
          value={query ?? city}
          placeholder="Selecione o município"
          onFocus={(e) => {
            e.target.select();
            openList();
          }}
          onClick={() => {
            if (!open) openList();
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIndex(0);
            setOpen(true);
          }}
          onBlur={close}
          onKeyDown={handleKeyDown}
          className="kp-input kp-input-with-icon pr-9"
        />
        <ChevronDown className="w-5 h-5 text-ink-muted absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />

        {open && (
          <ul
            id={listId}
            ref={listRef}
            role="listbox"
            aria-label={`Municípios de ${uf}`}
            className="absolute z-30 mt-1 w-full min-w-56 max-h-60 overflow-y-auto bg-surface-raised border border-line-strong rounded-md py-1 text-sm"
            style={{ boxShadow: 'var(--shadow-card)' }}
          >
            {options.map((name, index) => (
              <li
                key={name}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={name === city}
                // mouseDown (não click): acontece antes do blur que fecha a lista.
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(name);
                }}
                onMouseEnter={() => setActiveIndex(index)}
                className={`px-3 py-2 cursor-pointer ${
                  index === activeIndex ? 'bg-broto-soft text-broto-strong' : 'text-ink'
                } ${name === city ? 'font-semibold' : ''}`}
              >
                {name}
              </li>
            ))}
            {options.length === 0 && (
              <li className="px-3 py-2 text-ink-muted">Nenhum município de {uf} com esse nome.</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
};
