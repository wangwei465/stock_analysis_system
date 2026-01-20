// Stock data types
export interface StockInfo {
  code: string
  name: string
  market?: string
  industry?: string
}

export interface KlineData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number  // 成交额
  turnover?: number  // 换手率
}

export interface KlineResponse {
  code: string
  name: string
  period: string
  data: KlineData[]
}

export interface StockQuote {
  code: string
  name: string
  price: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  pre_close: number
  volume: number
  amount: number
  time: string
}

export interface StockSearchResult {
  code: string
  name: string
  market: string
}

// Indicator types
export interface IndicatorData {
  time: string
  value: number
}

export interface MAData {
  ma5?: IndicatorData[]
  ma10?: IndicatorData[]
  ma20?: IndicatorData[]
  ma60?: IndicatorData[]
}

export interface MACDData {
  macd: IndicatorData[]
  signal: IndicatorData[]
  histogram: IndicatorData[]
}

export interface RSIData {
  rsi: IndicatorData[]
}

export interface KDJData {
  k: IndicatorData[]
  d: IndicatorData[]
  j: IndicatorData[]
}

export interface BOLLData {
  upper: IndicatorData[]
  middle: IndicatorData[]
  lower: IndicatorData[]
}

export interface AllIndicators {
  ma: Record<string, IndicatorData[]>
  macd: {
    macd: IndicatorData[]
    signal: IndicatorData[]
    histogram: IndicatorData[]
  }
  rsi: IndicatorData[]
  kdj: {
    k: IndicatorData[]
    d: IndicatorData[]
    j: IndicatorData[]
  }
  boll: {
    upper: IndicatorData[]
    middle: IndicatorData[]
    lower: IndicatorData[]
  }
}

// Intraday (分时) data types
export interface IntradayData {
  time: string
  price: number
  avg_price: number
  volume: number // hands
  amount: number
}

export interface IntradayResponse {
  code: string
  name: string
  pre_close: number
  data: IntradayData[]
}
