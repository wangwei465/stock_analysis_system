import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Table,
  Statistic,
  Spin,
  Tag,
  Button,
  Empty,
  Progress
} from 'antd'
import {
  StockOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RiseOutlined,
  FallOutlined,
  ReloadOutlined,
  WalletOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { filterStocks, ScreenerResult } from '../api/screener'
import { getPortfoliosSummary, PortfolioSummary } from '../api/portfolio'

const { Title, Text } = Typography

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [topGainers, setTopGainers] = useState<ScreenerResult[]>([])
  const [topLosers, setTopLosers] = useState<ScreenerResult[]>([])
  const [highVolume, setHighVolume] = useState<ScreenerResult[]>([])
  const [marketStats, setMarketStats] = useState({
    gainers: 0,
    losers: 0,
    flat: 0
  })

  // Portfolio summary state
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)

  // Load portfolio summary on mount
  useEffect(() => {
    loadPortfolioSummary()
  }, [])

  const loadPortfolioSummary = async () => {
    setPortfolioLoading(true)
    try {
      const summary = await getPortfoliosSummary()
      setPortfolioSummary(summary)
    } catch (error) {
      console.error('Error loading portfolio summary:', error)
    } finally {
      setPortfolioLoading(false)
    }
  }

  // 延迟加载：用户点击按钮后才加载数据
  const loadDashboardData = async () => {
    setLoading(true)
    try {
      // 并行加载所有数据
      const [gainersRes, losersRes, volumeRes] = await Promise.all([
        // Load top gainers
        filterStocks({
          conditions: [{ field: 'change_pct', operator: 'gt', value: 0 }],
          sort_by: 'change_pct',
          sort_order: 'desc',
          page: 1,
          page_size: 10
        }),
        // Load top losers
        filterStocks({
          conditions: [{ field: 'change_pct', operator: 'lt', value: 0 }],
          sort_by: 'change_pct',
          sort_order: 'asc',
          page: 1,
          page_size: 10
        }),
        // Load high volume stocks
        filterStocks({
          conditions: [{ field: 'volume_ratio', operator: 'gt', value: 2 }],
          sort_by: 'volume_ratio',
          sort_order: 'desc',
          page: 1,
          page_size: 10
        })
      ])

      setTopGainers(gainersRes.data)
      setTopLosers(losersRes.data)
      setHighVolume(volumeRes.data)
      setMarketStats({
        gainers: gainersRes.total,
        losers: losersRes.total,
        flat: 0
      })
      setLoaded(true)

    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const stockColumns = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
      render: (code: string) => (
        <a onClick={() => navigate(`/stock/${code}`)}>{code}</a>
      )
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 80,
    },
    {
      title: '现价',
      dataIndex: 'price',
      key: 'price',
      width: 70,
      render: (v: number) => v?.toFixed(2)
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 90,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v?.toFixed(2)}%
        </span>
      )
    },
  ]

  const volumeColumns = [
    ...stockColumns.slice(0, 3),
    {
      title: '量比',
      dataIndex: 'volume_ratio',
      key: 'volume_ratio',
      width: 70,
      render: (v: number) => (
        <Tag color="blue">{v?.toFixed(2)}</Tag>
      )
    },
    {
      title: '涨跌',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 80,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v?.toFixed(2)}%
        </span>
      )
    },
  ]

  return (
    <div style={{ padding: 16 }}>
      <Title level={3} style={{ color: '#fff', marginBottom: 24 }}>
        <StockOutlined style={{ marginRight: 8 }} />
        市场概览
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={loadDashboardData}
          loading={loading}
          style={{ marginLeft: 16 }}
        >
          {loaded ? '刷新数据' : '加载行情'}
        </Button>
      </Title>

      {/* Portfolio Summary Section */}
      {portfolioSummary && portfolioSummary.portfolio_count > 0 && (
        <Card
          style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 24 }}
          title={
            <span>
              <WalletOutlined style={{ color: '#52c41a', marginRight: 8 }} />
              <Text style={{ color: '#fff' }}>投资组合概览</Text>
            </span>
          }
          extra={<a onClick={() => navigate('/portfolio')}>管理组合</a>}
          loading={portfolioLoading}
        >
          <Row gutter={16}>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ background: '#303030', borderColor: '#404040', height: 120 }}>
                <div>
                  <Text type="secondary">总市值</Text>
                  <div style={{ fontSize: 22, fontWeight: 500, color: '#fff', marginTop: 4 }}>
                    ¥{portfolioSummary.total_value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>
                    总资产: ¥{portfolioSummary.total_initial_capital.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ background: '#303030', borderColor: '#404040', height: 120 }}>
                <div>
                  <Text type="secondary">总盈亏</Text>
                  <div style={{
                    marginTop: 8,
                    color: portfolioSummary.total_pnl >= 0 ? '#ef4444' : '#10b981',
                  }}>
                    <div style={{ fontSize: 22, fontWeight: 500, whiteSpace: 'nowrap' }}>
                      {portfolioSummary.total_pnl >= 0 ? '+' : '-'}¥{Math.abs(portfolioSummary.total_pnl).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: 14, marginTop: 4 }}>
                      {portfolioSummary.total_pnl >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                      {' '}{portfolioSummary.total_pnl_pct >= 0 ? '+' : ''}{portfolioSummary.total_pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ background: '#303030', borderColor: '#404040', height: 120 }}>
                <div>
                  <Text type="secondary">当日盈亏</Text>
                  <div style={{
                    marginTop: 8,
                    color: portfolioSummary.daily_pnl >= 0 ? '#ef4444' : '#10b981',
                  }}>
                    <div style={{ fontSize: 22, fontWeight: 500, whiteSpace: 'nowrap' }}>
                      {portfolioSummary.daily_pnl >= 0 ? '+' : '-'}¥{Math.abs(portfolioSummary.daily_pnl).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: 14, marginTop: 4 }}>
                      {portfolioSummary.daily_pnl >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                      {' '}{portfolioSummary.daily_pnl_pct >= 0 ? '+' : ''}{portfolioSummary.daily_pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ background: '#303030', borderColor: '#404040', height: 120 }}>
                <div>
                  <Text type="secondary">仓位比例</Text>
                  <div style={{ marginTop: 8 }}>
                    <Progress
                      percent={portfolioSummary.position_ratio}
                      strokeColor={portfolioSummary.position_ratio > 80 ? '#ef4444' : '#1890ff'}
                      trailColor="#404040"
                      format={(percent) => <span style={{ color: '#fff' }}>{percent?.toFixed(1)}%</span>}
                    />
                    <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                      {portfolioSummary.portfolio_count}个组合 · {portfolioSummary.position_count}只持仓
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {!loaded && !loading ? (
        // 未加载状态：显示快速导航
        <>
          <Empty
            description={<Text type="secondary">点击「加载行情」获取市场数据</Text>}
            style={{ marginBottom: 24 }}
          />

          {/* Quick Actions */}
          <Card
            style={{ background: '#1f1f1f', borderColor: '#303030' }}
            title={<Text style={{ color: '#fff' }}>快速导航</Text>}
          >
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Card
                  hoverable
                  style={{ background: '#303030', borderColor: '#404040' }}
                  onClick={() => navigate('/screener')}
                >
                  <div style={{ textAlign: 'center' }}>
                    <StockOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                    <div style={{ marginTop: 8 }}>选股筛选</div>
                  </div>
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card
                  hoverable
                  style={{ background: '#303030', borderColor: '#404040' }}
                  onClick={() => navigate('/portfolio')}
                >
                  <div style={{ textAlign: 'center' }}>
                    <StockOutlined style={{ fontSize: 32, color: '#52c41a' }} />
                    <div style={{ marginTop: 8 }}>投资组合</div>
                  </div>
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card
                  hoverable
                  style={{ background: '#303030', borderColor: '#404040' }}
                  onClick={() => navigate('/backtest')}
                >
                  <div style={{ textAlign: 'center' }}>
                    <StockOutlined style={{ fontSize: 32, color: '#faad14' }} />
                    <div style={{ marginTop: 8 }}>策略回测</div>
                  </div>
                </Card>
              </Col>
            </Row>
          </Card>
        </>
      ) : (
        // 已加载或加载中状态
        <Spin spinning={loading}>
        {/* Market Stats */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={8}>
            <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
              <Statistic
                title={<Text type="secondary">上涨家数</Text>}
                value={marketStats.gainers}
                prefix={<RiseOutlined style={{ color: '#ef4444' }} />}
                valueStyle={{ color: '#ef4444' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
              <Statistic
                title={<Text type="secondary">下跌家数</Text>}
                value={marketStats.losers}
                prefix={<FallOutlined style={{ color: '#10b981' }} />}
                valueStyle={{ color: '#10b981' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
              <Statistic
                title={<Text type="secondary">放量异动</Text>}
                value={highVolume.length}
                prefix={<StockOutlined style={{ color: '#1890ff' }} />}
                suffix="只"
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Stock Lists */}
        <Row gutter={16}>
          {/* Top Gainers */}
          <Col xs={24} lg={8}>
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
              title={
                <span>
                  <ArrowUpOutlined style={{ color: '#ef4444', marginRight: 8 }} />
                  <Text style={{ color: '#fff' }}>涨幅榜</Text>
                </span>
              }
              extra={<a onClick={() => navigate('/screener?preset=gainers')}>更多</a>}
            >
              <Table
                dataSource={topGainers}
                columns={stockColumns}
                rowKey="code"
                size="small"
                pagination={false}
                scroll={{ x: 300 }}
              />
            </Card>
          </Col>

          {/* Top Losers */}
          <Col xs={24} lg={8}>
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
              title={
                <span>
                  <ArrowDownOutlined style={{ color: '#10b981', marginRight: 8 }} />
                  <Text style={{ color: '#fff' }}>跌幅榜</Text>
                </span>
              }
              extra={<a onClick={() => navigate('/screener?preset=losers')}>更多</a>}
            >
              <Table
                dataSource={topLosers}
                columns={stockColumns}
                rowKey="code"
                size="small"
                pagination={false}
                scroll={{ x: 300 }}
              />
            </Card>
          </Col>

          {/* High Volume */}
          <Col xs={24} lg={8}>
            <Card
              style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
              title={
                <span>
                  <StockOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                  <Text style={{ color: '#fff' }}>放量异动</Text>
                </span>
              }
              extra={<a onClick={() => navigate('/screener?preset=volume')}>更多</a>}
            >
              <Table
                dataSource={highVolume}
                columns={volumeColumns}
                rowKey="code"
                size="small"
                pagination={false}
                scroll={{ x: 350 }}
              />
            </Card>
          </Col>
        </Row>

        {/* Quick Actions */}
        <Card
          style={{ background: '#1f1f1f', borderColor: '#303030', marginTop: 16 }}
          title={<Text style={{ color: '#fff' }}>快速导航</Text>}
        >
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Card
                hoverable
                style={{ background: '#303030', borderColor: '#404040' }}
                onClick={() => navigate('/screener')}
              >
                <div style={{ textAlign: 'center' }}>
                  <StockOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                  <div style={{ marginTop: 8 }}>选股筛选</div>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card
                hoverable
                style={{ background: '#303030', borderColor: '#404040' }}
                onClick={() => navigate('/portfolio')}
              >
                <div style={{ textAlign: 'center' }}>
                  <StockOutlined style={{ fontSize: 32, color: '#52c41a' }} />
                  <div style={{ marginTop: 8 }}>投资组合</div>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card
                hoverable
                style={{ background: '#303030', borderColor: '#404040' }}
                onClick={() => navigate('/backtest')}
              >
                <div style={{ textAlign: 'center' }}>
                  <StockOutlined style={{ fontSize: 32, color: '#faad14' }} />
                  <div style={{ marginTop: 8 }}>策略回测</div>
                </div>
              </Card>
            </Col>
          </Row>
        </Card>
      </Spin>
      )}
    </div>
  )
}
