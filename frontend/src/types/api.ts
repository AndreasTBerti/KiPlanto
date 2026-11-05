export interface AuthUser {
  id: number;
  name: string;
  email: string;
}

export interface PrevisionInput {
  city: string;
  /** UF (ex.: "SP"). Opcional; resolve cidades homônimas. */
  state?: string;
  n_ratio: number;
  p_ratio: number;
  k_ratio: number;
  /** Aceito e registrado, mas NÃO usado pelo modelo atual. */
  ph?: number;
}

export interface DirectPrevisionInput {
  n: number;
  p: number;
  k: number;
  temperature: number;
  humidity: number;
  rainfall: number;
  ph?: number;
}

export interface TopRecommendation {
  crop: string;
  probability: number;
}

export interface ClimateData {
  city?: string;
  state?: string;
  uf?: string;
  latitude?: number;
  longitude?: number;
  // Condições do momento (só exibição)
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  wind_direction?: number;
  precipitation?: number;
  time?: string;
  // Agregados usados pelo modelo
  temperature_mean_7d?: number;
  humidity_mean_7d?: number;
  /** Total previsto para os próximos 7 dias, mm. */
  precipitation_total_7d?: number;
  /** Chuva média mensal dos últimos 12 meses, mm/mês. */
  rainfall_monthly_avg?: number;
  /** @deprecated use temperature_mean_7d */
  temperature_forecast?: number;
  /** @deprecated média DIÁRIA dos 7 dias; use precipitation_total_7d */
  preciptation_forecast?: number;
  /** @deprecated média diária de chuva dos 7 dias */
  rain_forecast?: number;
}

export interface PrevisionOutput {
  crop_recommendation: string;
  /** @deprecated grafia antiga de crop_recommendation */
  crop_recomendation?: string;
  confidence?: number;
  city?: string;
  state?: string;
  uf?: string;
  top_recommendations?: TopRecommendation[];
  climate_data?: ClimateData;
  features?: {
    N: number;
    P: number;
    K: number;
    temperature: number;
    humidity: number;
    rainfall: number;
  };
}

export interface PredictionHistoryItem {
  id: string;
  timestamp: string;
  city: string;
  uf?: string;
  inputs: {
    n: number;
    p: number;
    k: number;
    /** Registrado quando informado; o modelo atual não usa pH. */
    ph?: number;
  };
  result: PrevisionOutput;
}

export type CropCategory = 'Frutas' | 'Grãos' | 'Leguminosas' | 'Fibras' | 'Comercial';

export const CROP_DICTIONARY: Record<string, { namePt: string; category: CropCategory; description: string }> = {
  apple: { namePt: 'Maçã', category: 'Frutas', description: 'Clima temperado, exigência de frio invernal e solos profundos.' },
  banana: { namePt: 'Banana', category: 'Frutas', description: 'Alta demanda de potássio, umidade elevada e calor contínuo.' },
  blackgram: { namePt: 'Feijão-Preto (Vigna)', category: 'Leguminosas', description: 'Fixadora de nitrogênio, resistente a secas moderadas.' },
  chickpea: { namePt: 'Grão-de-Bico', category: 'Leguminosas', description: 'Clima seco a moderado, solos bem drenados e pH neutro.' },
  coconut: { namePt: 'Coco', category: 'Comercial', description: 'Regiões tropicais costeiras, solos arenosos e alta luminosidade.' },
  coffee: { namePt: 'Café', category: 'Comercial', description: 'Solos férteis, altitudes elevadas e temperaturas amenas.' },
  cotton: { namePt: 'Algodão', category: 'Fibras', description: 'Ciclo quente com períodos secos na maturação da fibra.' },
  grapes: { namePt: 'Uva', category: 'Frutas', description: 'Exige boa drenagem, controle hídrico e boa insolação.' },
  jute: { namePt: 'Juta', category: 'Fibras', description: 'Cultivo tropical em áreas de alta precipitação e alagamento.' },
  kidneybeans: { namePt: 'Feijão Vermelho', category: 'Leguminosas', description: 'Exige solos arejados com níveis balanceados de N-P-K.' },
  lentil: { namePt: 'Lentilha', category: 'Leguminosas', description: 'Tolerante ao frio, ciclo rápido e baixa necessidade hídrica.' },
  maize: { namePt: 'Milho', category: 'Grãos', description: 'Grande absorção de nitrogênio e luminosidade intensa.' },
  mango: { namePt: 'Manga', category: 'Frutas', description: 'Tolerância a calor, necessita de estiagem para floração.' },
  mothbeans: { namePt: 'Feijão-Moth', category: 'Leguminosas', description: 'Alta tolerância a estresse hídrico e solos pobres.' },
  mungbean: { namePt: 'Feijão-Mungo', category: 'Leguminosas', description: 'Ciclo curto, excelente para rotação de culturas.' },
  muskmelon: { namePt: 'Melão Cantaloupe', category: 'Frutas', description: 'Solos arenosos, alta insolação e irrigação controlada.' },
  orange: { namePt: 'Laranja', category: 'Frutas', description: 'Pomares com boa profundidade de solo e pH entre 5.5 e 6.5.' },
  papaya: { namePt: 'Mamão', category: 'Frutas', description: 'Desenvolvimento rápido em regiões quentes e solos drenados.' },
  pigeonpeas: { namePt: 'Feijão-Guandu', category: 'Leguminosas', description: 'Raízes profundas, descompactação de solo e fixação biológica.' },
  pomegranate: { namePt: 'Romã', category: 'Frutas', description: 'Resistência a solos alcalinos e climas semiáridos.' },
  rice: { namePt: 'Arroz', category: 'Grãos', description: 'Demanda hídrica alta, solos argilosos e clima quente.' },
  watermelon: { namePt: 'Melancia', category: 'Frutas', description: 'Solos leves com alto teor de matéria orgânica e sol pleno.' },
};

