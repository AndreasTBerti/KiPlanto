import React from 'react';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

const TONES = {
  error: { icon: AlertCircle, role: 'alert' },
  warn: { icon: AlertTriangle, role: 'status' },
  neutral: { icon: Info, role: 'status' },
} as const;

interface NoticeProps {
  tone?: keyof typeof TONES;
  title?: string;
  children: React.ReactNode;
}

export const Notice: React.FC<NoticeProps> = ({ tone = 'error', title, children }) => {
  const { icon: Icon, role } = TONES[tone];
  return (
    <div className={`kp-notice kp-notice-${tone}`} role={role}>
      <Icon className="kp-icon" aria-hidden="true" />
      <div className="min-w-0 space-y-1">
        {title && <p className="font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
};
