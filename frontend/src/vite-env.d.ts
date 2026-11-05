/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL da API. Vazio (padrão) = mesma origem, usando o proxy do Vite em `npm run dev`. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
