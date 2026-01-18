import client from './client'

export interface StrategyParam {
  name: string
  type: string
  default: number
  min: number
  max: number
  description: string
}

export interface Strategy {
  id: string
  name: string
  description: string
  params: StrategyParam[]
}

export interface BacktestRequest {
  strategy: string
  stock_code: string
  params?: Record<string, number>
  start_date?: string
  end_date?: string
  initial_capital?: number
  commission?: number
  slippage?: number
}

export interface TradeRecord {
  entry_date: string
  entry_price: number
  exit_date: string
  exit_price: number
  shares: number
  direction: string
  pnl: number
  pnl_pct: number
  holding_days: number
}

export interface EquityPoint {
  date: string
  equity: number
  cash: number
  position_value: number
  close: number
}

export interface BacktestMetrics {
  initial_capital: number
  final_capital: number
  total_return: number
  annualized_return: number
  max_drawdown: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  volatility: number
  trade_count: number
  win_rate: number
  profit_factor: number
  avg_trade_pnl: number
  avg_win: number
  avg_loss: number
  avg_holding_days: number
  trading_days: number
}

export interface BacktestResult {
  id?: number
  stock: {
    code: string
    name: string
  }
  strategy: {
    id: string
    name: string
    params: Record<string, number>
  }
  period: {
    start: string
    end: string
  }
  config: {
    initial_capital: number
    commission: number
    slippage: number
  }
  metrics: BacktestMetrics
  equity_curve: EquityPoint[]
  trades: TradeRecord[]
}

export interface BacktestHistoryItem {
  id: number
  strategy_name: string
  stock_code: string
  stock_name: string
  period: string
  total_return: number
  annualized_return: number
  max_drawdown: number
  sharpe_ratio: number
  win_rate: number
  trade_count: number
  created_at: string
}

export async function getStrategies(): Promise<Strategy[]> {
  const response = await client.get<Strategy[]>('/backtest/strategies')
  return response.data
}

export async function runBacktest(request: BacktestRequest): Promise<BacktestResult> {
  const response = await client.post<BacktestResult>('/backtest/run', request)
  return response.data
}

export async function getBacktestResult(id: number): Promise<BacktestResult> {
  const response = await client.get<BacktestResult>(`/backtest/results/${id}`)
  return response.data
}

export async function getBacktestHistory(
  limit: number = 20,
  strategy?: string,
  stockCode?: string
): Promise<BacktestHistoryItem[]> {
  const response = await client.get<BacktestHistoryItem[]>('/backtest/history', {
    params: { limit, strategy, stock_code: stockCode }
  })
  return response.data
}

export async function deleteBacktestResult(id: number): Promise<void> {
  await client.delete(`/backtest/results/${id}`)
}
