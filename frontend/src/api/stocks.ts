import client from './client'
import type {
  StockInfo,
  KlineResponse,
  StockQuote,
  StockSearchResult,
  IntradayResponse
} from '../types/stock'

export async function searchStocks(keyword: string): Promise<StockSearchResult[]> {
  const response = await client.get<StockSearchResult[]>('/stocks/search', {
    params: { q: keyword }
  })
  return response.data
}

export async function getStockInfo(code: string): Promise<StockInfo> {
  const response = await client.get<StockInfo>(`/stocks/${code}`)
  return response.data
}

export async function getKline(
  code: string,
  period: 'day' | 'week' | 'month' = 'day',
  startDate?: string,
  endDate?: string,
  adjust: 'qfq' | 'hfq' | 'none' = 'qfq'
): Promise<KlineResponse> {
  const response = await client.get<KlineResponse>(`/stocks/${code}/kline`, {
    params: {
      period,
      start_date: startDate,
      end_date: endDate,
      adjust
    }
  })
  return response.data
}

export async function getRealtimeQuote(code: string): Promise<StockQuote> {
  const response = await client.get<StockQuote>(`/stocks/${code}/quote`)
  return response.data
}

export async function getStockList(limit: number = 100): Promise<StockSearchResult[]> {
  const response = await client.get<StockSearchResult[]>('/stocks/', {
    params: { limit }
  })
  return response.data
}

export async function getIntradayData(code: string): Promise<IntradayResponse> {
  const response = await client.get<IntradayResponse>(`/stocks/${code}/intraday`)
  return response.data
}
