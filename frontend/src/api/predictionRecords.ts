import client from './client'

export type AccuracyStatus = 'unknown' | 'accurate' | 'inaccurate'

export interface PredictionRecord {
  id: number
  stock_name: string
  stock_code: string
  forward_days: number
  current_price: number | null
  direction: string
  signal: string
  recommendation: string
  expected_price: number | null
  support: number | null
  resistance: number | null
  prediction_date: string
  accuracy: AccuracyStatus
  created_at: string
}

export interface PredictionRecordCreate {
  stock_name: string
  stock_code: string
  forward_days: number
  current_price: number | null
  direction: string
  signal: string
  recommendation: string
  expected_price: number | null
  support: number | null
  resistance: number | null
  prediction_date: string
  accuracy?: AccuracyStatus
}

export interface PredictionRecordUpdate {
  accuracy: AccuracyStatus
}

export async function listPredictionRecords(limit: number = 200): Promise<PredictionRecord[]> {
  const response = await client.get<PredictionRecord[]>('/prediction-records', {
    params: { limit }
  })
  return response.data
}

export async function createPredictionRecord(payload: PredictionRecordCreate): Promise<PredictionRecord> {
  const response = await client.post<PredictionRecord>('/prediction-records', payload)
  return response.data
}

export async function updatePredictionRecord(
  recordId: number,
  payload: PredictionRecordUpdate
): Promise<PredictionRecord> {
  const response = await client.patch<PredictionRecord>(`/prediction-records/${recordId}`, payload)
  return response.data
}

export async function deletePredictionRecord(recordId: number) {
  const response = await client.delete(`/prediction-records/${recordId}`)
  return response.data
}
