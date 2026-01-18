import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  CrosshairMode,
  MouseEventParams,
  UTCTimestamp,
} from 'lightweight-charts'
import type { IntradayData } from '../../types/stock'

interface IntradayChartProps {
  data: IntradayData[]
  preClose: number
  height?: number
  stockName?: string
}

// 悬浮信息数据
interface TooltipData {
  time: string
  price: number
  avgPrice: number
  volume: number
  amount: number
  change: number
  changePct: number
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

// 将时间字符串转换为 Unix 时间戳（秒）- 使用本地时间
const parseTimeToTimestamp = (timeStr: string): UTCTimestamp => {
  // timeStr format: "YYYY-MM-DD HH:MM" or "HH:MM"
  // lightweight-charts 内部会将时间戳视为 UTC，所以我们需要补偿时区偏移
  let date: Date
  if (timeStr.includes('-')) {
    // Full datetime format: "2026-01-16 09:31"
    const [datePart, timePart] = timeStr.split(' ')
    const [year, month, day] = datePart.split('-').map(Number)
    const [hours, minutes] = timePart.split(':').map(Number)
    date = new Date(year, month - 1, day, hours, minutes)
  } else {
    // Time only format (legacy), use today's date
    const today = new Date()
    const [hours, minutes] = timeStr.split(':').map(Number)
    date = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes)
  }
  // 返回本地时间戳（不做 UTC 转换）
  // 加上时区偏移量，使 lightweight-charts 显示正确的本地时间
  const timezoneOffset = date.getTimezoneOffset() * 60  // 分钟转秒
  return (Math.floor(date.getTime() / 1000) - timezoneOffset) as UTCTimestamp
}

// 从时间字符串提取显示用的时分
const extractDisplayTime = (timeStr: string): string => {
  if (timeStr.includes(' ')) {
    return timeStr.split(' ')[1]  // "YYYY-MM-DD HH:MM" -> "HH:MM"
  }
  return timeStr  // Already "HH:MM"
}

