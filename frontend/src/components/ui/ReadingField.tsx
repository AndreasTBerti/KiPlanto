import React, { useEffect, useId, useRef, useState } from 'react';
import { formatNumber, parseNumber } from '../../utils/format';

interface ReadingFieldProps {
  label: React.ReactNode;
  icon?: React.ReactNode;
  /** Nome em texto do campo, para mensagens e leitores de tela. */
  name: string;
  /** Fica fora do input: a pessoa digita só o número. */
  unit?: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  /** Mostra um controle deslizante ao lado do campo. */
  slider?: boolean;
  help?: React.ReactNode;
}

/**
 * Campo de leitura do design system, com vírgula decimal. Só valores válidos sobem
 * para a tela. Um valor inválido fica no campo, com a mensagem, e a validação nativa
 * (setCustomValidity) impede o envio do formulário enquanto ele não for corrigido.
 */
export const ReadingField: React.FC<ReadingFieldProps> = ({
  label,
  icon,
  name,
  unit,
  value,
  onChange,
  min,
  max,
  step = 1,
  slider = true,
  help,
}) => {
  const helpId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const fractionDigits = step < 1 ? 1 : 0;
  const limits = `${formatNumber(min)} a ${formatNumber(max)}`;

  // O texto digitado vale enquanto o valor da tela for o mesmo de quando foi digitado:
  // se a tela mudar o valor (controle deslizante, restaurar valores), mostra o novo.
  const [draft, setDraft] = useState<{ text: string; base: number; error: string | null } | null>(null);
  const current = draft && draft.base === value ? draft : null;
  const text = current ? current.text : formatNumber(value, fractionDigits);
  const error = current?.error ?? null;

  useEffect(() => {
    inputRef.current?.setCustomValidity(error ?? '');
  }, [error]);

  const handleTextChange = (nextText: string) => {
    const parsed = parseNumber(nextText);
    if (parsed === null) {
      const message = nextText.trim() === '' ? `Informe ${name}.` : `${name}: digite só o número.`;
      setDraft({ text: nextText, base: value, error: message });
    } else if (parsed < min || parsed > max) {
      const position = parsed < min ? 'abaixo' : 'acima';
      setDraft({ text: nextText, base: value, error: `Valor ${position} da faixa aceita (${limits}).` });
    } else {
      setDraft({ text: nextText, base: parsed, error: null });
      onChange(parsed);
    }
  };

  return (
    <div className={`kp-field ${error ? 'is-invalid' : ''}`}>
      <label htmlFor={`${helpId}-input`} className="kp-field-label">
        {icon}
        <span>{label}</span>
      </label>

      <div className={slider ? 'kp-field-row' : undefined}>
        <div className="kp-field-box">
          <input
            id={`${helpId}-input`}
            ref={inputRef}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={text}
            onChange={(e) => handleTextChange(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={helpId}
          />
          {unit && <span className="kp-field-unit">{unit}</span>}
        </div>

        {slider && (
          <div className="kp-field-range">
            <input
              type="range"
              className="kp-range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => {
                setDraft(null);
                onChange(Number(e.target.value));
              }}
              aria-label={`${name}${unit ? ` em ${unit}` : ''}`}
            />
            <div className="kp-field-limits" aria-hidden="true">
              <span>{formatNumber(min)}</span>
              <span>{formatNumber(max)}</span>
            </div>
          </div>
        )}
      </div>

      <p id={helpId} className="kp-field-help">
        {error ?? help ?? `Faixa aceita: ${limits}`}
      </p>
    </div>
  );
};
