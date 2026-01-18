import { useEffect, useRef } from 'react'
import {
  createChart,
  IChartApi,
  LineData,
  ColorType,
} from 'lightweight-charts'

interface EquityPoint {
  date: string
  equity: number
}

interface EquityCurveChartProps {
  data: EquityPoint[]
  height?: number
  initialCapital?: number
}

export default function EquityCurveChart({
  data,
  height = 300,
  initialCapital = 1000000
}: EquityCurveChartProps) {
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
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
      },
    })

    chartRef.current = chart

    // Equity curve line
    const equitySeries = chart.addLineSeries({
      color: '#2196F3',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    })

    // Baseline (initial capital)
    const baselineSeries = chart.addLineSeries({
      color: '#666666',
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Set equity data
    const equityData: LineData[] = data.map((d) => ({
      time: d.date,
      value: d.equity,
    }))
    equitySeries.setData(equityData)

    // Set baseline
    if (data.length > 0) {
      baselineSeries.setData([
        { time: data[0].date, value: initialCapital },
        { time: data[data.length - 1].date, value: initialCapital },
      ])
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
  }, [data, height, initialCapital])

  return <div ref={chartContainerRef} style={{ height }} />
}
