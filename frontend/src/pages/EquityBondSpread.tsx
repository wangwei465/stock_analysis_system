import { useEffect, useState, useRef, useCallback } from 'react'
import { Card, Spin, Alert, Statistic, Row, Col, Typography, Divider, Tag, Progress } from 'antd'
import { LineChartOutlined, RiseOutlined, FallOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { createChart, IChartApi, ISeriesApi, LineData } from 'lightweight-charts'
import { getEquityBondSpreadData, getEquityBondSpreadStats, EquityBondSpreadData, EquityBondSpreadStats } from '../api/equityBondSpread'

const { Title, Paragraph, Text } = Typography

// 生成投资建议
function getInvestmentAdvice(stats: EquityBondSpreadStats, latestData: EquityBondSpreadData | null) {
  if (!stats || !latestData) return null

  const current = stats.equity_bond_spread.current
  const avg = stats.equity_bond_spread.avg
  const ma = stats.equity_bond_spread_ma.current
  const stdUpper = latestData.股债利差标准差上界
  const stdLower = latestData.股债利差标准差下界

  // 计算历史分位数（简化计算）
  const range = stats.equity_bond_spread.max - stats.equity_bond_spread.min
  const percentile = ((current - stats.equity_bond_spread.min) / range) * 100

  // 判断信号
  let signal: 'bullish' | 'neutral' | 'bearish'
  let signalText: string
  let signalColor: string
  let icon: React.ReactNode

  if (current > stdUpper) {
    signal = 'bullish'
    signalText = '积极看多'
    signalColor = '#10b981'
    icon = <CheckCircleOutlined />
  } else if (current < stdLower) {
    signal = 'bearish'
    signalText = '谨慎观望'
    signalColor = '#ef4444'
    icon = <CloseCircleOutlined />
  } else if (current > ma) {
    signal = 'bullish'
    signalText = '偏多'
    signalColor = '#22c55e'
    icon = <CheckCircleOutlined />
  } else if (current > avg) {
    signal = 'neutral'
    signalText = '中性偏多'
    signalColor = '#f59e0b'
    icon = <WarningOutlined />
  } else {
    signal = 'neutral'
    signalText = '中性偏空'
    signalColor = '#f97316'
    icon = <WarningOutlined />
  }

  // 配置建议
  let stockAlloc: string
  let bondAlloc: string
  let cashAlloc: string

  if (signal === 'bullish' && current > stdUpper) {
    stockAlloc = '70-80%'
    bondAlloc = '15-25%'
    cashAlloc = '5-10%'
  } else if (signal === 'bullish') {
    stockAlloc = '60-70%'
    bondAlloc = '25-35%'
    cashAlloc = '5-10%'
  } else if (signal === 'bearish') {
    stockAlloc = '30-40%'
    bondAlloc = '40-50%'
    cashAlloc = '15-20%'
  } else {
    stockAlloc = '50-60%'
    bondAlloc = '30-40%'
    cashAlloc = '10-15%'
  }

  return {
    signal,
    signalText,
    signalColor,
    icon,
    percentile,
    current,
    avg,
    ma,
    stdUpper,
    stdLower,
    stockAlloc,
    bondAlloc,
    cashAlloc,
    aboveAvg: current > avg,
    aboveMa: current > ma,
  }
}

// 图例配置
interface LegendItem {
  key: string
  label: string
  color: string
  visible: boolean
}

const initialLegendItems: LegendItem[] = [
  { key: 'ebs', label: '股债利差', color: '#3b82f6', visible: true },
  { key: 'index', label: '指数', color: '#ef4444', visible: true },
  { key: 'ebsMa', label: '股债利差均线', color: '#f59e0b', visible: true },
  { key: 'stdUpper', label: '股债利差标准差 × 2', color: '#10b981', visible: true },
  { key: 'stdLower', label: '-股债利差标准差 × 2', color: '#8b5cf6', visible: true },
]

export default function EquityBondSpread() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<EquityBondSpreadData[]>([])
  const [stats, setStats] = useState<EquityBondSpreadStats | null>(null)
  const [legendItems, setLegendItems] = useState<LegendItem[]>(initialLegendItems)
  const [tooltip, setTooltip] = useState<{ visible: boolean; x: number; y: number; date: string; values: { label: string; value: string; color: string }[] }>({
    visible: false, x: 0, y: 0, date: '', values: []
  })

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<Record<string, ISeriesApi<'Line'>>>({})

  // 加载数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        const [spreadData, spreadStats] = await Promise.all([
          getEquityBondSpreadData(),
          getEquityBondSpreadStats()
        ])

        setData(spreadData)
        setStats(spreadStats)
      } catch (err) {
        console.error('加载股债利差数据失败:', err)
        setError(err instanceof Error ? err.message : '加载数据失败')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // 切换图例可见性
  const toggleLegend = useCallback((key: string) => {
    setLegendItems(prev => prev.map(item => {
      if (item.key === key) {
        const newVisible = !item.visible
        const series = seriesRef.current[key]
        if (series) {
          series.applyOptions({ visible: newVisible })
        }
        return { ...item, visible: newVisible }
      }
      return item
    }))
  }, [])

  // 初始化图表
  useEffect(() => {
    if (!data.length || !chartContainerRef.current) return

    const chartContainer = chartContainerRef.current

    // 创建新图表（配置双Y轴）
    const newChart = createChart(chartContainer, {
      width: chartContainer.clientWidth,
      height: 500,
      layout: {
        background: { color: '#1e293b' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      leftPriceScale: {
        borderColor: '#334155',
        visible: true,
      },
      rightPriceScale: {
        borderColor: '#334155',
        visible: true,
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: false,
        minBarSpacing: 0.001,  // 允许缩小到看到全部数据
        fixLeftEdge: true,     // 固定左边缘，防止滚动超出数据范围
        fixRightEdge: true,    // 固定右边缘，防止滚动超出数据范围
      },
      crosshair: {
        mode: 1,
        vertLine: {
          labelVisible: true,
        },
        horzLine: {
          labelVisible: true,
        },
      },
      localization: {
        dateFormat: 'yyyy-MM-dd',
      },
    })

    chartRef.current = newChart

    // 创建股债利差线（左Y轴）
    const ebsSeries = newChart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    // 创建股债利差均线（左Y轴）
    const ebsMaSeries = newChart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    // 创建标准差上界（左Y轴）
    const stdUpperSeries = newChart.addLineSeries({
      color: '#10b981',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    // 创建标准差下界（左Y轴）
    const stdLowerSeries = newChart.addLineSeries({
      color: '#8b5cf6',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    // 创建指数线（右Y轴）
    const indexSeries = newChart.addLineSeries({
      color: '#ef4444',
      lineWidth: 2,
      priceScaleId: 'right',
    })

    // 保存series引用
    seriesRef.current = {
      ebs: ebsSeries,
      ebsMa: ebsMaSeries,
      stdUpper: stdUpperSeries,
      stdLower: stdLowerSeries,
      index: indexSeries,
    }

    // 准备数据
    const ebsData: LineData[] = data.map(item => ({
      time: item.日期,
      value: item.股债利差,
    }))

    const ebsMaData: LineData[] = data.map(item => ({
      time: item.日期,
      value: item.股债利差均线,
    }))

    const stdUpperData: LineData[] = data
      .filter(item => item.股债利差标准差上界 !== null)
      .map(item => ({
        time: item.日期,
        value: item.股债利差标准差上界!,
      }))

    const stdLowerData: LineData[] = data
      .filter(item => item.股债利差标准差下界 !== null)
      .map(item => ({
        time: item.日期,
        value: item.股债利差标准差下界!,
      }))

    const indexData: LineData[] = data.map(item => ({
      time: item.日期,
      value: item.沪深300指数,
    }))

    ebsSeries.setData(ebsData)
    ebsMaSeries.setData(ebsMaData)
    stdUpperSeries.setData(stdUpperData)
    stdLowerSeries.setData(stdLowerData)
    indexSeries.setData(indexData)

    // 自动缩放
    newChart.timeScale().fitContent()

    // 订阅十字线移动事件，显示tooltip
    newChart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {
        setTooltip(prev => ({ ...prev, visible: false }))
        return
      }

      const dateStr = param.time as string
      const values: { label: string; value: string; color: string }[] = []

      const ebsValue = param.seriesData.get(ebsSeries)
      const indexValue = param.seriesData.get(indexSeries)
      const ebsMaValue = param.seriesData.get(ebsMaSeries)
      const stdUpperValue = param.seriesData.get(stdUpperSeries)
      const stdLowerValue = param.seriesData.get(stdLowerSeries)

      if (ebsValue && 'value' in ebsValue) {
        values.push({ label: '股债利差', value: ebsValue.value.toFixed(6), color: '#3b82f6' })
      }
      if (indexValue && 'value' in indexValue) {
        values.push({ label: '指数', value: indexValue.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), color: '#ef4444' })
      }
      if (ebsMaValue && 'value' in ebsMaValue) {
        values.push({ label: '股债利差均线', value: ebsMaValue.value.toFixed(6), color: '#f59e0b' })
      }
      if (stdUpperValue && 'value' in stdUpperValue) {
        values.push({ label: '股债利差标准差 × 2', value: stdUpperValue.value.toFixed(6), color: '#10b981' })
      }
      if (stdLowerValue && 'value' in stdLowerValue) {
        values.push({ label: '-股债利差标准差 × 2', value: stdLowerValue.value.toFixed(6), color: '#8b5cf6' })
      }

      const containerRect = chartContainer.getBoundingClientRect()
      const tooltipWidth = 220
      const tooltipHeight = 180
      const offsetX = 60  // 水平偏移量，确保不挡住垂直十字线
      const offsetY = 20  // 垂直偏移量

      // 根据鼠标位置动态调整 tooltip 方向，避免遮挡选中点和十字线
      // 水平方向：鼠标在左半边则 tooltip 显示在右边，反之亦然
      let tooltipX: number
      if (param.point.x < containerRect.width / 2) {
        tooltipX = param.point.x + offsetX
      } else {
        tooltipX = param.point.x - tooltipWidth - offsetX
      }

      // 垂直方向：鼠标在上半边则 tooltip 显示在下边，反之亦然
      let tooltipY: number
      if (param.point.y < containerRect.height / 2) {
        tooltipY = param.point.y + offsetY
      } else {
        tooltipY = param.point.y - tooltipHeight - offsetY
      }

      setTooltip({
        visible: true,
        x: tooltipX,
        y: tooltipY,
        date: dateStr,
        values,
      })
    })

    // 使用 ResizeObserver 监听容器大小变化
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        if (width > 0) {
          newChart.applyOptions({ width })
        }
      }
    })

    resizeObserver.observe(chartContainer)

    return () => {
      resizeObserver.disconnect()
      newChart.remove()
      chartRef.current = null
      seriesRef.current = {}
    }
  }, [data])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载股债利差数据中..." />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
        />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <LineChartOutlined /> 股债利差
      </Title>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="当前股债利差"
                value={stats.equity_bond_spread.current}
                precision={4}
                valueStyle={{ color: '#3b82f6' }}
                prefix={<LineChartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="当前均线"
                value={stats.equity_bond_spread_ma.current}
                precision={4}
                valueStyle={{ color: '#f59e0b' }}
                prefix={<LineChartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="历史最高"
                value={stats.equity_bond_spread.max}
                precision={4}
                valueStyle={{ color: '#ef4444' }}
                prefix={<RiseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="历史最低"
                value={stats.equity_bond_spread.min}
                precision={4}
                valueStyle={{ color: '#10b981' }}
                prefix={<FallOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 图表 */}
      <Card style={{ marginBottom: 24 }}>
        {/* 图例 */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 16, justifyContent: 'center' }}>
          {legendItems.map(item => (
            <div
              key={item.key}
              onClick={() => toggleLegend(item.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
                padding: '4px 12px',
                borderRadius: 4,
                backgroundColor: item.visible ? 'rgba(255,255,255,0.1)' : 'transparent',
                opacity: item.visible ? 1 : 0.5,
                transition: 'all 0.2s',
                userSelect: 'none',
              }}
            >
              <span style={{
                width: 24,
                height: 3,
                backgroundColor: item.color,
                borderRadius: 2,
              }} />
              <span style={{ color: '#94a3b8', fontSize: 13 }}>{item.label}</span>
            </div>
          ))}
        </div>
        {/* 图表容器 */}
        <div style={{ position: 'relative' }}>
          <div ref={chartContainerRef} style={{ width: '100%', height: 500 }} />
          {/* Tooltip */}
          {tooltip.visible && (
            <div style={{
              position: 'absolute',
              left: tooltip.x,
              top: tooltip.y,
              backgroundColor: 'rgba(15, 23, 42, 0.75)',
              backdropFilter: 'blur(4px)',
              border: '1px solid rgba(148, 163, 184, 0.3)',
              borderRadius: 6,
              padding: '10px 14px',
              pointerEvents: 'none',
              zIndex: 100,
              minWidth: 200,
            }}>
              <div style={{ color: '#fff', fontWeight: 600, marginBottom: 8, fontSize: 14, textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                {tooltip.date}
              </div>
              {tooltip.values.map((v, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: v.color,
                    boxShadow: `0 0 4px ${v.color}`,
                  }} />
                  <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: 13, textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>{v.label}:</span>
                  <span style={{ color: '#fff', fontSize: 13, marginLeft: 'auto', fontWeight: 500, textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>{v.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* 当前投资建议 */}
      {stats && data.length > 0 && (() => {
        const latestData = data[data.length - 1]
        const advice = getInvestmentAdvice(stats, latestData)
        if (!advice) return null

        return (
          <Card
            title={
              <span>
                <LineChartOutlined style={{ marginRight: 8 }} />
                当前投资建议（{latestData.日期}）
              </span>
            }
            style={{ marginBottom: 24 }}
            extra={
              <Tag color={advice.signalColor} icon={advice.icon} style={{ fontSize: 14, padding: '4px 12px' }}>
                {advice.signalText}
              </Tag>
            }
          >
            <Row gutter={[24, 24]}>
              {/* 左侧：核心指标 */}
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 16 }}>核心指标</Text>
                </div>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic
                      title="当前股债利差"
                      value={advice.current}
                      precision={4}
                      valueStyle={{ color: '#3b82f6', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="均线"
                      value={advice.ma}
                      precision={4}
                      valueStyle={{ color: '#f59e0b', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="历史平均"
                      value={advice.avg}
                      precision={4}
                      valueStyle={{ color: '#94a3b8', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>历史分位</Text>
                      <Progress
                        percent={Math.round(advice.percentile)}
                        size="small"
                        strokeColor={advice.percentile > 50 ? '#10b981' : '#f59e0b'}
                        format={p => `${p}%`}
                      />
                    </div>
                  </Col>
                </Row>
                <Divider style={{ margin: '16px 0' }} />
                <div>
                  <Text type="secondary">位置分析：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Tag color={advice.aboveAvg ? 'green' : 'orange'}>
                      {advice.aboveAvg ? '✓ 高于历史平均' : '✗ 低于历史平均'}
                    </Tag>
                    <Tag color={advice.aboveMa ? 'green' : 'orange'}>
                      {advice.aboveMa ? '✓ 高于均线' : '✗ 低于均线'}
                    </Tag>
                    <Tag color={advice.current > advice.stdLower ? 'green' : 'red'}>
                      {advice.current > advice.stdLower ? '✓ 高于下界' : '✗ 低于下界'}
                    </Tag>
                  </div>
                </div>
              </Col>

              {/* 右侧：配置建议 */}
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 16 }}>配置建议</Text>
                </div>
                <div style={{
                  background: 'linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(16,185,129,0.1) 100%)',
                  borderRadius: 8,
                  padding: 16,
                }}>
                  <Row gutter={[16, 16]}>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 24, fontWeight: 600, color: '#ef4444' }}>{advice.stockAlloc}</div>
                        <Text type="secondary">股票</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 24, fontWeight: 600, color: '#3b82f6' }}>{advice.bondAlloc}</div>
                        <Text type="secondary">债券</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 24, fontWeight: 600, color: '#10b981' }}>{advice.cashAlloc}</div>
                        <Text type="secondary">现金</Text>
                      </div>
                    </Col>
                  </Row>
                </div>
                <Divider style={{ margin: '16px 0' }} />
                <div>
                  <Text type="secondary">操作建议：</Text>
                  <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                    {advice.signal === 'bullish' && advice.current > advice.stdUpper && (
                      <>股债利差处于历史高位，股票相对债券极具吸引力，可积极配置股票资产。</>
                    )}
                    {advice.signal === 'bullish' && advice.current <= advice.stdUpper && (
                      <>股债利差高于均线，股票相对债券有吸引力，可适当增加股票配置。</>
                    )}
                    {advice.signal === 'neutral' && advice.aboveAvg && (
                      <>股债利差高于历史平均但低于均线，建议维持均衡配置，关注趋势变化。</>
                    )}
                    {advice.signal === 'neutral' && !advice.aboveAvg && (
                      <>股债利差低于历史平均，市场估值偏高，建议谨慎，可适当增加债券配置。</>
                    )}
                    {advice.signal === 'bearish' && (
                      <>股债利差处于历史低位，股票估值偏高，建议降低股票仓位，增加债券和现金配置。</>
                    )}
                  </Paragraph>
                </div>
              </Col>
            </Row>
            <Divider style={{ margin: '16px 0' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              风险提示：以上建议仅供参考，不构成投资建议。股债利差是中长期指标，投资决策需综合考虑多重因素。
            </Text>
          </Card>
        )
      })()}

      {/* 使用说明和投资建议 */}
      <Card title="股债利差说明" style={{ marginBottom: 24 }}>
        <Typography>
          <Title level={4}>什么是股债利差？</Title>
          <Paragraph>
            股债利差（Equity Bond Spread，EBS）是指股票市场的盈利收益率与债券市场收益率之间的差值。
            它反映了股票相对于债券的投资吸引力，是衡量市场估值水平的重要指标。
          </Paragraph>

          <Title level={4}>计算方法</Title>
          <Paragraph>
            股债利差 = 沪深300指数盈利收益率 - 10年期国债收益率
            <br />
            其中，盈利收益率 = 1 / 市盈率（PE）
          </Paragraph>

          <Divider />

          <Title level={4}>如何解读股债利差？</Title>
          <Paragraph>
            <Text strong>1. 股债利差越高，股票相对债券越有吸引力</Text>
            <br />
            当股债利差处于历史高位时，说明股票市场估值较低，相对债券更具投资价值。
          </Paragraph>

          <Paragraph>
            <Text strong>2. 股债利差越低，债券相对股票越有吸引力</Text>
            <br />
            当股债利差处于历史低位时，说明股票市场估值较高，相对债券投资价值降低。
          </Paragraph>

          <Paragraph>
            <Text strong>3. 观察股债利差与均线的关系</Text>
            <br />
            • 当股债利差上穿均线时，可能是买入信号
            <br />
            • 当股债利差下穿均线时，可能是卖出信号
          </Paragraph>

          <Divider />

          <Title level={4}>投资建议</Title>
          <Paragraph>
            <Text type="success" strong>✓ 股债利差 &gt; 历史平均值 + 1倍标准差</Text>
            <br />
            市场估值处于低位，股票投资价值较高，可考虑增加股票配置。
          </Paragraph>

          <Paragraph>
            <Text type="warning" strong>⚠ 历史平均值 - 1倍标准差 &lt; 股债利差 &lt; 历史平均值 + 1倍标准差</Text>
            <br />
            市场估值处于合理区间，建议保持均衡配置，关注市场变化。
          </Paragraph>

          <Paragraph>
            <Text type="danger" strong>✗ 股债利差 &lt; 历史平均值 - 1倍标准差</Text>
            <br />
            市场估值处于高位，股票投资风险较大，建议降低股票配置或转向债券。
          </Paragraph>

          <Divider />

          <Title level={4}>注意事项</Title>
          <Paragraph>
            <Text type="secondary">
              1. 股债利差是一个相对指标，需要结合历史数据和市场环境综合判断
              <br />
              2. 该指标主要适用于中长期投资决策，不适合短期交易
              <br />
              3. 投资决策应综合考虑多个指标，不应单独依赖股债利差
              <br />
              4. 市场环境变化可能导致历史规律失效，需要持续关注和调整策略
            </Text>
          </Paragraph>
        </Typography>
      </Card>

      {/* 数据来源 */}
      <Card>
        <Paragraph type="secondary">
          数据来源：乐咕乐股（legulegu.com）
          <br />
          数据更新：每日更新
          <br />
          历史数据：{stats?.date_range.start} 至 {stats?.date_range.end}，共 {stats?.total_records} 条记录
        </Paragraph>
      </Card>
    </div>
  )
}
