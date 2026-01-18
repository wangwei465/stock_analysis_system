import { useEffect, useRef } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  HistogramData,
  LineData,
  ColorType,
} from 'lightweight-charts'
import type { IndicatorData } from '../../types/stock'
import type { TimeRange } from './KLineChart'

interface MACDChartProps {
  data: {
    macd: IndicatorData[]
    signal: IndicatorData[]
    histogram: IndicatorData[]
  }
  height?: number
  visibleRange?: TimeRange | null  // 同步可见范围
}

export default function MACDChart({ data, height = 150, visibleRange }: MACDChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

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
      },
      timeScale: {
        borderColor: '#2B2B43',
        visible: false,
      },
    })

    chartRef.current = chart

    // MACD histogram
    const histogramSeries = chart.addHistogramSeries({
      priceFormat: { type: 'price', precision: 4 },
      priceLineVisible: false,
    })

    // MACD line
    const macdSeries = chart.addLineSeries({
      color: '#2196F3',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Signal line
    const signalSeries = chart.addLineSeries({
      color: '#FF9800',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Set histogram data with colors
    if (data.histogram && data.histogram.length > 0) {
      const histData: HistogramData[] = data.histogram.map((d) => ({
        time: d.time,
        value: d.value,
        color: d.value >= 0 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)',
      }))
      histogramSeries.setData(histData)
    }

    // Set MACD line data
    if (data.macd && data.macd.length > 0) {
      const macdData: LineData[] = data.macd.map((d) => ({
        time: d.time,
        value: d.value,
      }))
      macdSeries.setData(macdData)
    }

    // Set signal line data
    if (data.signal && data.signal.length > 0) {
      const signalData: LineData[] = data.signal.map((d) => ({
        time: d.time,
        value: d.value,
      }))
      signalSeries.setData(signalData)
    }

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
        MACD (12, 26, 9)
      </div>
      <div ref={chartContainerRef} style={{ height }} />
    </div>
  )
}
