import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  ColorType,
  CrosshairMode,
  MouseEventParams,
  LogicalRange,
} from 'lightweight-charts'
import type { KlineData, IndicatorData } from '../../types/stock'

// 导出时间范围类型供其他组件使用
export interface TimeRange {
  from: number
  to: number
}

interface KLineChartProps {
  data: KlineData[]
  ma?: Record<string, IndicatorData[]>
  boll?: {
    upper: IndicatorData[]
    middle: IndicatorData[]
    lower: IndicatorData[]
  }
  height?: number
  showVolume?: boolean
  stockName?: string
  defaultBars?: number  // 默认显示的K线数量
  onVisibleRangeChange?: (range: TimeRange | null) => void  // 可见范围变化回调
}

// 悬浮信息数据
interface TooltipData {
  time: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount?: number
  turnover?: number
  change: number
  changePct: number
  amplitude: number
  ma5?: number
  ma10?: number
  ma20?: number
  ma60?: number
}

// MA line colors
const MA_COLORS: Record<string, string> = {
  ma5: '#f6c85c',
  ma10: '#6b93d6',
  ma20: '#d66b9a',
  ma60: '#50c878',
}

// BOLL colors
const BOLL_COLORS = {
  upper: '#ff6b6b',
  middle: '#f6c85c',
  lower: '#4ecdc4',
}

// 格式化数字
const formatNumber = (num: number, precision = 2): string => {
  if (num === null || num === undefined || isNaN(num)) return '-'
  return num.toFixed(precision)
}

// 格式化成交量
const formatVolume = (vol: number): string => {
  if (vol >= 100000000) {
    return (vol / 100000000).toFixed(2) + '亿'
  } else if (vol >= 10000) {
    return (vol / 10000).toFixed(2) + '万'
  }
  return vol.toFixed(0)
}

// 格式化成交额
const formatAmount = (amount: number): string => {
  if (amount >= 100000000) {
    return (amount / 100000000).toFixed(2) + '亿'
  } else if (amount >= 10000) {
    return (amount / 10000).toFixed(2) + '万'
  }
  return amount.toFixed(2)
}

