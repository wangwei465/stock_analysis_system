import client from './client'
import type { AllIndicators, MAData, MACDData, RSIData, KDJData, BOLLData } from '../types/stock'

export async function getMA(
  code: string,
  periods: string = '5,10,20,60',
  startDate?: string,
  endDate?: string
): Promise<MAData> {
  const response = await client.get<MAData>(`/indicators/${code}/ma`, {
    params: { periods, start_date: startDate, end_date: endDate }
  })
  return response.data
}

export async function getMACD(
  code: string,
  fast: number = 12,
  slow: number = 26,
  signal: number = 9,
  startDate?: string,
  endDate?: string
): Promise<MACDData> {
  const response = await client.get<MACDData>(`/indicators/${code}/macd`, {
    params: { fast, slow, signal, start_date: startDate, end_date: endDate }
  })
  return response.data
}

export async function getRSI(
  code: string,
  period: number = 14,
  startDate?: string,
  endDate?: string
): Promise<RSIData> {
  const response = await client.get<RSIData>(`/indicators/${code}/rsi`, {
    params: { period, start_date: startDate, end_date: endDate }
  })
  return response.data
}

export async function getKDJ(
  code: string,
  n: number = 9,
  m1: number = 3,
  m2: number = 3,
  startDate?: string,
  endDate?: string
): Promise<KDJData> {
  const response = await client.get<KDJData>(`/indicators/${code}/kdj`, {
    params: { n, m1, m2, start_date: startDate, end_date: endDate }
  })
  return response.data
}

export async function getBOLL(
  code: string,
  period: number = 20,
  std: number = 2,
  startDate?: string,
  endDate?: string
): Promise<BOLLData> {
  const response = await client.get<BOLLData>(`/indicators/${code}/boll`, {
    params: { period, std, start_date: startDate, end_date: endDate }
  })
  return response.data
}

export async function getAllIndicators(
  code: string,
  maPeriods: string = '5,10,20,60',
  klinePeriod: string = 'day',
  startDate?: string,
  endDate?: string
): Promise<AllIndicators> {
  const response = await client.get<AllIndicators>(`/indicators/${code}/all`, {
    params: { ma_periods: maPeriods, kline_period: klinePeriod, start_date: startDate, end_date: endDate }
  })
  return response.data
}
