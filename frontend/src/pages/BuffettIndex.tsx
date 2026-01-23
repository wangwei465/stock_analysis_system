import React, { useEffect, useState, useRef, useCallback } from 'react'
import { Card, Spin, Alert, Statistic, Row, Col, Typography, Divider, Tag, Progress } from 'antd'
import { LineChartOutlined, RiseOutlined, FallOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { createChart, IChartApi, ISeriesApi, LineData } from 'lightweight-charts'
import { getBuffettIndexData, getBuffettIndexStats, BuffettIndexData, BuffettIndexStats } from '../api/buffettIndex'

const { Title, Paragraph, Text } = Typography

// 生成投资建议
function getInvestmentAdvice(stats: BuffettIndexStats, latestData: BuffettIndexData | null) {
  if (!stats || !latestData) return null

  const current = stats.buffett_ratio.current
  const avg = stats.buffett_ratio.avg
  const percentile10y = stats.percentile_10y.current
  const percentileAll = stats.percentile_all.current

  // 判断信号
  let signal: 'bullish' | 'neutral' | 'bearish'
  let signalText: string
  let signalColor: string
  let icon: React.ReactNode

  if (percentileAll < 0.3) {
    signal = 'bullish'
    signalText = '积极看多'
    signalColor = '#10b981'
    icon = <CheckCircleOutlined />
  } else if (percentileAll > 0.7) {
    signal = 'bearish'
    signalText = '谨慎观望'
    signalColor = '#ef4444'
    icon = <CloseCircleOutlined />
  } else if (percentileAll < 0.5) {
    signal = 'bullish'
    signalText = '偏多'
    signalColor = '#22c55e'
    icon = <CheckCircleOutlined />
  } else {
    signal = 'neutral'
    signalText = '中性'
    signalColor = '#f59e0b'
    icon = <WarningOutlined />
  }

  // 配置建议
  let stockAlloc: string
  let bondAlloc: string
  let cashAlloc: string

  if (percentileAll < 0.3) {
    stockAlloc = '70-80%'
    bondAlloc = '15-25%'
    cashAlloc = '5-10%'
  } else if (percentileAll > 0.7) {
    stockAlloc = '30-40%'
    bondAlloc = '40-50%'
    cashAlloc = '15-20%'
  } else if (percentileAll < 0.5) {
    stockAlloc = '60-70%'
    bondAlloc = '25-35%'
    cashAlloc = '5-10%'
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
    current,
    avg,
    percentile10y,
    percentileAll,
    stockAlloc,
    bondAlloc,
    cashAlloc,
    belowAvg: current < avg,
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
  { key: 'index', label: '沪深300', color: '#ef4444', visible: true },
  { key: 'ratio', label: '总市值/GDP', color: '#3b82f6', visible: true },
]

export default function BuffettIndex() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<BuffettIndexData[]>([])
  const [stats, setStats] = useState<BuffettIndexStats | null>(null)
  const [legendItems, setLegendItems] = useState<LegendItem[]>(initialLegendItems)
  const [tooltip, setTooltip] = useState<{ visible: boolean; x: number; y: number; date: string; values: { label: string; value: string; color: string }[] }>({
    visible: false, x: 0, y: 0, date: '', values: []
  })

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<Record<string, ISeriesApi<'Line'> | ISeriesApi<'Area'>>>({})

  // 加载数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        const [indexData, indexStats] = await Promise.all([
          getBuffettIndexData(),
          getBuffettIndexStats()
        ])

        setData(indexData)
        setStats(indexStats)
      } catch (err) {
        console.error('加载巴菲特指标数据失败:', err)
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
        vertLine: { labelVisible: true },
        horzLine: { labelVisible: true },
      },
      localization: {
        dateFormat: 'yyyy-MM-dd',
      },
    })

    chartRef.current = newChart

    // 创建沪深300线（左Y轴）
    const indexSeries = newChart.addLineSeries({
      color: '#ef4444',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    // 创建总市值/GDP面积图（右Y轴）
    const ratioSeries = newChart.addAreaSeries({
      lineColor: '#3b82f6',
      topColor: 'rgba(59, 130, 246, 0.4)',
      bottomColor: 'rgba(59, 130, 246, 0.05)',
      lineWidth: 2,
      priceScaleId: 'right',
    })

    seriesRef.current = {
      index: indexSeries,
      ratio: ratioSeries,
    }

    // 准备数据
    const indexData: LineData[] = data.map(item => ({
      time: item.日期,
      value: item.收盘价,
    }))

    const ratioData: LineData[] = data.map(item => ({
      time: item.日期,
      value: item.总市值GDP比,
    }))

    indexSeries.setData(indexData)
    ratioSeries.setData(ratioData)

    newChart.timeScale().fitContent()

    // 订阅十字线移动事件
    newChart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {
        setTooltip(prev => ({ ...prev, visible: false }))
        return
      }

      const dateStr = param.time as string
      const values: { label: string; value: string; color: string }[] = []

      const indexValue = param.seriesData.get(indexSeries)
      const ratioValue = param.seriesData.get(ratioSeries)

      if (indexValue && 'value' in indexValue) {
        values.push({ label: '沪深300', value: indexValue.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), color: '#ef4444' })
      }
      if (ratioValue && 'value' in ratioValue) {
        values.push({ label: '总市值/GDP', value: (ratioValue.value * 100).toFixed(2) + '%', color: '#3b82f6' })
      }

      const containerRect = chartContainer.getBoundingClientRect()
      let tooltipX = param.point.x + 15
      let tooltipY = param.point.y + 15

      if (tooltipX + 200 > containerRect.width) {
        tooltipX = param.point.x - 215
      }
      if (tooltipY + 120 > containerRect.height) {
        tooltipY = param.point.y - 135
      }

      setTooltip({
        visible: true,
        x: tooltipX,
        y: tooltipY,
        date: dateStr,
        values,
      })
    })

    // ResizeObserver
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
        <Spin size="large" tip="加载巴菲特指标数据中..." />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert message="加载失败" description={error} type="error" showIcon />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <LineChartOutlined /> 巴菲特指标（总市值/GDP）
      </Title>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总市值/GDP"
                value={(stats.buffett_ratio.current * 100).toFixed(2)}
                suffix="%"
                valueStyle={{ color: '#3b82f6' }}
                prefix={<LineChartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="近十年分位"
                value={(stats.percentile_10y.current * 100).toFixed(2)}
                suffix="%"
                valueStyle={{ color: '#f59e0b' }}
                prefix={<LineChartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总市值（万亿）"
                value={(stats.market_cap.current / 10000).toFixed(2)}
                valueStyle={{ color: '#10b981' }}
                prefix={<RiseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="GDP（万亿）"
                value={(stats.gdp.current / 10000).toFixed(2)}
                valueStyle={{ color: '#8b5cf6' }}
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
              minWidth: 180,
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
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 16 }}>核心指标</Text>
                </div>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic
                      title="总市值/GDP"
                      value={(advice.current * 100).toFixed(2)}
                      suffix="%"
                      valueStyle={{ color: '#3b82f6', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="历史平均"
                      value={(advice.avg * 100).toFixed(2)}
                      suffix="%"
                      valueStyle={{ color: '#94a3b8', fontSize: 20 }}
                    />
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>近十年分位</Text>
                      <Progress
                        percent={Math.round(advice.percentile10y * 100)}
                        size="small"
                        strokeColor={advice.percentile10y < 0.5 ? '#10b981' : '#f59e0b'}
                      />
                    </div>
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>总历史分位</Text>
                      <Progress
                        percent={Math.round(advice.percentileAll * 100)}
                        size="small"
                        strokeColor={advice.percentileAll < 0.5 ? '#10b981' : '#f59e0b'}
                      />
                    </div>
                  </Col>
                </Row>
                <Divider style={{ margin: '16px 0' }} />
                <div>
                  <Text type="secondary">位置分析：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Tag color={advice.belowAvg ? 'green' : 'orange'}>
                      {advice.belowAvg ? '✓ 低于历史平均' : '✗ 高于历史平均'}
                    </Tag>
                    <Tag color={advice.percentileAll < 0.5 ? 'green' : 'orange'}>
                      {advice.percentileAll < 0.5 ? '✓ 低于中位数' : '✗ 高于中位数'}
                    </Tag>
                  </div>
                </div>
              </Col>

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
                    {advice.percentileAll < 0.3 && (
                      <>巴菲特指标处于历史低位，市场估值较低，是较好的买入时机，可积极配置股票资产。</>
                    )}
                    {advice.percentileAll >= 0.3 && advice.percentileAll < 0.5 && (
                      <>巴菲特指标低于中位数，市场估值合理偏低，可适当增加股票配置。</>
                    )}
                    {advice.percentileAll >= 0.5 && advice.percentileAll < 0.7 && (
                      <>巴菲特指标处于中等水平，市场估值合理，建议维持均衡配置。</>
                    )}
                    {advice.percentileAll >= 0.7 && (
                      <>巴菲特指标处于历史高位，市场估值偏高，建议降低股票仓位，增加债券和现金配置。</>
                    )}
                  </Paragraph>
                </div>
              </Col>
            </Row>
            <Divider style={{ margin: '16px 0' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              风险提示：以上建议仅供参考，不构成投资建议。巴菲特指标是中长期指标，投资决策需综合考虑多重因素。
            </Text>
          </Card>
        )
      })()}

      {/* 使用说明 */}
      <Card title="巴菲特指标说明" style={{ marginBottom: 24 }}>
        <Typography>
          <Title level={4}>什么是巴菲特指标？</Title>
          <Paragraph>
            巴菲特指标（Buffett Indicator）是由沃伦·巴菲特提出的一个衡量股市整体估值水平的指标，
            计算方法为：股票总市值 / GDP。巴菲特曾称这是"在任何时候衡量股市估值的最佳单一指标"。
          </Paragraph>

          <Title level={4}>计算方法</Title>
          <Paragraph>
            巴菲特指标 = A股总市值 / 上年度GDP
            <br />
            其中，总市值 = A股收盘价 × 已发行股票总股本（A股+B股+H股）
          </Paragraph>

          <Divider />

          <Title level={4}>如何解读巴菲特指标？</Title>
          <Paragraph>
            <Text strong>1. 指标越低，股市越被低估</Text>
            <br />
            当巴菲特指标处于历史低位时，说明股市整体估值较低，可能是较好的买入时机。
          </Paragraph>

          <Paragraph>
            <Text strong>2. 指标越高，股市越被高估</Text>
            <br />
            当巴菲特指标处于历史高位时，说明股市整体估值较高，投资风险增大。
          </Paragraph>

          <Paragraph>
            <Text strong>3. 参考分位数判断</Text>
            <br />
            • 分位数 &lt; 30%：市场低估，可积极买入
            <br />
            • 分位数 30%-50%：市场合理偏低，可适当买入
            <br />
            • 分位数 50%-70%：市场合理，保持观望
            <br />
            • 分位数 &gt; 70%：市场高估，谨慎投资
          </Paragraph>

          <Divider />

          <Title level={4}>注意事项</Title>
          <Paragraph>
            <Text type="secondary">
              1. 巴菲特指标是一个宏观指标，主要用于判断市场整体估值水平
              <br />
              2. 该指标适用于中长期投资决策，不适合短期交易
              <br />
              3. 中国股市与美国股市结构不同，指标的绝对值参考意义有限，应更关注相对位置
              <br />
              4. 投资决策应综合考虑多个指标，不应单独依赖巴菲特指标
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