export default function KLineChart({
  data,
  ma,
  boll,
  height = 500,
  showVolume = true,
  stockName = '',
  defaultBars = 80,
  onVisibleRangeChange,
}: KLineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const maSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const bollSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const dataMapRef = useRef<Map<string, KlineData>>(new Map())
  const isInitializedRef = useRef(false)

  // 悬浮信息状态
  const [tooltipData, setTooltipData] = useState<TooltipData | null>(null)

  // 构建数据映射以便快速查找
  useEffect(() => {
    const map = new Map<string, KlineData>()
    data.forEach((d, index) => {
      map.set(d.time, { ...d, _index: index } as any)
    })
    dataMapRef.current = map
  }, [data])

  // 当 defaultBars 变化时（切换周期），重置初始化标志
  useEffect(() => {
    isInitializedRef.current = false
  }, [defaultBars])

  // 获取MA值
  const getMaValue = useCallback((time: string, maKey: string): number | undefined => {
    if (!ma || !ma[maKey]) return undefined
    const maData = ma[maKey].find(d => d.time === time)
    return maData?.value
  }, [ma])

  // 处理十字光标移动
  const handleCrosshairMove = useCallback((param: MouseEventParams) => {
    if (!param.time || !param.point) {
      // 鼠标离开图表，显示最后一根K线数据
      if (data.length > 0) {
        const lastData = data[data.length - 1]
        const prevClose = data.length > 1 ? data[data.length - 2].close : lastData.open
        const change = lastData.close - prevClose
        const changePct = (change / prevClose) * 100
        const amplitude = ((lastData.high - lastData.low) / prevClose) * 100

        setTooltipData({
          time: lastData.time,
          open: lastData.open,
          close: lastData.close,
          high: lastData.high,
          low: lastData.low,
          volume: lastData.volume,
          amount: lastData.amount,
          turnover: lastData.turnover,
          change,
          changePct,
          amplitude,
          ma5: getMaValue(lastData.time, 'ma5'),
          ma10: getMaValue(lastData.time, 'ma10'),
          ma20: getMaValue(lastData.time, 'ma20'),
          ma60: getMaValue(lastData.time, 'ma60'),
        })
      }
      return
    }

    const timeStr = param.time as string
    const currentData = dataMapRef.current.get(timeStr)

    if (currentData) {
      // 找到前一根K线
      const dataIndex = data.findIndex(d => d.time === timeStr)
      const prevClose = dataIndex > 0 ? data[dataIndex - 1].close : currentData.open

      const change = currentData.close - prevClose
      const changePct = (change / prevClose) * 100
      const amplitude = ((currentData.high - currentData.low) / prevClose) * 100

      setTooltipData({
        time: currentData.time,
        open: currentData.open,
        close: currentData.close,
        high: currentData.high,
        low: currentData.low,
        volume: currentData.volume,
        amount: currentData.amount,
        turnover: currentData.turnover,
        change,
        changePct,
        amplitude,
        ma5: getMaValue(timeStr, 'ma5'),
        ma10: getMaValue(timeStr, 'ma10'),
        ma20: getMaValue(timeStr, 'ma20'),
        ma60: getMaValue(timeStr, 'ma60'),
      })
    }
  }, [data, getMaValue])

  // 处理可见范围变化
  const handleVisibleLogicalRangeChange = useCallback((logicalRange: LogicalRange | null) => {
    if (logicalRange && onVisibleRangeChange) {
      onVisibleRangeChange({
        from: logicalRange.from,
        to: logicalRange.to,
      })
    }
  }, [onVisibleRangeChange])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height - 60, // 为顶部信息栏留出空间
      layout: {
        background: { type: ColorType.Solid, color: '#141414' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
        scaleMargins: {
          top: 0.1,
          bottom: showVolume ? 0.2 : 0.1,
        },
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: false,
        secondsVisible: false,
        tickMarkFormatter: (time: string | number) => {
          // time 可能是字符串 "YYYY-MM-DD" 或时间戳
          if (typeof time === 'string') {
            return time  // 已经是 YYYY-MM-DD 格式
          }
          const date = new Date(time * 1000)
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        },
      },
      localization: {
        timeFormatter: (time: string | number) => {
          if (typeof time === 'string') {
            return time
          }
          const date = new Date(time * 1000)
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        },
      },
    })

    // Candlestick series - Chinese market: red up, green down
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#10b981',
      borderVisible: false,
      wickUpColor: '#ef4444',
      wickDownColor: '#10b981',
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries

    // Volume series
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#10b981',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      })

      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.85,
          bottom: 0,
        },
      })

      volumeSeriesRef.current = volumeSeries
    }

    // 订阅十字光标移动事件
    chart.subscribeCrosshairMove(handleCrosshairMove)

    // 订阅可见范围变化事件
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange)

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange)
      chart.remove()
      isInitializedRef.current = false
    }
  }, [height, showVolume, handleCrosshairMove, handleVisibleLogicalRangeChange])

  // Update data
  useEffect(() => {
    if (!candleSeriesRef.current || !data.length) return

    // Format candlestick data
    const candleData: CandlestickData[] = data.map((d) => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))

    candleSeriesRef.current.setData(candleData)

    // Volume data with colors
    if (volumeSeriesRef.current) {
      const volumeData = data.map((d, i) => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.5)',
      }))
      volumeSeriesRef.current.setData(volumeData)
    }

    // 设置默认可见范围（最近N根K线，右对齐）
    if (chartRef.current && !isInitializedRef.current) {
      const totalBars = data.length
      const visibleBars = Math.min(defaultBars, totalBars)

      if (totalBars <= visibleBars) {
        // K线不够，fitContent 填满整个区域
        chartRef.current.timeScale().fitContent()
      } else {
        // K线足够，显示最近N根，右对齐（右边留2根K线的小空间）
        const rightPadding = 2
        const from = totalBars - visibleBars
        const to = totalBars - 1 + rightPadding

        chartRef.current.timeScale().setVisibleLogicalRange({
          from: from,
          to: to,
        })
      }
      isInitializedRef.current = true
    }

    // 初始化显示最后一根K线数据
    if (data.length > 0) {
      const lastData = data[data.length - 1]
      const prevClose = data.length > 1 ? data[data.length - 2].close : lastData.open
      const change = lastData.close - prevClose
      const changePct = (change / prevClose) * 100
      const amplitude = ((lastData.high - lastData.low) / prevClose) * 100

      setTooltipData({
        time: lastData.time,
        open: lastData.open,
        close: lastData.close,
        high: lastData.high,
        low: lastData.low,
        volume: lastData.volume,
        amount: lastData.amount,
        turnover: lastData.turnover,
        change,
        changePct,
        amplitude,
        ma5: getMaValue(lastData.time, 'ma5'),
        ma10: getMaValue(lastData.time, 'ma10'),
        ma20: getMaValue(lastData.time, 'ma20'),
        ma60: getMaValue(lastData.time, 'ma60'),
      })
    }
  }, [data, getMaValue, defaultBars])

  // Update MA lines
  useEffect(() => {
    if (!chartRef.current || !ma) return

    // Remove old MA series (safely handle undefined)
    maSeriesRef.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series)
        } catch (e) {
          console.warn('Failed to remove MA series:', e)
        }
      }
    })
    maSeriesRef.current.clear()

    // Add new MA series
    Object.entries(ma).forEach(([key, values]) => {
      if (!chartRef.current || !values || !values.length) return

      const color = MA_COLORS[key] || '#ffffff'
      const series = chartRef.current.addLineSeries({
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      })

      const lineData: LineData[] = values.map((d) => ({
        time: d.time,
        value: d.value,
      }))

      series.setData(lineData)
      maSeriesRef.current.set(key, series)
    })
  }, [ma])

  // Update BOLL lines
  useEffect(() => {
    if (!chartRef.current || !boll) return

    // Remove old BOLL series (safely handle undefined)
    bollSeriesRef.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series)
        } catch (e) {
          console.warn('Failed to remove BOLL series:', e)
        }
      }
    })
    bollSeriesRef.current.clear()

    // Add BOLL series
    const bollLines: [string, IndicatorData[], string][] = [
      ['upper', boll.upper, BOLL_COLORS.upper],
      ['middle', boll.middle, BOLL_COLORS.middle],
      ['lower', boll.lower, BOLL_COLORS.lower],
    ]

    bollLines.forEach(([key, values, color]) => {
      if (!chartRef.current || !values || !values.length) return

      const series = chartRef.current.addLineSeries({
        color,
        lineWidth: 1,
        lineStyle: key === 'middle' ? 0 : 2, // Dashed for upper/lower
        priceLineVisible: false,
        lastValueVisible: false,
      })

      const lineData: LineData[] = values.map((d) => ({
        time: d.time,
        value: d.value,
      }))

      series.setData(lineData)
      bollSeriesRef.current.set(key, series)
    })
  }, [boll])

  // 计算涨跌颜色
  const isUp = tooltipData ? tooltipData.change >= 0 : true
  const priceColor = isUp ? '#ef4444' : '#10b981'

  return (
    <div className="chart-container" style={{ height, position: 'relative' }}>
      {/* 顶部信息栏 */}
      <div
        style={{
          height: 56,
          padding: '8px 12px',
          background: '#1a1a1a',
          borderBottom: '1px solid #2B2B43',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '8px 16px',
          fontSize: 12,
          color: '#d1d4dc',
        }}
      >
        {/* 股票名称和日期 */}
        {stockName && (
          <span style={{ fontWeight: 600, color: '#fff', marginRight: 8 }}>{stockName}</span>
        )}

        {tooltipData && (
          <>
            {/* 日期 */}
            <span style={{
              background: '#2a2a3a',
              padding: '2px 8px',
              borderRadius: 4,
              color: '#a0a0ff'
            }}>
              {tooltipData.time}
            </span>

            {/* OHLC 数据 */}
            <span>
              <span style={{ color: '#888' }}>开</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>{formatNumber(tooltipData.open)}</span>
            </span>
            <span>
              <span style={{ color: '#888' }}>收</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>{formatNumber(tooltipData.close)}</span>
            </span>
            <span>
              <span style={{ color: '#888' }}>高</span>
              <span style={{ color: '#ef4444', marginLeft: 4 }}>{formatNumber(tooltipData.high)}</span>
            </span>
            <span>
              <span style={{ color: '#888' }}>低</span>
              <span style={{ color: '#10b981', marginLeft: 4 }}>{formatNumber(tooltipData.low)}</span>
            </span>

            {/* 涨跌幅 */}
            <span>
              <span style={{ color: '#888' }}>涨跌幅</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.changePct)}%
              </span>
            </span>

            {/* 涨跌额 */}
            <span>
              <span style={{ color: '#888' }}>涨跌额</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.change)}
              </span>
            </span>

            {/* 成交量 */}
            <span>
              <span style={{ color: '#888' }}>成交量</span>
              <span style={{ color: '#fff', marginLeft: 4 }}>{formatVolume(tooltipData.volume)}</span>
            </span>

            {/* 成交额 */}
            {tooltipData.amount !== undefined && tooltipData.amount !== null && (
              <span>
                <span style={{ color: '#888' }}>成交额</span>
                <span style={{ color: '#fff', marginLeft: 4 }}>{formatAmount(tooltipData.amount)}</span>
              </span>
            )}

            {/* 换手率 */}
            {tooltipData.turnover !== undefined && tooltipData.turnover !== null && (
              <span>
                <span style={{ color: '#888' }}>换手率</span>
                <span style={{ color: '#fff', marginLeft: 4 }}>{formatNumber(tooltipData.turnover)}%</span>
              </span>
            )}

            {/* 振幅 */}
            <span>
              <span style={{ color: '#888' }}>振幅</span>
              <span style={{ color: '#fff', marginLeft: 4 }}>{formatNumber(tooltipData.amplitude)}%</span>
            </span>

            {/* MA 指标 */}
            {tooltipData.ma5 !== undefined && (
              <span>
                <span style={{ color: MA_COLORS.ma5 }}>MA5:</span>
                <span style={{ color: MA_COLORS.ma5, marginLeft: 2 }}>{formatNumber(tooltipData.ma5)}</span>
              </span>
            )}
            {tooltipData.ma10 !== undefined && (
              <span>
                <span style={{ color: MA_COLORS.ma10 }}>MA10:</span>
                <span style={{ color: MA_COLORS.ma10, marginLeft: 2 }}>{formatNumber(tooltipData.ma10)}</span>
              </span>
            )}
            {tooltipData.ma20 !== undefined && (
              <span>
                <span style={{ color: MA_COLORS.ma20 }}>MA20:</span>
                <span style={{ color: MA_COLORS.ma20, marginLeft: 2 }}>{formatNumber(tooltipData.ma20)}</span>
              </span>
            )}
            {tooltipData.ma60 !== undefined && (
              <span>
                <span style={{ color: MA_COLORS.ma60 }}>MA60:</span>
                <span style={{ color: MA_COLORS.ma60, marginLeft: 2 }}>{formatNumber(tooltipData.ma60)}</span>
              </span>
            )}
          </>
        )}
      </div>

      {/* 图表区域 */}
      <div ref={chartContainerRef} style={{ height: height - 60 }} />
    </div>
  )
}
