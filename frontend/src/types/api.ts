export interface PrevisionInput {
  city: string;
  n_ratio: number;
  p_ratio: number;
  k_ratio: number;
  ph: number;
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
  latitude?: number;
  longitude?: number;
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  wind_direction?: number;
  precipitation?: number;
  temperature_forecast?: number;
  preciptation_forecast?: number;
  rain_forecast?: number;
  time?: string;
}

export interface PrevisionOutput {
  crop_recomendation: string;
  confidence?: number;
  city?: string;
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
  inputs: {
    n: number;
    p: number;
    k: number;
    ph: number;
  };
  result: PrevisionOutput;
}

export interface CropInfo {
  id: string;
  namePt: string;
  category: 'Frutas' | 'Grãos' | 'Leguminosas' | 'Fibras' | 'Comercial';
  idealN: [number, number];
  idealP: [number, number];
  idealK: [number, number];
  idealTemp: [number, number];
  idealHumidity: [number, number];
  idealRain: [number, number];
  description: string;
}

export const CROP_DICTIONARY: Record<string, { namePt: string; category: CropInfo['category']; description: string }> = {
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
