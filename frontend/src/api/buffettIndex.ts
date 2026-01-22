/**
 * 巴菲特指标API客户端
 */
import client from './client'

export interface BuffettIndexData {
  日期: string
  收盘价: number
  总市值: number
  GDP: number
  近十年分位数: number
  总历史分位数: number
  总市值GDP比: number
}

export interface BuffettIndexStats {
  total_records: number
  date_range: {
    start: string
    end: string
  }
  buffett_ratio: {
    current: number
    max: number
    min: number
    avg: number
  }
  percentile_10y: {
    current: number
  }
  percentile_all: {
    current: number
  }
  market_cap: {
    current: number
  }
  gdp: {
    current: number
  }
  close_price: {
    current: number
  }
}

/**
 * 获取巴菲特指标历史数据
 */
export const getBuffettIndexData = async (): Promise<BuffettIndexData[]> => {
  const response = await client.get('/buffett-index/data')
  return response.data
}

/**
 * 获取最新的巴菲特指标数据
 */
export const getLatestBuffettIndex = async (): Promise<BuffettIndexData> => {
  const response = await client.get('/buffett-index/latest')
  return response.data
}

/**
 * 获取巴菲特指标统计信息
 */
export const getBuffettIndexStats = async (): Promise<BuffettIndexStats> => {
  const response = await client.get('/buffett-index/stats')
  return response.data
}
