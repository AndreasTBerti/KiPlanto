import React from 'react';

interface ReadingTileProps {
  icon: React.ReactNode;
  label: string;
  /** Já formatado, com vírgula decimal. */
  value: string;
  unit?: string;
  foot?: React.ReactNode;
}

/** Uma leitura com nome, valor grande e status em uma linha. Só borda, sem sombra. */
export const ReadingTile: React.FC<ReadingTileProps> = ({ icon, label, value, unit, foot }) => (
  <div className="kp-reading">
    <div className="kp-reading-head">
      {icon}
      <span>{label}</span>
    </div>
    <div className="kp-reading-value">
      {value}
      {unit && <small>{unit}</small>}
    </div>
    {foot && <div className="kp-reading-foot">{foot}</div>}
  </div>
);
