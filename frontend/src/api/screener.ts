import client from './client'

export interface ScreenerCondition {
  field: string
  operator: string
  value: number | number[] | string[]
}

export interface ScreenerRequest {
  conditions: ScreenerCondition[]
  sort_by?: string
  sort_order?: string
  page?: number
  page_size?: number
  market_boards?: string[]
  exclude_boards?: string[]
}

export interface ScreenerResult {
  code: string
  name: string
  board: string
  price: number | null
  change_pct: number | null
  pe: number | null
  pb: number | null
  market_cap: number | null
  circulating_cap: number | null
  turnover_rate: number | null
  volume_ratio: number | null
  amplitude: number | null
}

export interface ScreenerResponse {
  total: number
  page: number
  page_size: number
  data: ScreenerResult[]
}

export interface ScreenerPreset {
  name: string
  description: string
  conditions: ScreenerCondition[]
  market_boards?: string[]
  exclude_boards?: string[]
}

export interface ScreenerField {
  field: string
  name: string
  type: string
  unit: string
}

export interface MarketBoard {
  key: string
  name: string
  description: string
}

export async function filterStocks(request: ScreenerRequest): Promise<ScreenerResponse> {
  const response = await client.post<ScreenerResponse>('/screener/filter', request)
  return response.data
}

export async function getPresets(): Promise<ScreenerPreset[]> {
  const response = await client.get<ScreenerPreset[]>('/screener/presets')
  return response.data
}

export async function getScreenerFields(): Promise<ScreenerField[]> {
  const response = await client.get<ScreenerField[]>('/screener/fields')
  return response.data
}

export async function getMarketBoards(): Promise<MarketBoard[]> {
  const response = await client.get<MarketBoard[]>('/screener/boards')
  return response.data
}
