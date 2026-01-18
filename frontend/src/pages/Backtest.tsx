import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  InputNumber,
  DatePicker,
  Table,
  Statistic,
  Typography,
  Space,
  Spin,
  message,
  Divider,
  Tag,
  Tabs
} from 'antd'
import {
  ExperimentOutlined,
  PlayCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  HistoryOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  getStrategies,
  runBacktest,
  getBacktestHistory,
  Strategy,
  BacktestResult,
  BacktestHistoryItem,
  TradeRecord
} from '../api/backtest'
import { searchStocks } from '../api/stocks'
import EquityCurveChart from '../components/charts/EquityCurveChart'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

export default function Backtest() {
  // State
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<string>('')
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({})
  const [stockCode, setStockCode] = useState<string>('')
  const [stockOptions, setStockOptions] = useState<{ value: string; label: string }[]>([])
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [initialCapital, setInitialCapital] = useState(1000000)
  const [commission, setCommission] = useState(0.0003)

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [history, setHistory] = useState<BacktestHistoryItem[]>([])
  const [activeTab, setActiveTab] = useState('config')

  // Load strategies and history
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // 并行加载策略和历史记录
        const [strategiesData, historyData] = await Promise.all([
          getStrategies(),
          getBacktestHistory(10)
        ])

        setStrategies(strategiesData)
        if (strategiesData.length > 0) {
          setSelectedStrategy(strategiesData[0].id)
          initParams(strategiesData[0])
        }

        setHistory(historyData)
      } catch (error) {
        console.error('Error loading initial data:', error)
      }
    }
    loadInitialData()
  }, [])

  const initParams = (strategy: Strategy) => {
    const params: Record<string, number> = {}
    strategy.params.forEach(p => {
      params[p.name] = p.default
    })
    setStrategyParams(params)
  }

  const loadHistory = async () => {
    try {
      const data = await getBacktestHistory(10)
      setHistory(data)
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const handleStrategyChange = (strategyId: string) => {
    setSelectedStrategy(strategyId)
    const strategy = strategies.find(s => s.id === strategyId)
    if (strategy) {
      initParams(strategy)
    }
  }

  const handleSearchStock = async (value: string) => {
    if (!value || value.length < 1) {
      setStockOptions([])
      return
    }
    try {
      const results = await searchStocks(value)
      setStockOptions(results.map(s => ({
        value: s.code,
        label: `${s.code} - ${s.name}`
      })))
    } catch (error) {
      console.error('Search error:', error)
    }
  }

  const handleRunBacktest = async () => {
    if (!stockCode) {
      message.warning('请选择股票')
      return
    }

    setLoading(true)
    try {
      const data = await runBacktest({
        strategy: selectedStrategy,
        stock_code: stockCode,
        params: strategyParams,
        start_date: dateRange?.[0]?.format('YYYYMMDD'),
        end_date: dateRange?.[1]?.format('YYYYMMDD'),
        initial_capital: initialCapital,
        commission
      })
      setResult(data)
      setActiveTab('result')
      message.success('回测完成')
      loadHistory()
    } catch (error) {
      console.error('Backtest error:', error)
      message.error('回测失败')
    } finally {
      setLoading(false)
    }
  }

  const currentStrategy = strategies.find(s => s.id === selectedStrategy)

  const tradeColumns = [
    { title: '买入日期', dataIndex: 'entry_date', key: 'entry_date', width: 100 },
    { title: '买入价', dataIndex: 'entry_price', key: 'entry_price', width: 80, render: (v: number) => v.toFixed(2) },
    { title: '卖出日期', dataIndex: 'exit_date', key: 'exit_date', width: 100 },
    { title: '卖出价', dataIndex: 'exit_price', key: 'exit_price', width: 80, render: (v: number) => v.toFixed(2) },
    { title: '数量', dataIndex: 'shares', key: 'shares', width: 80 },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (v: number, record: TradeRecord) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}
          <div style={{ fontSize: 12 }}>({record.pnl_pct >= 0 ? '+' : ''}{record.pnl_pct.toFixed(2)}%)</div>
        </span>
      )
    },
    { title: '持仓天数', dataIndex: 'holding_days', key: 'holding_days', width: 80 },
  ]

  const historyColumns = [
    { title: '策略', dataIndex: 'strategy_name', key: 'strategy_name', width: 120 },
    { title: '股票', key: 'stock', width: 100, render: (_: any, r: BacktestHistoryItem) => `${r.stock_name}` },
    { title: '周期', dataIndex: 'period', key: 'period', width: 180 },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      width: 100,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      )
    },
    { title: '夏普比率', dataIndex: 'sharpe_ratio', key: 'sharpe_ratio', width: 80 },
    { title: '最大回撤', dataIndex: 'max_drawdown', key: 'max_drawdown', width: 80, render: (v: number) => `${v.toFixed(2)}%` },
    { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', width: 70, render: (v: number) => `${v.toFixed(0)}%` },
    { title: '交易次数', dataIndex: 'trade_count', key: 'trade_count', width: 80 },
  ]

  return (
    <div style={{ padding: 16 }}>
      <Title level={3} style={{ color: '#fff', marginBottom: 16 }}>
        <ExperimentOutlined style={{ marginRight: 8 }} />
        策略回测
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'config',
            label: '回测配置',
            children: (
              <Row gutter={16}>
                <Col xs={24} lg={8}>
                  <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      {/* Strategy Selection */}
                      <div>
                        <Text type="secondary">选择策略</Text>
                        <Select
                          value={selectedStrategy}
                          onChange={handleStrategyChange}
                          style={{ width: '100%', marginTop: 8 }}
                          options={strategies.map(s => ({
                            value: s.id,
                            label: s.name
                          }))}
                        />
                        {currentStrategy && (
                          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
                            {currentStrategy.description}
                          </Text>
                        )}
                      </div>

                      {/* Strategy Parameters */}
                      {currentStrategy?.params.map(param => (
                        <div key={param.name}>
                          <Text type="secondary">{param.description}</Text>
                          <InputNumber
                            value={strategyParams[param.name]}
                            onChange={(v) => setStrategyParams({ ...strategyParams, [param.name]: v ?? param.default })}
                            min={param.min}
                            max={param.max}
                            step={param.type === 'float' ? 0.1 : 1}
                            style={{ width: '100%', marginTop: 4 }}
                          />
                        </div>
                      ))}

                      <Divider style={{ margin: '12px 0' }} />

                      {/* Stock Selection */}
                      <div>
                        <Text type="secondary">选择股票</Text>
                        <Select
                          showSearch
                          value={stockCode}
                          onChange={setStockCode}
                          onSearch={handleSearchStock}
                          placeholder="搜索股票代码或名称"
                          style={{ width: '100%', marginTop: 8 }}
                          options={stockOptions}
                          filterOption={false}
                        />
                      </div>

                      {/* Date Range */}
                      <div>
                        <Text type="secondary">回测周期</Text>
                        <RangePicker
                          value={dateRange}
                          onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
                          style={{ width: '100%', marginTop: 8 }}
                          placeholder={['开始日期', '结束日期']}
                        />
                      </div>

                      {/* Capital & Commission */}
                      <div>
                        <Text type="secondary">初始资金</Text>
                        <InputNumber
                          value={initialCapital}
                          onChange={(v) => setInitialCapital(v ?? 1000000)}
                          formatter={v => `¥ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                          parser={v => v!.replace(/¥\s?|(,*)/g, '') as any}
                          style={{ width: '100%', marginTop: 4 }}
                        />
                      </div>

                      <div>
                        <Text type="secondary">手续费率</Text>
                        <InputNumber
                          value={commission * 100}
                          onChange={(v) => setCommission((v ?? 0.03) / 100)}
                          min={0}
                          max={1}
                          step={0.01}
                          formatter={v => `${v}%`}
                          parser={v => parseFloat(v!.replace('%', ''))}
                          style={{ width: '100%', marginTop: 4 }}
                        />
                      </div>

                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleRunBacktest}
                        loading={loading}
                        block
                        size="large"
                      >
                        开始回测
                      </Button>
                    </Space>
                  </Card>
                </Col>

                <Col xs={24} lg={16}>
                  <Card
                    style={{ background: '#1f1f1f', borderColor: '#303030' }}
                    title={<><HistoryOutlined /> 回测历史</>}
                  >
                    <Table
                      dataSource={history}
                      columns={historyColumns}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      scroll={{ x: 800 }}
                    />
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: 'result',
            label: '回测结果',
            disabled: !result,
            children: result && (
              <>
                {/* Performance Summary */}
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">总收益</Text>}
                        value={result.metrics.total_return}
                        precision={2}
                        suffix="%"
                        prefix={result.metrics.total_return >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                        valueStyle={{ color: result.metrics.total_return >= 0 ? '#ef4444' : '#10b981' }}
                      />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">年化收益</Text>}
                        value={result.metrics.annualized_return}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: result.metrics.annualized_return >= 0 ? '#ef4444' : '#10b981' }}
                      />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">最大回撤</Text>}
                        value={result.metrics.max_drawdown}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: '#10b981' }}
                      />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">夏普比率</Text>}
                        value={result.metrics.sharpe_ratio}
                        precision={2}
                        valueStyle={{ color: '#fff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">胜率</Text>}
                        value={result.metrics.win_rate}
                        precision={1}
                        suffix="%"
                        valueStyle={{ color: '#fff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={4}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
                      <Statistic
                        title={<Text type="secondary">交易次数</Text>}
                        value={result.metrics.trade_count}
                        valueStyle={{ color: '#fff' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* Equity Curve */}
                <Card
                  style={{ background: '#1f1f1f', borderColor: '#303030', marginBottom: 16 }}
                  title={
                    <Space>
                      <Text style={{ color: '#fff' }}>权益曲线</Text>
                      <Tag>{result.stock.name} ({result.stock.code})</Tag>
                      <Tag color="blue">{result.strategy.name}</Tag>
                      <Tag>{result.period.start} ~ {result.period.end}</Tag>
                    </Space>
                  }
                >
                  <EquityCurveChart
                    data={result.equity_curve}
                    height={350}
                    initialCapital={result.config.initial_capital}
                  />
                </Card>

                {/* Additional Metrics */}
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={12}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }} title="风险指标">
                      <Row gutter={[16, 16]}>
                        <Col span={8}><Statistic title="波动率" value={result.metrics.volatility} suffix="%" precision={2} /></Col>
                        <Col span={8}><Statistic title="索提诺比率" value={result.metrics.sortino_ratio} precision={2} /></Col>
                        <Col span={8}><Statistic title="卡尔玛比率" value={result.metrics.calmar_ratio} precision={2} /></Col>
                      </Row>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card style={{ background: '#1f1f1f', borderColor: '#303030' }} title="交易统计">
                      <Row gutter={[16, 16]}>
                        <Col span={8}><Statistic title="盈亏比" value={result.metrics.profit_factor} precision={2} /></Col>
                        <Col span={8}><Statistic title="平均持仓" value={result.metrics.avg_holding_days} suffix="天" precision={0} /></Col>
                        <Col span={8}><Statistic title="平均盈利" value={result.metrics.avg_win} prefix="¥" precision={0} /></Col>
                      </Row>
                    </Card>
                  </Col>
                </Row>

                {/* Trade List */}
                <Card style={{ background: '#1f1f1f', borderColor: '#303030' }} title="交易记录">
                  <Table
                    dataSource={result.trades}
                    columns={tradeColumns}
                    rowKey={(r, i) => `${r.entry_date}-${i}`}
                    size="small"
                    pagination={{ pageSize: 10 }}
                    scroll={{ x: 700 }}
                  />
                </Card>
              </>
            )
          }
        ]}
      />
    </div>
  )
}
