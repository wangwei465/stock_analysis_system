import client from './client'

// Direction Prediction
export interface DirectionPrediction {
  direction: number
  direction_label: string
  confidence: number
  score: number
  signals: Record<string, string>
}

// Price Range Prediction
export interface PriceRange {
  confidence: number
  lower: number
  upper: number
  range_pct: number
}

export interface PriceRangePrediction {
  current_price: number
  forward_days: number
  volatility: {
    daily: number
    annualized: number
    forward_period: number
  }
  price_ranges: PriceRange[]
  expected: {
    price: number
    return_pct: number
  }
  support_resistance: {
    resistance: number
    support: number
    atr_14: number
  }
  risk_assessment: {
    atr_pct: number
    volatility_level: string
  }
}

// Trading Signal
export interface TradingSignal {
  signal: number
  signal_label: string
  confidence: number
  score: number
  reasons: string[]
  entry_price: number
  stop_loss: number | null
  take_profit: number | null
  risk_reward_ratio: number | null
  atr: number
  components: Record<string, { score: number; reasons: string[] }>
  risk_tolerance: string
  holding_period: number
}

// Sentiment Analysis
export interface SentimentResult {
  score: number
  label: string
  level: number
  positive_words: string[]
  negative_words: string[]
}

export interface NewsItem {
  title: string
  source: string
  publish_time: string
  sentiment: SentimentResult
}

export interface SentimentSummary {
  stock_code: string
  stock_sentiment: {
    score: number
    label: string
    news_count: number
  }
  market_sentiment: {
    score: number
    label: string
    news_count: number
  }
  combined: {
    score: number
    label: string
    color: string
  }
  recommendation: string
  top_news: NewsItem[]
}

// Comprehensive Prediction
export interface ComprehensivePrediction {
  stock_code: string
  stock_name: string
  forward_days: number
  prediction_date: string
  stock_info: {
    current_price: number
    date: string
  }
  direction: DirectionPrediction
  price_range: PriceRangePrediction
  signal: TradingSignal
  sentiment?: SentimentSummary
  risk: {
    daily_volatility: number
    annualized_volatility: number
    max_drawdown_20d: number
    var_95: number
    cvar_95: number
  }
  recommendation: {
    action: string
    risk_level: string
    score: number
    summary: string
  }
}

// API Functions
export async function getDirectionPrediction(code: string, days: number = 5) {
  const response = await client.get(`/ml/direction/${code}`, {
    params: { days }
  })
  return response.data
}

export async function getPriceRangePrediction(code: string, days: number = 5) {
  const response = await client.get(`/ml/price-range/${code}`, {
    params: { days }
  })
  return response.data
}

export async function getPriceTargetPrediction(code: string, days: number = 20) {
  const response = await client.get(`/ml/price-target/${code}`, {
    params: { days }
  })
  return response.data
}

export async function getTradingSignal(
  code: string,
  riskTolerance: string = 'moderate',
  holdingPeriod: number = 5
) {
  const response = await client.get(`/ml/signal/${code}`, {
    params: {
      risk_tolerance: riskTolerance,
      holding_period: holdingPeriod
    }
  })
  return response.data
}

export async function getComprehensivePrediction(
  code: string,
  forwardDays: number = 5,
  includeSentiment: boolean = true
): Promise<ComprehensivePrediction> {
  const response = await client.get<ComprehensivePrediction>(`/ml/comprehensive/${code}`, {
    params: {
      forward_days: forwardDays,
      include_sentiment: includeSentiment
    }
  })
  return response.data
}

export async function getSentimentAnalysis(code: string, limit: number = 20): Promise<SentimentSummary> {
  const response = await client.get<SentimentSummary>(`/ml/sentiment/${code}`, {
    params: { limit }
  })
  return response.data
}

export async function getMarketSentiment(limit: number = 30) {
  const response = await client.get('/ml/sentiment/market', {
    params: { limit }
  })
  return response.data
}

export interface BatchPredictionResult {
  stock_code: string
  stock_name?: string
  current_price?: number
  direction?: string
  direction_confidence?: number
  signal?: string
  signal_confidence?: number
  status: 'success' | 'error'
  message?: string
}

export async function batchPredict(stockCodes: string[], forwardDays: number = 5) {
  const response = await client.post<{
    forward_days: number
    results: BatchPredictionResult[]
    success_count: number
    error_count: number
  }>('/ml/batch-predict', stockCodes, {
    params: { forward_days: forwardDays }
  })
  return response.data
}
