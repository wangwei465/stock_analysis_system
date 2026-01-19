import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  CrosshairMode,
  MouseEventParams,
  UTCTimestamp,
  PriceScaleMode,
} from 'lightweight-charts'
import type { IntradayData } from '../../types/stock'

interface IntradayChartProps {
  data: IntradayData[]
  preClose: number
  height?: number
  stockName?: string
}

interface TooltipData {
  time: string
  price: number
  avgPrice: number
  volume: number
  amount: number
  change: number
  changePct: number
}

const formatNumber = (num: number, precision = 2): string => {
  if (num === null || num === undefined || isNaN(num)) return '-'
  return num.toFixed(precision)
}

const formatVolume = (vol: number): string => {
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol.toFixed(0)
}

const formatAmount = (amount: number): string => {
  if (amount >= 100000000) return (amount / 100000000).toFixed(2) + '亿'
  if (amount >= 10000) return (amount / 10000).toFixed(2) + '万'
  return amount.toFixed(2)
}

// 获取今天的日期字符串
const getTodayDateStr = (): string => {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 从数据中提取日期，如果没有数据则使用今天
const getDateFromData = (data: IntradayData[]): string => {
  if (data.length > 0 && data[0].time.includes('-')) {
    return data[0].time.split(' ')[0]
  }
  return getTodayDateStr()
}

// 生成交易时间点（9:30-11:30, 13:00-15:00）
const generateTradingTimes = (dateStr: string): string[] => {
  const times: string[] = []
  // 上午 9:30 - 11:30
  for (let h = 9; h <= 11; h++) {
    const startMin = h === 9 ? 30 : 0
    const endMin = h === 11 ? 30 : 59
    for (let m = startMin; m <= endMin; m++) {
      times.push(`${dateStr} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
    }
  }
  // 下午 13:00 - 15:00
  for (let h = 13; h <= 15; h++) {
    const endMin = h === 15 ? 0 : 59
    for (let m = 0; m <= endMin; m++) {
      times.push(`${dateStr} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
    }
  }
  return times
}

// 将时间字符串转换为时间戳
const parseTimeToTimestamp = (timeStr: string): UTCTimestamp => {
  let date: Date
  if (timeStr.includes('-')) {
    const [datePart, timePart] = timeStr.split(' ')
    const [year, month, day] = datePart.split('-').map(Number)
    const [hours, minutes] = timePart.split(':').map(Number)
    date = new Date(year, month - 1, day, hours, minutes)
  } else {
    const today = new Date()
    const [hours, minutes] = timeStr.split(':').map(Number)
    date = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes)
  }
  const timezoneOffset = date.getTimezoneOffset() * 60
  return (Math.floor(date.getTime() / 1000) - timezoneOffset) as UTCTimestamp
}

const extractDisplayTime = (timeStr: string): string => {
  if (timeStr.includes(' ')) return timeStr.split(' ')[1]
  return timeStr
}

export default function IntradayChart({
  data,
  preClose,
  height = 500,
  stockName = '',
}: IntradayChartProps) {
  const priceChartContainerRef = useRef<HTMLDivElement>(null)
  const priceChartRef = useRef<IChartApi | null>(null)
  const priceSeriesRef = useRef<ISeriesApi<'Area'> | null>(null)
  const avgPriceSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const baselineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)

  const volumeChartContainerRef = useRef<HTMLDivElement>(null)
  const volumeChartRef = useRef<IChartApi | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  const dataMapRef = useRef<Map<number, IntradayData>>(new Map())
  const [tooltipData, setTooltipData] = useState<TooltipData | null>(null)

  const headerHeight = 56
  const priceChartHeight = Math.floor((height - headerHeight) * 0.7)
  const volumeChartHeight = Math.floor((height - headerHeight) * 0.3)

  useEffect(() => {
    const map = new Map<number, IntradayData>()
    data.forEach((d) => {
      const timestamp = parseTimeToTimestamp(d.time)
      map.set(timestamp, d)
    })
    dataMapRef.current = map
  }, [data])

  const handleCrosshairMove = useCallback((param: MouseEventParams) => {
    if (!param.time || !param.point) {
      if (data.length > 0) {
        const lastData = data[data.length - 1]
        const change = lastData.price - preClose
        const changePct = (change / preClose) * 100
        setTooltipData({
          time: extractDisplayTime(lastData.time),
          price: lastData.price,
          avgPrice: lastData.avg_price,
          volume: lastData.volume,
          amount: lastData.amount,
          change,
          changePct,
        })
      }
      return
    }

    const timestamp = param.time as number
    const currentData = dataMapRef.current.get(timestamp)
    if (currentData) {
      const change = currentData.price - preClose
      const changePct = (change / preClose) * 100
      setTooltipData({
        time: extractDisplayTime(currentData.time),
        price: currentData.price,
        avgPrice: currentData.avg_price,
        volume: currentData.volume,
        amount: currentData.amount,
        change,
        changePct,
      })
    }
  }, [data, preClose])

  // 初始化图表
  useEffect(() => {
    if (!priceChartContainerRef.current || !volumeChartContainerRef.current) return

    const priceChart = createChart(priceChartContainerRef.current, {
      width: priceChartContainerRef.current.clientWidth,
      height: priceChartHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#1a1a2e' },
        textColor: '#8a8a9a',
      },
      grid: {
        vertLines: { color: '#2a2a3e', style: 1 },
        horzLines: { color: '#2a2a3e', style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#555577', width: 1, style: 2, labelBackgroundColor: '#3a3a5a' },
        horzLine: { color: '#555577', width: 1, style: 2, labelBackgroundColor: '#3a3a5a' },
      },
      rightPriceScale: {
        borderColor: '#2a2a3e',
        scaleMargins: { top: 0.05, bottom: 0.05 },
        mode: PriceScaleMode.Normal,
      },
      timeScale: {
        borderColor: '#2a2a3e',
        timeVisible: true,
        secondsVisible: false,
        visible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: (time: number) => {
          const date = new Date(time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          return `${hours}:${minutes}`
        },
      },
      handleScroll: false,  // Disable scrolling
      handleScale: false,   // Disable zooming
      localization: {
        timeFormatter: (time: number) => {
          const date = new Date(time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          return `${hours}:${minutes}`
        },
      },
    })

    const priceSeries = priceChart.addAreaSeries({
      lineColor: '#5b9cf6',
      topColor: 'rgba(91, 156, 246, 0.4)',
      bottomColor: 'rgba(91, 156, 246, 0.05)',
      lineWidth: 2,
      priceLineVisible: true,
      priceLineColor: '#5b9cf6',
      priceLineWidth: 1,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: '#5b9cf6',
      crosshairMarkerBorderColor: '#ffffff',
    })

    const avgPriceSeries = priceChart.addLineSeries({
      color: '#e6a23c',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 3,
      crosshairMarkerBackgroundColor: '#e6a23c',
    })

    const baselineSeries = priceChart.addLineSeries({
      color: '#666688',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    const volumeChart = createChart(volumeChartContainerRef.current, {
      width: volumeChartContainerRef.current.clientWidth,
      height: volumeChartHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#1a1a2e' },
        textColor: '#8a8a9a',
      },
      grid: {
        vertLines: { color: '#2a2a3e', style: 1 },
        horzLines: { color: '#2a2a3e', style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#555577', width: 1, style: 2, labelBackgroundColor: '#3a3a5a' },
        horzLine: { color: '#555577', width: 1, style: 2, labelBackgroundColor: '#3a3a5a' },
      },
      rightPriceScale: {
        borderColor: '#2a2a3e',
        scaleMargins: { top: 0.1, bottom: 0.05 },
      },
      timeScale: {
        borderColor: '#2a2a3e',
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
        tickMarkFormatter: (time: number) => {
          const date = new Date(time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          // 显示关键时间点
          if (minutes === '00' || minutes === '30') {
            return `${hours}:${minutes}`
          }
          return ''
        },
      },
      handleScroll: false,  // Disable scrolling
      handleScale: false,   // Disable zooming
      localization: {
        timeFormatter: (time: number) => {
          const date = new Date(time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          return `${hours}:${minutes}`
        },
      },
    })

    const volumeSeries = volumeChart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'right',
    })

    priceChartRef.current = priceChart
    priceSeriesRef.current = priceSeries
    avgPriceSeriesRef.current = avgPriceSeries
    baselineSeriesRef.current = baselineSeries
    volumeChartRef.current = volumeChart
    volumeSeriesRef.current = volumeSeries

    priceChart.subscribeCrosshairMove(handleCrosshairMove)
    volumeChart.subscribeCrosshairMove(handleCrosshairMove)

    // 同步时间轴
    priceChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) volumeChart.timeScale().setVisibleLogicalRange(range)
    })
    volumeChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) priceChart.timeScale().setVisibleLogicalRange(range)
    })

    const handleResize = () => {
      if (priceChartContainerRef.current && volumeChartContainerRef.current) {
        priceChart.applyOptions({ width: priceChartContainerRef.current.clientWidth })
        volumeChart.applyOptions({ width: volumeChartContainerRef.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      priceChart.unsubscribeCrosshairMove(handleCrosshairMove)
      volumeChart.unsubscribeCrosshairMove(handleCrosshairMove)
      priceChart.remove()
      volumeChart.remove()
    }
  }, [priceChartHeight, volumeChartHeight, handleCrosshairMove])

  // 更新数据
  useEffect(() => {
    if (!priceSeriesRef.current || !avgPriceSeriesRef.current || !volumeSeriesRef.current || !baselineSeriesRef.current) return

    const dateStr = getDateFromData(data)
    const allTradingTimes = generateTradingTimes(dateStr)

    // 构建数据映射
    const dataByTime = new Map<string, IntradayData>()
    data.forEach((d) => {
      const timeKey = d.time.includes(' ') ? d.time : `${dateStr} ${d.time}`
      dataByTime.set(timeKey, d)
    })

    // 生成完整时间轴数据
    const priceData: { time: UTCTimestamp; value: number }[] = []
    const avgPriceData: { time: UTCTimestamp; value: number }[] = []
    const volumeData: { time: UTCTimestamp; value: number; color: string }[] = []
    const baselineData: { time: UTCTimestamp; value: number }[] = []

    let hasData = false

    allTradingTimes.forEach((timeStr, index) => {
      const timestamp = parseTimeToTimestamp(timeStr)
      const d = dataByTime.get(timeStr)

      if (d) {
        hasData = true
        priceData.push({ time: timestamp, value: d.price })
        avgPriceData.push({ time: timestamp, value: d.avg_price })

        const prevData = index > 0 ? dataByTime.get(allTradingTimes[index - 1]) : null
        const prevPrice = prevData ? prevData.price : preClose
        const isUp = d.price >= prevPrice

        volumeData.push({
          time: timestamp,
          value: d.volume,
          color: isUp ? '#ef5350' : '#26a69a',
        })
      } else {
        // 没有数据的时间点，成交量设为0（保持时间轴对齐）
        volumeData.push({
          time: timestamp,
          value: 0,
          color: 'transparent',
        })
      }

      // 基准线覆盖整个时间范围
      baselineData.push({ time: timestamp, value: preClose })
    })

    if (!hasData && data.length === 0) {
      // 没有数据时，只显示基准线
      priceSeriesRef.current.setData([])
      avgPriceSeriesRef.current.setData([])
      volumeSeriesRef.current.setData([])
      baselineSeriesRef.current.setData(baselineData)
    } else {
      priceSeriesRef.current.setData(priceData)
      avgPriceSeriesRef.current.setData(avgPriceData)
      volumeSeriesRef.current.setData(volumeData)
      baselineSeriesRef.current.setData(baselineData)
    }

    // 设置固定时间范围
    if (priceChartRef.current && volumeChartRef.current && allTradingTimes.length > 0) {
      const startTime = parseTimeToTimestamp(allTradingTimes[0])
      const endTime = parseTimeToTimestamp(allTradingTimes[allTradingTimes.length - 1])

      priceChartRef.current.timeScale().setVisibleRange({
        from: startTime,
        to: endTime,
      })
      volumeChartRef.current.timeScale().setVisibleRange({
        from: startTime,
        to: endTime,
      })
    }

    // 更新 tooltip
    if (data.length > 0) {
      const lastData = data[data.length - 1]
      const change = lastData.price - preClose
      const changePct = (change / preClose) * 100
      setTooltipData({
        time: extractDisplayTime(lastData.time),
        price: lastData.price,
        avgPrice: lastData.avg_price,
        volume: lastData.volume,
        amount: lastData.amount,
        change,
        changePct,
      })
    }
  }, [data, preClose])

  const isUp = tooltipData ? tooltipData.change >= 0 : true
  const priceColor = isUp ? '#ef5350' : '#26a69a'

  return (
    <div className="intraday-chart-container" style={{ height, position: 'relative', background: '#1a1a2e' }}>
      {/* 顶部信息栏 */}
      <div
        style={{
          height: headerHeight,
          padding: '8px 16px',
          background: '#1a1a2e',
          borderBottom: '1px solid #2a2a3e',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '8px 20px',
          fontSize: 13,
          color: '#b0b0c0',
        }}
      >
        {stockName && (
          <span style={{ fontWeight: 600, color: '#ffffff', marginRight: 4 }}>{stockName}</span>
        )}

        {tooltipData && (
          <>
            <span style={{
              background: '#2a2a4a',
              padding: '3px 10px',
              borderRadius: 4,
              color: '#7eb8ff',
              fontWeight: 500,
            }}>
              {tooltipData.time}
            </span>

            <span>
              <span style={{ color: '#888' }}>价格:</span>
              <span style={{ color: priceColor, marginLeft: 6, fontWeight: 600, fontSize: 14 }}>
                {formatNumber(tooltipData.price)}
              </span>
            </span>

            <span>
              <span style={{ color: '#888' }}>涨跌:</span>
              <span style={{ color: priceColor, marginLeft: 6 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.change)}
              </span>
            </span>

            <span>
              <span style={{ color: '#888' }}>涨幅:</span>
              <span style={{ color: priceColor, marginLeft: 6, fontWeight: 500 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.changePct)}%
              </span>
            </span>

            <span>
              <span style={{ color: '#888' }}>均价:</span>
              <span style={{ color: '#e6a23c', marginLeft: 6 }}>
                {formatNumber(tooltipData.avgPrice)}
              </span>
            </span>

            <span>
              <span style={{ color: '#888' }}>成交量:</span>
              <span style={{ color: '#fff', marginLeft: 6 }}>{formatVolume(tooltipData.volume)}</span>
            </span>

            <span>
              <span style={{ color: '#888' }}>成交额:</span>
              <span style={{ color: '#fff', marginLeft: 6 }}>{formatAmount(tooltipData.amount)}</span>
            </span>

            <span>
              <span style={{ color: '#888' }}>昨收:</span>
              <span style={{ color: '#999', marginLeft: 6 }}>{formatNumber(preClose)}</span>
            </span>
          </>
        )}
      </div>

      {/* 价格图表 */}
      <div ref={priceChartContainerRef} style={{ height: priceChartHeight }} />

      {/* 成交量图表 */}
      <div ref={volumeChartContainerRef} style={{ height: volumeChartHeight }} />

      {/* 右侧涨跌幅标签 */}
      {tooltipData && (
        <div
          style={{
            position: 'absolute',
            right: 8,
            top: headerHeight + 8,
            background: priceColor,
            color: '#fff',
            padding: '4px 8px',
            borderRadius: 4,
            fontSize: 12,
            fontWeight: 600,
            zIndex: 10,
          }}
        >
          {isUp ? '+' : ''}{formatNumber(tooltipData.changePct)}%
        </div>
      )}

      {/* 当前价格标签 */}
      {tooltipData && (
        <div
          style={{
            position: 'absolute',
            right: 8,
            top: headerHeight + 36,
            background: '#5b9cf6',
            color: '#fff',
            padding: '4px 8px',
            borderRadius: 4,
            fontSize: 12,
            fontWeight: 600,
            zIndex: 10,
          }}
        >
          {formatNumber(tooltipData.price)}
        </div>
      )}

      {/* 午休分隔线标记 */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: headerHeight,
          bottom: volumeChartHeight + 24,
          width: 1,
          background: 'rgba(100, 100, 150, 0.3)',
          pointerEvents: 'none',
        }}
      />
    </div>
  )
}
