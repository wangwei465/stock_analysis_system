import { useEffect, useRef } from 'react'
import {
  createChart,
  IChartApi,
  LineData,
  ColorType,
} from 'lightweight-charts'
import type { IndicatorData } from '../../types/stock'
import type { TimeRange } from './KLineChart'

interface RSIChartProps {
  data: IndicatorData[]
  period?: number
  height?: number
  visibleRange?: TimeRange | null  // 同步可见范围
}

export default function RSIChart({ data, period = 14, height = 120, visibleRange }: RSIChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#141414' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: '#2B2B43',
        visible: false,
      },
    })

    chartRef.current = chart

    // RSI line
    const rsiSeries = chart.addLineSeries({
      color: '#ab47bc',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    })

    // Overbought line (70)
    const overboughtSeries = chart.addLineSeries({
      color: '#ef4444',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Oversold line (30)
    const oversoldSeries = chart.addLineSeries({
      color: '#10b981',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Set RSI data
    const rsiData: LineData[] = data.map((d) => ({
      time: d.time,
      value: d.value,
    }))
    rsiSeries.setData(rsiData)

    // Set horizontal lines
    const firstTime = data[0].time
    const lastTime = data[data.length - 1].time
    overboughtSeries.setData([
      { time: firstTime, value: 70 },
      { time: lastTime, value: 70 },
    ])
    oversoldSeries.setData([
      { time: firstTime, value: 30 },
      { time: lastTime, value: 30 },
    ])

    chart.timeScale().fitContent()

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
      chart.remove()
    }
  }, [data, height])

  // 同步可见范围
  useEffect(() => {
    if (chartRef.current && visibleRange) {
      chartRef.current.timeScale().setVisibleLogicalRange({
        from: visibleRange.from,
        to: visibleRange.to,
      })
    }
  }, [visibleRange])

  return (
    <div>
      <div style={{ color: '#a0a0a0', fontSize: 12, marginBottom: 4 }}>
        RSI ({period})
      </div>
      <div ref={chartContainerRef} style={{ height }} />
    </div>
  )
}
