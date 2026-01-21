import { useEffect, useState } from 'react'
import { Card, Spin, Alert, Statistic, Row, Col, Typography, Divider } from 'antd'
import { LineChartOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons'
import { createChart, LineData } from 'lightweight-charts'
import { getEquityBondSpreadData, getEquityBondSpreadStats, EquityBondSpreadData, EquityBondSpreadStats } from '../api/equityBondSpread'

const { Title, Paragraph, Text } = Typography

export default function EquityBondSpread() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<EquityBondSpreadData[]>([])
  const [stats, setStats] = useState<EquityBondSpreadStats | null>(null)

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

  // 初始化图表
  useEffect(() => {
    if (!data.length) return

    const chartContainer = document.getElementById('ebs-chart')
    if (!chartContainer) return

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
        timeVisible: true,
      },
    })

    // 创建股债利差线（左Y轴）
    const ebsSeries = newChart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 2,
      title: '股债利差',
      priceScaleId: 'left',
    })

    // 创建股债利差均线（左Y轴）
    const ebsMaSeries = newChart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 2,
      title: '股债利差均线',
      priceScaleId: 'left',
    })

    // 创建标准差上界（左Y轴）
    const stdUpperSeries = newChart.addLineSeries({
      color: '#10b981',
      lineWidth: 1.5,
      title: '股债利差标准差 × 2',
      priceScaleId: 'left',
    })

    // 创建标准差下界（左Y轴）
    const stdLowerSeries = newChart.addLineSeries({
      color: '#8b5cf6',
      lineWidth: 1.5,
      title: '-股债利差标准差 × 2',
      priceScaleId: 'left',
    })

    // 创建指数线（右Y轴）
    const indexSeries = newChart.addLineSeries({
      color: '#ef4444',
      lineWidth: 2,
      title: '指数',
      priceScaleId: 'right',
    })

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

    // 响应式调整
    const handleResize = () => {
      if (chartContainer) {
        newChart.applyOptions({ width: chartContainer.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      newChart.remove()
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
        <div id="ebs-chart" style={{ width: '100%', height: 500 }} />
      </Card>

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
