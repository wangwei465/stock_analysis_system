import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Typography,
  Spin,
  Space,
  Segmented,
  Tag,
  Statistic,
  Switch,
  Divider,
  message,
  Badge
} from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ReloadOutlined,
  WifiOutlined
} from '@ant-design/icons'
import KLineChart, { TimeRange } from '../components/charts/KLineChart'
import IntradayChart from '../components/charts/IntradayChart'
import MACDChart from '../components/charts/MACDChart'
import RSIChart from '../components/charts/RSIChart'
import KDJChart from '../components/charts/KDJChart'
import { getKline, getStockInfo, getRealtimeQuote } from '../api/stocks'
import { getAllIndicators } from '../api/indicators'
import { useStockStore } from '../store/stockStore'
import { useIntradayWebSocket } from '../hooks/useIntradayWebSocket'
import type { StockQuote, AllIndicators } from '../types/stock'

const { Title, Text } = Typography

export default function StockDetail() {
  const { code } = useParams<{ code: string }>()
  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [loadingQuote, setLoadingQuote] = useState(false)
  const [visibleRange, setVisibleRange] = useState<TimeRange | null>(null)  // 图表可见范围同步
  const [chartType, setChartType] = useState<'intraday' | 'kline'>('intraday')  // 图表类型：分时或K线

  // WebSocket for real-time intraday data
  const {
    data: intradayData,
    preClose: intradayPreClose,
    isConnected: wsConnected,
    error: wsError
  } = useIntradayWebSocket(chartType === 'intraday' ? code : undefined)

  const {
    currentStock,
    setCurrentStock,
    klineData,
    setKlineData,
    period,
    setPeriod,
    indicators,
    setIndicators,
    loading,
    setLoading,
    showMA,
    showBOLL,
    showMACD,
    showRSI,
    showKDJ,
    toggleIndicator,
  } = useStockStore()

  // Load stock data
  useEffect(() => {
    if (!code) return

    const loadData = async () => {
      setLoading(true)
      setVisibleRange(null)  // 重置可见范围
      try {
        if (chartType === 'kline') {
          // K线模式：并行加载股票信息、K线数据和指标数据
          const [stockInfo, klineResponse, indicatorData] = await Promise.all([
            getStockInfo(code),
            getKline(code, period),
            getAllIndicators(code, '5,10,20,60', period)
          ])
          setCurrentStock(stockInfo)
          setKlineData(klineResponse.data)
          setIndicators(indicatorData)
        } else {
          // 分时模式：只需加载股票信息
          const stockInfo = await getStockInfo(code)
          setCurrentStock(stockInfo)
        }
      } catch (error) {
        console.error('Error loading stock data:', error)
        message.error('加载股票数据失败')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [code, chartType, period])

  // Load realtime quote
  const loadQuote = async () => {
    if (!code) return
    setLoadingQuote(true)
    try {
      const quoteData = await getRealtimeQuote(code)
      setQuote(quoteData)
    } catch (error) {
      console.error('Error loading quote:', error)
    } finally {
      setLoadingQuote(false)
    }
  }

  useEffect(() => {
    loadQuote()
    // Refresh quote every 10 seconds
    const interval = setInterval(loadQuote, 10000)
    return () => clearInterval(interval)
  }, [code])

  if (!code) {
    return <div>请选择股票</div>
  }

  const isUp = quote ? quote.change >= 0 : true
  const priceColor = isUp ? '#ef4444' : '#10b981'

  // 根据周期设置默认显示K线数量
  const getDefaultBars = () => {
    switch (period) {
      case 'week':
        return 52  // 周K显示约1年
      case 'month':
        return 36  // 月K显示约3年
      default:
        return 80  // 日K显示约4个月
    }
  }

  return (
    <div style={{ padding: 16 }}>
      {/* Stock Header */}
      <Card
        style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
        loading={loading && !currentStock}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              <div>
                <Title level={3} style={{ color: '#fff', margin: 0 }}>
                  {currentStock?.name || code}
                </Title>
                <Text type="secondary">{code}</Text>
              </div>
              {quote && (
                <>
                  <Statistic
                    value={quote.price}
                    precision={2}
                    valueStyle={{ color: priceColor, fontSize: 28 }}
                  />
                  <Tag color={isUp ? 'red' : 'green'} style={{ fontSize: 14 }}>
                    {isUp ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                    {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)}
                    ({quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%)
                  </Tag>
                </>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              <Spin spinning={loadingQuote} size="small" />
              <ReloadOutlined
                onClick={loadQuote}
                style={{ cursor: 'pointer', color: '#1890ff' }}
              />
            </Space>
          </Col>
        </Row>

        {quote && (
          <Row gutter={32} style={{ marginTop: 16 }}>
            <Col>
              <Text type="secondary">今开</Text>
              <div style={{ color: quote.open >= quote.pre_close ? '#ef4444' : '#10b981' }}>
                {quote.open.toFixed(2)}
              </div>
            </Col>
            <Col>
              <Text type="secondary">最高</Text>
              <div style={{ color: '#ef4444' }}>{quote.high.toFixed(2)}</div>
            </Col>
            <Col>
              <Text type="secondary">最低</Text>
              <div style={{ color: '#10b981' }}>{quote.low.toFixed(2)}</div>
            </Col>
            <Col>
              <Text type="secondary">昨收</Text>
              <div style={{ color: '#fff' }}>{quote.pre_close.toFixed(2)}</div>
            </Col>
            <Col>
              <Text type="secondary">成交量</Text>
              <div style={{ color: '#fff' }}>
                {(quote.volume / 10000).toFixed(2)}万手
              </div>
            </Col>
            <Col>
              <Text type="secondary">成交额</Text>
              <div style={{ color: '#fff' }}>
                {(quote.amount / 100000000).toFixed(2)}亿
              </div>
            </Col>
          </Row>
        )}
      </Card>

      {/* Chart Controls */}
      <Card
        style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              {/* 图表类型切换 */}
              <Space>
                <Text style={{ color: '#fff' }}>图表：</Text>
                <Segmented
                  value={chartType}
                  onChange={(value) => setChartType(value as 'intraday' | 'kline')}
                  options={[
                    { label: '分时', value: 'intraday' },
                    { label: 'K线', value: 'kline' },
                  ]}
                />
              </Space>

              {/* K线周期选择（仅在K线模式显示） */}
              {chartType === 'kline' && (
                <Space>
                  <Text style={{ color: '#fff' }}>周期：</Text>
                  <Segmented
                    value={period}
                    onChange={(value) => setPeriod(value as 'day' | 'week' | 'month')}
                    options={[
                      { label: '日K', value: 'day' },
                      { label: '周K', value: 'week' },
                      { label: '月K', value: 'month' },
                    ]}
                  />
                </Space>
              )}

              {/* WebSocket 连接状态指示器（仅在分时模式显示） */}
              {chartType === 'intraday' && (
                <Space>
                  <Badge
                    status={wsConnected ? 'success' : 'error'}
                    text={
                      <Text style={{ color: wsConnected ? '#52c41a' : '#ff4d4f', fontSize: 12 }}>
                        <WifiOutlined style={{ marginRight: 4 }} />
                        {wsConnected ? '实时' : '未连接'}
                      </Text>
                    }
                  />
                </Space>
              )}
            </Space>
          </Col>

          {/* 技术指标开关（仅在K线模式显示） */}
          {chartType === 'kline' && (
            <Col>
              <Space split={<Divider type="vertical" />}>
                <Space>
                  <Text type="secondary">MA</Text>
                  <Switch size="small" checked={showMA} onChange={() => toggleIndicator('MA')} />
                </Space>
                <Space>
                  <Text type="secondary">BOLL</Text>
                  <Switch size="small" checked={showBOLL} onChange={() => toggleIndicator('BOLL')} />
                </Space>
                <Space>
                  <Text type="secondary">MACD</Text>
                  <Switch size="small" checked={showMACD} onChange={() => toggleIndicator('MACD')} />
                </Space>
                <Space>
                  <Text type="secondary">RSI</Text>
                  <Switch size="small" checked={showRSI} onChange={() => toggleIndicator('RSI')} />
                </Space>
                <Space>
                  <Text type="secondary">KDJ</Text>
                  <Switch size="small" checked={showKDJ} onChange={() => toggleIndicator('KDJ')} />
                </Space>
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {/* Main Chart */}
      <Card
        style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
        loading={chartType === 'kline' && loading}
      >
        {chartType === 'intraday' ? (
          // 分时图 - WebSocket 实时数据
          intradayData.length > 0 ? (
            <IntradayChart
              data={intradayData}
              preClose={intradayPreClose}
              height={510}
              stockName={currentStock?.name || ''}
            />
          ) : (
            <div style={{ height: 510, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {wsConnected ? (
                <Spin tip="加载分时数据..." />
              ) : (
                <Text type="secondary">正在连接实时数据...</Text>
              )}
            </div>
          )
        ) : (
          // K线图
          loading ? (
            <div style={{ height: 510, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spin tip="加载K线数据..." />
            </div>
          ) : klineData.length > 0 ? (
            <KLineChart
              data={klineData}
              ma={showMA ? indicators?.ma : undefined}
              boll={showBOLL ? indicators?.boll : undefined}
              height={510}
              stockName={currentStock?.name || ''}
              defaultBars={getDefaultBars()}
              onVisibleRangeChange={setVisibleRange}
            />
          ) : (
            <div style={{ height: 510, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text type="secondary">暂无K线数据</Text>
            </div>
          )
        )}
      </Card>

      {/* Sub Charts - 仅在K线模式下显示 */}
      {chartType === 'kline' && (
        <>
          {showMACD && indicators?.macd && (
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
            >
              <MACDChart data={indicators.macd} height={150} visibleRange={visibleRange} />
            </Card>
          )}

          {showRSI && indicators?.rsi && indicators.rsi.length > 0 && (
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
            >
              <RSIChart data={indicators.rsi} height={120} visibleRange={visibleRange} />
            </Card>
          )}

          {showKDJ && indicators?.kdj && (
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
            >
              <KDJChart data={indicators.kdj} height={120} visibleRange={visibleRange} />
            </Card>
          )}
        </>
      )}
    </div>
  )
}