export default function IntradayChart({
  data,
  preClose,
  height = 500,
  stockName = '',
}: IntradayChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRef = useRef<ISeriesApi<'Area'> | null>(null)
  const avgPriceSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const baselineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const dataMapRef = useRef<Map<number, IntradayData>>(new Map())

  // 悬浮信息状态
  const [tooltipData, setTooltipData] = useState<TooltipData | null>(null)

  // 构建数据映射（使用时间戳作为 key）
  useEffect(() => {
    const map = new Map<number, IntradayData>()
    data.forEach((d) => {
      const timestamp = parseTimeToTimestamp(d.time)
      map.set(timestamp, d)
    })
    dataMapRef.current = map
  }, [data])

  // 处理十字光标移动
  const handleCrosshairMove = useCallback((param: MouseEventParams) => {
    if (!param.time || !param.point) {
      // 鼠标离开图表，显示最后一个数据点
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
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height - 60,
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
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => {
          // 使用 UTC 方法，因为 parseTimeToTimestamp 已经补偿了时区
          const date = new Date(time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          return `${hours}:${minutes}`
        },
      },
      localization: {
        timeFormatter: (time: number) => {
          // 十字光标悬浮显示的时间格式
          const date = new Date(time * 1000)
          const year = date.getUTCFullYear()
          const month = String(date.getUTCMonth() + 1).padStart(2, '0')
          const day = String(date.getUTCDate()).padStart(2, '0')
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          return `${year}-${month}-${day} ${hours}:${minutes}`
        },
      },
    })

    // 价格面积图
    const priceSeries = chart.addAreaSeries({
      lineColor: '#ef4444',
      topColor: 'rgba(239, 68, 68, 0.4)',
      bottomColor: 'rgba(239, 68, 68, 0.0)',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    })

    // 均价线
    const avgPriceSeries = chart.addLineSeries({
      color: '#f6c85c',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
    })

    // 昨收价基准线
    const baselineSeries = chart.addLineSeries({
      color: '#888888',
      lineWidth: 1,
      lineStyle: 2, // 虚线
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // 成交量柱状图
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

    chartRef.current = chart
    priceSeriesRef.current = priceSeries
    avgPriceSeriesRef.current = avgPriceSeries
    baselineSeriesRef.current = baselineSeries
    volumeSeriesRef.current = volumeSeries

    // 订阅十字光标移动事件
    chart.subscribeCrosshairMove(handleCrosshairMove)

    // 处理窗口大小变化
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
      chart.remove()
    }
  }, [height, handleCrosshairMove])

  // 更新数据
  useEffect(() => {
    if (!priceSeriesRef.current || !avgPriceSeriesRef.current || !volumeSeriesRef.current || !baselineSeriesRef.current || !data.length) return

    // 去重并排序数据（按时间戳去重，保留最后一个重复项）
    const uniqueDataMap = new Map<number, typeof data[0]>()
    data.forEach((d) => {
      const timestamp = parseTimeToTimestamp(d.time)
      uniqueDataMap.set(timestamp, d)
    })
    const sortedData = Array.from(uniqueDataMap.values()).sort((a, b) => {
      return parseTimeToTimestamp(a.time) - parseTimeToTimestamp(b.time)
    })

    // 如果没有有效数据，跳过
    if (sortedData.length === 0) return

    try {
      // 价格数据（使用时间戳）
      const priceData = sortedData.map((d) => ({
        time: parseTimeToTimestamp(d.time),
        value: d.price,
      }))

      // 均价数据
      const avgPriceData = sortedData.map((d) => ({
        time: parseTimeToTimestamp(d.time),
        value: d.avg_price,
      }))

      // 成交量数据（根据涨跌着色）
      const volumeData = sortedData.map((d) => ({
        time: parseTimeToTimestamp(d.time),
        value: d.volume,
        color: d.price >= preClose ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.5)',
      }))

      // 昨收价基准线（横跨整个时间范围）
      // 注意：如果只有一个数据点，只创建一个基准点，避免重复时间戳
      let baselineData: { time: UTCTimestamp; value: number }[] = []
      if (sortedData.length === 1) {
        baselineData = [
          { time: parseTimeToTimestamp(sortedData[0].time), value: preClose },
        ]
      } else if (sortedData.length > 1) {
        baselineData = [
          { time: parseTimeToTimestamp(sortedData[0].time), value: preClose },
          { time: parseTimeToTimestamp(sortedData[sortedData.length - 1].time), value: preClose },
        ]
      }

      priceSeriesRef.current.setData(priceData)
      avgPriceSeriesRef.current.setData(avgPriceData)
      volumeSeriesRef.current.setData(volumeData)
      baselineSeriesRef.current.setData(baselineData)

      // 根据涨跌动态调整价格线颜色
      const lastPrice = sortedData[sortedData.length - 1].price
      const isUp = lastPrice >= preClose

      priceSeriesRef.current.applyOptions({
        lineColor: isUp ? '#ef4444' : '#10b981',
        topColor: isUp ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)',
        bottomColor: isUp ? 'rgba(239, 68, 68, 0.0)' : 'rgba(16, 185, 129, 0.0)',
      })

      // 自动适配内容
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent()
      }

      // 初始化显示最后一个数据点
      const lastData = sortedData[sortedData.length - 1]
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
    } catch (error) {
      console.error('[IntradayChart] Error updating chart data:', error)
    }
  }, [data, preClose])

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
        {/* 股票名称 */}
        {stockName && (
          <span style={{ fontWeight: 600, color: '#fff', marginRight: 8 }}>{stockName}</span>
        )}

        {tooltipData && (
          <>
            {/* 时间 */}
            <span style={{
              background: '#2a2a3a',
              padding: '2px 8px',
              borderRadius: 4,
              color: '#a0a0ff'
            }}>
              {tooltipData.time}
            </span>

            {/* 价格 */}
            <span>
              <span style={{ color: '#888' }}>价格</span>
              <span style={{ color: priceColor, marginLeft: 4, fontWeight: 600 }}>
                {formatNumber(tooltipData.price)}
              </span>
            </span>

            {/* 涨跌额 */}
            <span>
              <span style={{ color: '#888' }}>涨跌</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.change)}
              </span>
            </span>

            {/* 涨跌幅 */}
            <span>
              <span style={{ color: '#888' }}>涨跌幅</span>
              <span style={{ color: priceColor, marginLeft: 4 }}>
                {isUp ? '+' : ''}{formatNumber(tooltipData.changePct)}%
              </span>
            </span>

            {/* 均价 */}
            <span>
              <span style={{ color: '#888' }}>均价</span>
              <span style={{ color: '#f6c85c', marginLeft: 4 }}>
                {formatNumber(tooltipData.avgPrice)}
              </span>
            </span>

            {/* 成交量 */}
            <span>
              <span style={{ color: '#888' }}>成交量</span>
              <span style={{ color: '#fff', marginLeft: 4 }}>{formatVolume(tooltipData.volume)}</span>
            </span>

            {/* 成交额 */}
            <span>
              <span style={{ color: '#888' }}>成交额</span>
              <span style={{ color: '#fff', marginLeft: 4 }}>{formatAmount(tooltipData.amount)}</span>
            </span>

            {/* 昨收 */}
            <span>
              <span style={{ color: '#888' }}>昨收</span>
              <span style={{ color: '#888', marginLeft: 4 }}>{formatNumber(preClose)}</span>
            </span>
          </>
        )}
      </div>

      {/* 图表区域 */}
      <div ref={chartContainerRef} style={{ height: height - 60 }} />
    </div>
  )
}
