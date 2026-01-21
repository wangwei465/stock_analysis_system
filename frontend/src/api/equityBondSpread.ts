/**
 * 股债利差API客户端
 */
import client from './client'

export interface EquityBondSpreadData {
  日期: string
  沪深300指数: number
  股债利差: number
  股债利差均线: number
  股债利差标准差上界: number
  股债利差标准差下界: number
}

export interface EquityBondSpreadStats {
  total_records: number
  date_range: {
    start: string
    end: string
  }
  equity_bond_spread: {
    current: number
    max: number
    min: number
    avg: number
  }
  equity_bond_spread_ma: {
    current: number
    max: number
    min: number
    avg: number
  }
  hs300_index: {
    current: number
  }
}

/**
 * 获取股债利差历史数据
 */
export const getEquityBondSpreadData = async (): Promise<EquityBondSpreadData[]> => {
  const response = await client.get('/equity-bond-spread/data')
  return response.data
}

/**
 * 获取最新的股债利差数据
 */
export const getLatestEquityBondSpread = async (): Promise<EquityBondSpreadData> => {
  const response = await client.get('/equity-bond-spread/latest')
  return response.data
}

/**
 * 获取股债利差统计信息
 */
export const getEquityBondSpreadStats = async (): Promise<EquityBondSpreadStats> => {
  const response = await client.get('/equity-bond-spread/stats')
  return response.data
}
