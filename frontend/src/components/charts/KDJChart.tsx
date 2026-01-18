import { useEffect, useRef } from 'react'
import {
  createChart,
  IChartApi,
  LineData,
  ColorType,
} from 'lightweight-charts'
import type { IndicatorData } from '../../types/stock'
import type { TimeRange } from './KLineChart'

interface KDJChartProps {
  data: {
    k: IndicatorData[]
    d: IndicatorData[]
    j: IndicatorData[]
  }
  height?: number
  visibleRange?: TimeRange | null  // 同步可见范围
}

export default function KDJChart({ data, height = 120, visibleRange }: KDJChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current || !data.k || data.k.length === 0) return

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

    // K line (yellow)
    const kSeries = chart.addLineSeries({
      color: '#f6c85c',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // D line (blue)
    const dSeries = chart.addLineSeries({
      color: '#6b93d6',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // J line (purple)
    const jSeries = chart.addLineSeries({
      color: '#ab47bc',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Set data
    if (data.k && data.k.length > 0) {
      const kData: LineData[] = data.k.map((d) => ({
        time: d.time,
        value: d.value,
      }))
      kSeries.setData(kData)
    }

    if (data.d && data.d.length > 0) {
      const dData: LineData[] = data.d.map((d) => ({
        time: d.time,
        value: d.value,
      }))
      dSeries.setData(dData)
    }

    if (data.j && data.j.length > 0) {
      const jData: LineData[] = data.j.map((d) => ({
        time: d.time,
        value: d.value,
      }))
      jSeries.setData(jData)
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
        KDJ (9, 3, 3) -
        <span style={{ color: '#f6c85c' }}> K</span>
        <span style={{ color: '#6b93d6' }}> D</span>
        <span style={{ color: '#ab47bc' }}> J</span>
      </div>
      <div ref={chartContainerRef} style={{ height }} />
    </div>
  )
}
