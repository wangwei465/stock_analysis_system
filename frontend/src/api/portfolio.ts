import client from './client'

export interface Portfolio {
  id: number
  name: string
  description: string | null
  initial_capital: number
  created_at: string
  updated_at: string
}

export interface Position {
  id: number
  portfolio_id: number
  code: string
  name: string
  quantity: number
  avg_cost: number
  buy_date: string | null
  notes: string | null
  created_at: string
}

export interface PositionDetail extends Position {
  current_price: number
  pre_close: number
  cost: number
  value: number
  pnl: number
  pnl_pct: number
  daily_pnl: number
  daily_pnl_pct: number
  weight: number
}

export interface PortfolioPerformance {
  portfolio_id: number
  name: string
  initial_capital: number
  total_cost: number
  total_value: number
  total_pnl: number
  total_pnl_pct: number
  cash: number
  positions: PositionDetail[]
}

export interface CreatePortfolioRequest {
  name: string
  description?: string
  initial_capital?: number
}

export interface CreatePositionRequest {
  code: string
  name: string
  quantity: number
  avg_cost: number
  buy_date?: string
  notes?: string
}

export async function getPortfolios(): Promise<Portfolio[]> {
  const response = await client.get<Portfolio[]>('/portfolios/')
  return response.data
}

export async function createPortfolio(data: CreatePortfolioRequest): Promise<Portfolio> {
  const response = await client.post<Portfolio>('/portfolios/', data)
  return response.data
}

export async function getPortfolio(id: number): Promise<{ portfolio: Portfolio; positions: Position[] }> {
  const response = await client.get(`/portfolios/${id}`)
  return response.data
}

export async function updatePortfolio(id: number, data: Partial<CreatePortfolioRequest>): Promise<Portfolio> {
  const response = await client.put<Portfolio>(`/portfolios/${id}`, data)
  return response.data
}

export async function deletePortfolio(id: number): Promise<void> {
  await client.delete(`/portfolios/${id}`)
}

export async function addPosition(portfolioId: number, data: CreatePositionRequest): Promise<Position> {
  const response = await client.post<Position>(`/portfolios/${portfolioId}/positions`, data)
  return response.data
}

export async function updatePosition(portfolioId: number, positionId: number, data: Partial<CreatePositionRequest>): Promise<Position> {
  const response = await client.put<Position>(`/portfolios/${portfolioId}/positions/${positionId}`, data)
  return response.data
}

export async function deletePosition(portfolioId: number, positionId: number): Promise<void> {
  await client.delete(`/portfolios/${portfolioId}/positions/${positionId}`)
}

export async function getPortfolioPerformance(id: number): Promise<PortfolioPerformance> {
  const response = await client.get<PortfolioPerformance>(`/portfolios/${id}/performance`)
  return response.data
}

export interface PortfolioSummary {
  portfolio_count: number
  position_count: number
  total_initial_capital: number
  total_cost: number
  total_value: number
  total_pnl: number
  total_pnl_pct: number
  daily_pnl: number
  daily_pnl_pct: number
  total_cash: number
  position_ratio: number
  portfolios: {
    id: number
    name: string
    total_value: number
    total_pnl: number
    total_pnl_pct: number
    daily_pnl: number
    daily_pnl_pct: number
  }[]
}

export async function getPortfoliosSummary(): Promise<PortfolioSummary> {
  const response = await client.get<PortfolioSummary>('/portfolios/summary/all')
  return response.data
}

// Transaction types
export interface Transaction {
  id: number
  portfolio_id: number
  code: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  price: number
  commission: number
  trade_date: string
  created_at: string
}

export interface CreateTransactionRequest {
  code: string
  name?: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  price: number
  commission?: number
  trade_date?: string
}

export interface ImportResult {
  imported: number
  errors: string[]
  total_errors: number
}

export async function getTransactions(portfolioId: number, limit = 50): Promise<Transaction[]> {
  const response = await client.get<Transaction[]>(`/portfolios/${portfolioId}/transactions`, {
    params: { limit }
  })
  return response.data
}

export async function createTransaction(portfolioId: number, data: CreateTransactionRequest): Promise<Transaction> {
  const response = await client.post<Transaction>(`/portfolios/${portfolioId}/transactions`, data)
  return response.data
}

export async function deleteTransaction(portfolioId: number, transactionId: number): Promise<void> {
  await client.delete(`/portfolios/${portfolioId}/transactions/${transactionId}`)
}

export async function importTransactions(portfolioId: number, file: File): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await client.post<ImportResult>(`/portfolios/${portfolioId}/transactions/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}