// --- Notícias de colheita (GET /news) -------------------------------------------

export type NewsSourceFeed =
  | 'g1_estadual'
  | 'g1_agro'
  | 'canal_rural'
  | 'portal_agronegocio'
  | 'globo_rural'
  | 'compre_rural';

/**
 * city = cita a cidade · state = cita o estado/UF · inferred = feed regional sem menção explícita ·
 * outside = cita a cultura pedida, mas não a região
 */
export type NewsLocationMatch = 'city' | 'state' | 'inferred' | 'outside';

export interface NewsLocation {
  city: string;
  state?: string | null;
  uf?: string | null;
}

/** Cultura do modelo usada para priorizar as notícias (parâmetro `crop`). */
export interface NewsCrop {
  id: string;
  name: string;
  terms: string[];
}

export interface NewsArticle {
  id: string;
  title: string;
  /** Texto puro (≤ 500 caracteres). Renderizar como texto, nunca como HTML. */
  summary?: string | null;
  url: string;
  source_name: string;
  source_feed: NewsSourceFeed;
  published_at?: string | null;
  image_url?: string | null;
  location_match: NewsLocationMatch;
  matched_keywords: string[];
  /** A notícia cita a cultura recomendada pelo modelo. */
  crop_match: boolean;
  relevance_score: number;
}

export interface SourceStatus {
  source: NewsSourceFeed;
  ok: boolean;
  items_fetched: number;
  items_kept: number;
  cached: boolean;
  error?: string | null;
}

export interface NewsResponse {
  location: NewsLocation;
  generated_at: string;
  cached: boolean;
  total: number;
  crop?: NewsCrop | null;
  articles: NewsArticle[];
  sources: SourceStatus[];
}

export interface NewsQuery {
  city: string;
  /** UF (ex.: "SP"); vazio = resolvido pela geocodificação. */
  state?: string;
  days?: number;
  limit?: number;
  /** Classe do modelo (ex.: "maize"). */
  crop?: string;
}

// --- Recomendação cruzada (POST /ai/cross-recommendation) -----------------------

export interface CrossRecommendationInput {
  city: string;
  state?: string;
  n: number;
  p: number;
  k: number;
  temperature: number;
  humidity: number;
  rainfall: number;
}

/**
 * news = cita a cultura na região · alert = idem, com termo de risco ·
 * generic_news = só cita o termo geral ("feijão") · no_news = nada na região ·
 * unavailable = a busca de notícias falhou
 */
export type CrossCandidateStatus = 'news' | 'alert' | 'generic_news' | 'no_news' | 'unavailable';

export interface CrossAlert {
  article_id: string;
  title: string;
  terms: string[];
}

/** Do ponto de vista de quem produz: preço em alta é positivo, custo em alta é negativo. */
export type ArticleSentiment = 'positive' | 'negative' | 'mixed' | 'neutral';
export type OutlookSentiment = ArticleSentiment | 'no_news' | 'unavailable';

export interface ClassifiedArticle {
  article_id: string;
  title: string;
  /** Fala da região pedida. */
  regional: boolean;
  sentiment: ArticleSentiment;
  /** Palavras que decidiram o sentimento. */
  signals: string[];
  /** IA ou regras locais. */
  classified_by: 'llm' | 'rules';
}

/** O que o classificador leu nas notícias de uma cultura. */
export interface CropOutlook {
  sentiment: OutlookSentiment;
  /** De onde veio a leitura: a região tem prioridade. */
  scope?: 'region' | 'other_regions' | null;
  positive: number;
  negative: number;
  neutral: number;
  text: string;
  /** Só as notícias que são mesmo da cultura. */
  articles: ClassifiedArticle[];
}

export interface CrossCandidate {
  crop: string;
  name: string;
  /** Probabilidade do modelo, em %. */
  probability: number;
  /** Posição na ordem do modelo (1 = primeira). */
  model_rank: number;
  regional_news: number;
  status: CrossCandidateStatus;
  summary: string;
  alerts: CrossAlert[];
  outlook: CropOutlook;
  news?: NewsResponse | null;
}

/** Junta a predição do modelo com a leitura das notícias. */
export interface CrossReport {
  conclusion: string;
  /** Quem escreveu a conclusão. */
  conclusion_by: 'llm' | 'rules';
  /** Modelo de IA usado nesta consulta, se algum respondeu. */
  model?: string | null;
  caveat: string;
}

export interface CitedCrop {
  crop: string;
  name: string;
  mentions: number;
  probability: number;
}

export interface CrossRecommendationOutput {
  model_recommendation: string;
  recommendation: string;
  /** As notícias mudaram a primeira colocada. */
  changed: boolean;
  explanation: string;
  report: CrossReport;
  /** As até 3 primeiras do modelo, na ordem final. */
  candidates: CrossCandidate[];
  also_cited: CitedCrop[];
}
