import React, { useState } from 'react';

interface NewsImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  /** Exibido sem imagem ou quando ela falha ao carregar. */
  fallback?: React.ReactNode;
}

/** Imagem hospedada pelo veículo: lazy, sem Referer e com fallback em caso de erro. */
export const NewsImage: React.FC<NewsImageProps> = ({ src, alt, className, fallback = null }) => {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (!src || failedSrc === src) return <>{fallback}</>;

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailedSrc(src)}
      className={className}
    />
  );
};
