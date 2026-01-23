import { useEffect, useRef, useState, useCallback } from 'react'
import type { IntradayData } from '../types/stock'

interface IntradayWebSocketMessage {
  type: 'init' | 'update'
  code: string
  name?: string
  pre_close: number
  data: IntradayData[] | IntradayData
  timestamp: string
}

interface UseIntradayWebSocketReturn {
  data: IntradayData[]
  preClose: number
  isConnected: boolean
  error: string | null
  reconnect: () => void
}

export function useIntradayWebSocket(code: string | undefined): UseIntradayWebSocketReturn {
  const [data, setData] = useState<IntradayData[]>([])
  const [preClose, setPreClose] = useState<number>(0)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const shouldReconnectRef = useRef(true)

  // 清理函数
  const cleanup = useCallback(() => {
    shouldReconnectRef.current = false

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Intentional close')
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const connect = useCallback(() => {
    if (!code) {
      // code 为空时，清理连接并重置数据
      cleanup()
      setData([])
      setPreClose(0)
      return
    }

    shouldReconnectRef.current = true

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'Reconnecting')
      wsRef.current = null
    }

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/ws/intraday/${code}`

    console.log(`[WebSocket] Connecting to ${wsUrl}`)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[WebSocket] Connected')
      setIsConnected(true)
      setError(null)

      // Start ping interval
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 25000)
    }

    ws.onmessage = (event) => {
      try {
        // Handle pong
        if (event.data === 'pong' || event.data === 'ping') {
          if (event.data === 'ping' && ws.readyState === WebSocket.OPEN) {
            ws.send('pong')
          }
          return
        }

        const message: IntradayWebSocketMessage = JSON.parse(event.data)

        if (message.type === 'init') {
          // Initial data - replace all
          console.log(`[WebSocket] Received init data: ${(message.data as IntradayData[]).length} points`)
          setData(message.data as IntradayData[])
          setPreClose(message.pre_close)
        } else if (message.type === 'update') {
          // Update - append new data point
          const newPoint = message.data as IntradayData
          console.log(`[WebSocket] Received update: ${newPoint.time}`)
          setData(prev => {
            // Check if this point already exists
            const exists = prev.some(p => p.time === newPoint.time)
            if (exists) {
              // Update existing point
              return prev.map(p => p.time === newPoint.time ? newPoint : p)
            } else {
              // Append new point
              return [...prev, newPoint]
            }
          })
          setPreClose(message.pre_close)
        }
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
      }
    }

    ws.onerror = (event) => {
      console.error('[WebSocket] Error:', event)
      setError('WebSocket connection error')
    }

    ws.onclose = (event) => {
      console.log(`[WebSocket] Closed: ${event.code} ${event.reason}`)
      setIsConnected(false)

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }

      // Reconnect after 5 seconds if not intentionally closed and should reconnect
      if (event.code !== 1000 && shouldReconnectRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WebSocket] Reconnecting...')
          connect()
        }, 5000)
      }
    }
  }, [code, cleanup])

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    connect()
  }, [connect])

  // 当 code 变化时连接/断开
  useEffect(() => {
    connect()

    return () => {
      cleanup()
    }
  }, [code]) // 只依赖 code，不依赖 connect

  return { data, preClose, isConnected, error, reconnect }
}
