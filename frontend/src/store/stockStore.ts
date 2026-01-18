import { create } from 'zustand'
import type { KlineData, StockInfo, AllIndicators } from '../types/stock'

interface StockState {
  // Current stock
  currentStock: StockInfo | null
  setCurrentStock: (stock: StockInfo | null) => void

  // K-line data
  klineData: KlineData[]
  setKlineData: (data: KlineData[]) => void

  // Period
  period: 'day' | 'week' | 'month'
  setPeriod: (period: 'day' | 'week' | 'month') => void

  // Indicators
  indicators: AllIndicators | null
  setIndicators: (indicators: AllIndicators | null) => void

  // Loading states
  loading: boolean
  setLoading: (loading: boolean) => void

  // Indicator visibility
  showMA: boolean
  showBOLL: boolean
  showMACD: boolean
  showRSI: boolean
  showKDJ: boolean
  toggleIndicator: (name: 'MA' | 'BOLL' | 'MACD' | 'RSI' | 'KDJ') => void
}

export const useStockStore = create<StockState>((set) => ({
  currentStock: null,
  setCurrentStock: (stock) => set({ currentStock: stock }),

  klineData: [],
  setKlineData: (data) => set({ klineData: data }),

  period: 'day',
  setPeriod: (period) => set({ period }),

  indicators: null,
  setIndicators: (indicators) => set({ indicators }),

  loading: false,
  setLoading: (loading) => set({ loading }),

  // Default indicator visibility
  showMA: true,
  showBOLL: false,
  showMACD: true,
  showRSI: false,
  showKDJ: false,

  toggleIndicator: (name) => {
    set((state) => {
      switch (name) {
        case 'MA':
          return { showMA: !state.showMA }
        case 'BOLL':
          return { showBOLL: !state.showBOLL }
        case 'MACD':
          return { showMACD: !state.showMACD }
        case 'RSI':
          return { showRSI: !state.showRSI }
        case 'KDJ':
          return { showKDJ: !state.showKDJ }
        default:
          return state
      }
    })
  },
}))
