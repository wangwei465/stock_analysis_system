import { useState, useMemo, useCallback } from 'react'
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Statistic,
  Typography,
  Space,
  message,
  Tag,
  Tabs,
  Progress,
  List,
  Divider,
  Spin,
  Alert,
  Slider,
  Tooltip,
  Dropdown
} from 'antd'
import type { MenuProps } from 'antd'
import {
  RobotOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  BulbOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
  DownloadOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import debounce from 'lodash/debounce'
import { searchStocks } from '../api/stocks'
import {
  getComprehensivePrediction,
  ComprehensivePrediction,
  getSentimentAnalysis,
  SentimentSummary
} from '../api/ml'
import { createPredictionRecord, AccuracyStatus } from '../api/predictionRecords'

const { Title, Text, Paragraph } = Typography

// 使用 CSS 变量的颜色常量
const colors = {
  up: '#ef4444',
  down: '#10b981',
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  neutral: '#64748b',
  text: '#f1f5f9',
  textSecondary: '#94a3b8',
}

export default function Prediction() {
  const [stockCode, setStockCode] = useState<string>('')
  const [stockOptions, setStockOptions] = useState<{ value: string; label: string }[]>([])
  const [forwardDays, setForwardDays] = useState(5)
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState<ComprehensivePrediction | null>(null)
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)

  // =========================================================================
  // 防抖搜索：500ms延迟，避免频繁API调用
  // =========================================================================
  const debouncedSearch = useMemo(
    () =>
      debounce(async (value: string) => {
        if (!value || value.length < 1) {
          setStockOptions([])
          setSearchLoading(false)
          return
        }
        try {
          const results = await searchStocks(value)
          setStockOptions(results.map(s => ({
            value: s.code,
            label: `${s.code} - ${s.name}`
          })))
        } catch (error) {
          console.error('搜索错误:', error)
        } finally {
          setSearchLoading(false)
        }
      }, 500),
    []
  )

  // 搜索处理函数
  const handleSearchStock = useCallback((value: string) => {
    setSearchLoading(true)
    debouncedSearch(value)
  }, [debouncedSearch])

  const safeNumber = (value: number | null | undefined): number | null => {
    if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value)) {
      return null
    }
    return value
  }

  const buildRecord = (predResult: ComprehensivePrediction) => {
    const now = new Date()
    return {
      stock_name: predResult.stock_name,
      stock_code: predResult.stock_code,
      forward_days: predResult.forward_days,
      current_price: safeNumber(predResult.stock_info?.current_price ?? predResult.price_range?.current_price),
      direction: predResult.direction.direction_label,
      signal: predResult.signal.signal_label,
      recommendation: predResult.recommendation.action,
      expected_price: safeNumber(predResult.price_range?.expected?.price),
      support: safeNumber(predResult.price_range?.support_resistance?.support),
      resistance: safeNumber(predResult.price_range?.support_resistance?.resistance),
      prediction_date: predResult.prediction_date || now.toISOString().slice(0, 10),
      accuracy: 'unknown' as AccuracyStatus,
    }
  }

  const handlePredict = async () => {
    if (!stockCode) {
      message.warning('请选择股票')
      return
    }

    setLoading(true)
    try {
      const [predResult, sentResult] = await Promise.all([
        getComprehensivePrediction(stockCode, forwardDays, true),
        getSentimentAnalysis(stockCode)
      ])
      setPrediction(predResult)
      setSentiment(sentResult)
      try {
        await createPredictionRecord(buildRecord(predResult))
      } catch (recordError) {
        console.error('Prediction record save error:', recordError)
        message.warning('预测记录保存失败')
      }
      message.success('预测完成')
    } catch (error) {
      console.error('Prediction error:', error)
      message.error('预测失败')
    } finally {
      setLoading(false)
    }
  }

  // =========================================================================
  // 导出功能：支持CSV和JSON格式导出预测结果
  // =========================================================================
  const exportToCSV = useCallback(() => {
    if (!prediction) {
      message.warning('暂无预测数据可导出')
      return
    }

    // 构建CSV数据
    const csvRows = [
      ['字段', '值'],
      ['股票代码', prediction.stock_code],
      ['股票名称', prediction.stock_name],
      ['当前价格', prediction.stock_info?.current_price?.toString() || ''],
      ['预测周期', `${prediction.forward_days}天`],
      ['方向预测', prediction.direction?.direction_label || ''],
      ['方向置信度', `${((prediction.direction?.confidence || 0) * 100).toFixed(1)}%`],
      ['交易信号', prediction.signal?.signal_label || ''],
      ['信号置信度', `${((prediction.signal?.confidence || 0) * 100).toFixed(1)}%`],
      ['综合建议', prediction.recommendation?.action || ''],
      ['风险等级', prediction.recommendation?.risk_level || ''],
      ['预期价格', prediction.price_range?.expected?.price?.toFixed(2) || ''],
      ['支撑位', prediction.price_range?.support_resistance?.support?.toFixed(2) || ''],
      ['阻力位', prediction.price_range?.support_resistance?.resistance?.toFixed(2) || ''],
      ['日波动率', `${prediction.risk?.daily_volatility?.toFixed(2) || ''}%`],
      ['年化波动率', `${prediction.risk?.annualized_volatility?.toFixed(2) || ''}%`],
      ['20日最大回撤', `${prediction.risk?.max_drawdown_20d?.toFixed(2) || ''}%`],
      ['VaR(95%)', `${prediction.risk?.var_95?.toFixed(2) || ''}%`],
      ['预测日期', prediction.prediction_date || new Date().toISOString().slice(0, 10)]
    ]

    const csvContent = csvRows.map(row => row.join(',')).join('\n')
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `预测报告_${prediction.stock_code}_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    message.success('CSV导出成功')
  }, [prediction])

  const exportToJSON = useCallback(() => {
    if (!prediction) {
      message.warning('暂无预测数据可导出')
      return
    }

    const exportData = {
      stock_code: prediction.stock_code,
      stock_name: prediction.stock_name,
      prediction_date: prediction.prediction_date || new Date().toISOString().slice(0, 10),
      forward_days: prediction.forward_days,
      current_price: prediction.stock_info?.current_price,
      direction: {
        label: prediction.direction?.direction_label,
        confidence: prediction.direction?.confidence
      },
      signal: {
        label: prediction.signal?.signal_label,
        confidence: prediction.signal?.confidence,
        entry_price: prediction.signal?.entry_price,
        stop_loss: prediction.signal?.stop_loss,
        take_profit: prediction.signal?.take_profit
      },
      recommendation: prediction.recommendation,
      price_range: {
        expected: prediction.price_range?.expected,
        support: prediction.price_range?.support_resistance?.support,
        resistance: prediction.price_range?.support_resistance?.resistance
      },
      risk: prediction.risk,
      sentiment: sentiment
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `预测报告_${prediction.stock_code}_${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    message.success('JSON导出成功')
  }, [prediction, sentiment])

  // 导出菜单项
  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'csv',
      icon: <FileTextOutlined />,
      label: '导出为 CSV',
      onClick: exportToCSV
    },
    {
      key: 'json',
      icon: <FileTextOutlined />,
      label: '导出为 JSON',
      onClick: exportToJSON
    }
  ]

  const getSignalColor = (signal: number) => {
    if (signal >= 2) return colors.success
    if (signal === 1) return '#22c55e'
    if (signal === -1) return '#f87171'
    if (signal <= -2) return colors.error
    return colors.neutral
  }

  const getSignalIcon = (signal: number) => {
    if (signal > 0) return <ArrowUpOutlined />
    if (signal < 0) return <ArrowDownOutlined />
    return <MinusOutlined />
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return colors.success
    if (confidence >= 0.4) return colors.warning
    return colors.neutral
  }

  const getDirectionColor = (direction: number) => {
    if (direction === 1) return colors.up
    if (direction === -1) return colors.down
    return colors.neutral
  }


  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <RobotOutlined style={{ marginRight: 8, color: colors.primary }} />
        智能预测
      </Title>

      {/* 配置区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} sm={24} md={8}>
            <div style={{ marginBottom: 8 }}>
              <Text style={{ color: colors.textSecondary }}>选择股票</Text>
            </div>
            <Select
              showSearch
              value={stockCode}
              onChange={setStockCode}
              onSearch={handleSearchStock}
              placeholder="搜索股票代码或名称"
              style={{ width: '100%' }}
              options={stockOptions}
              filterOption={false}
              size="large"
              loading={searchLoading}
              notFoundContent={searchLoading ? <Spin size="small" /> : '暂无数据'}
            />
          </Col>
          <Col xs={24} sm={24} md={10}>
            <div style={{ marginBottom: 8 }}>
              <Text style={{ color: colors.textSecondary }}>预测周期</Text>
            </div>
            <Slider
              value={forwardDays}
              onChange={setForwardDays}
              min={1}
              max={20}
              marks={{ 1: '1天', 5: '5天', 10: '10天', 20: '20天' }}
            />
          </Col>
          <Col xs={24} sm={24} md={6}>
            <Space style={{ width: '100%', marginTop: 8 }} direction="vertical">
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handlePredict}
                loading={loading}
                size="large"
                block
              >
                开始预测
              </Button>
              {prediction && (
                <Dropdown menu={{ items: exportMenuItems }} placement="bottom">
                  <Button icon={<DownloadOutlined />} block>
                    导出报告
                  </Button>
                </Dropdown>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text style={{ color: colors.textSecondary }}>正在分析数据...</Text>
          </div>
        </div>
      )}

      {prediction && !loading && (
        <Tabs
          items={[
            {
              key: 'overview',
              label: '预测概览',
              children: (
                <div className="animate-fade-in">
                  {/* 核心预测结果 */}
                  <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                    <Col xs={24} sm={12} lg={6}>
                      <Card hoverable>
                        <Statistic
                          title="当前价格"
                          value={prediction.stock_info.current_price}
                          precision={2}
                          prefix="¥"
                        />
                        <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                          {prediction.stock_name}
                        </Text>
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card hoverable>
                        <Statistic
                          title="方向预测"
                          value={prediction.direction.direction_label}
                          valueStyle={{ color: getDirectionColor(prediction.direction.direction) }}
                          prefix={getSignalIcon(prediction.direction.direction)}
                        />
                        <Progress
                          percent={prediction.direction.confidence * 100}
                          size="small"
                          strokeColor={getConfidenceColor(prediction.direction.confidence)}
                          format={() => `${(prediction.direction.confidence * 100).toFixed(0)}%置信度`}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card hoverable>
                        <Statistic
                          title="交易信号"
                          value={prediction.signal.signal_label}
                          valueStyle={{ color: getSignalColor(prediction.signal.signal) }}
                          prefix={getSignalIcon(prediction.signal.signal)}
                        />
                        <Progress
                          percent={prediction.signal.confidence * 100}
                          size="small"
                          strokeColor={getConfidenceColor(prediction.signal.confidence)}
                          format={() => `${(prediction.signal.confidence * 100).toFixed(0)}%置信度`}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card hoverable>
                        <Statistic
                          title="综合建议"
                          value={prediction.recommendation.action}
                          valueStyle={{
                            color: prediction.recommendation.score > 0 ? colors.success :
                                   prediction.recommendation.score < 0 ? colors.error : colors.neutral
                          }}
                        />
                        <Tag color={
                          prediction.recommendation.risk_level === '较高' ? 'red' :
                          prediction.recommendation.risk_level === '中等' ? 'orange' : 'green'
                        }>
                          风险{prediction.recommendation.risk_level}
                        </Tag>
                      </Card>
                    </Col>
                  </Row>

                  {/* 详细分析 */}
                  <Row gutter={[16, 16]}>
                    <Col xs={24} lg={12}>
                      <Card
                        title={
                          <Space>
                            <LineChartOutlined style={{ color: colors.primary }} />
                            <span>价格区间预测 ({forwardDays}天)</span>
                          </Space>
                        }
                      >
                        {prediction.price_range.price_ranges && prediction.price_range.price_ranges.map((range, idx) => (
                          <div key={idx} style={{ marginBottom: 16 }}>
                            <Text style={{ color: colors.textSecondary }}>
                              {(range.confidence * 100).toFixed(0)}% 置信区间
                            </Text>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                              <Tag color="green" style={{ margin: 0 }}>¥{range.lower.toFixed(2)}</Tag>
                              <div style={{ flex: 1, height: 4, background: 'linear-gradient(to right, #10b981, #64748b, #ef4444)', margin: '0 12px', borderRadius: 2 }} />
                              <Tag color="red" style={{ margin: 0 }}>¥{range.upper.toFixed(2)}</Tag>
                            </div>
                          </div>
                        ))}

                        <Divider style={{ margin: '16px 0' }} />

                        <Row gutter={16}>
                          <Col span={8}>
                            <Statistic
                              title="预期价格"
                              value={prediction.price_range.expected?.price || 0}
                              precision={2}
                              prefix="¥"
                              valueStyle={{ fontSize: 18 }}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="支撑位"
                              value={prediction.price_range.support_resistance?.support || 0}
                              precision={2}
                              prefix="¥"
                              valueStyle={{ fontSize: 18, color: colors.down }}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="阻力位"
                              value={prediction.price_range.support_resistance?.resistance || 0}
                              precision={2}
                              prefix="¥"
                              valueStyle={{ fontSize: 18, color: colors.up }}
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>

                    <Col xs={24} lg={12}>
                      <Card
                        title={
                          <Space>
                            <BulbOutlined style={{ color: colors.warning }} />
                            <span>信号分析</span>
                          </Space>
                        }
                      >
                        <List
                          size="small"
                          dataSource={prediction.signal.reasons}
                          renderItem={item => (
                            <List.Item style={{ padding: '10px 0' }}>
                              <Text>
                                <CheckCircleOutlined style={{ marginRight: 8, color: colors.success }} />
                                {item}
                              </Text>
                            </List.Item>
                          )}
                        />

                        <Divider style={{ margin: '16px 0' }} />

                        {prediction.signal.stop_loss && (
                          <Row gutter={16}>
                            <Col span={8}>
                              <Statistic
                                title="入场价"
                                value={prediction.signal.entry_price}
                                precision={2}
                                prefix="¥"
                                valueStyle={{ fontSize: 16 }}
                              />
                            </Col>
                            <Col span={8}>
                              <Statistic
                                title="止损位"
                                value={prediction.signal.stop_loss}
                                precision={2}
                                prefix="¥"
                                valueStyle={{ fontSize: 16, color: colors.error }}
                              />
                            </Col>
                            <Col span={8}>
                              <Statistic
                                title="止盈位"
                                value={prediction.signal.take_profit || 0}
                                precision={2}
                                prefix="¥"
                                valueStyle={{ fontSize: 16, color: colors.success }}
                              />
                            </Col>
                          </Row>
                        )}

                        {prediction.signal.risk_reward_ratio && (
                          <Alert
                            message={`盈亏比 ${prediction.signal.risk_reward_ratio.toFixed(2)}`}
                            type={prediction.signal.risk_reward_ratio >= 2 ? 'success' : 'warning'}
                            style={{ marginTop: 16 }}
                            showIcon
                          />
                        )}
                      </Card>
                    </Col>
                  </Row>

                  {/* 风险指标 - 带Tooltip说明 */}
                  <Card
                    title={
                      <Space>
                        <WarningOutlined style={{ color: colors.warning }} />
                        <span>风险评估</span>
                        <Tooltip title="风险指标帮助您评估投资的潜在风险，数值越高表示风险越大">
                          <QuestionCircleOutlined style={{ color: colors.textSecondary, cursor: 'help' }} />
                        </Tooltip>
                      </Space>
                    }
                    style={{ marginTop: 16 }}
                  >
                    <Row gutter={[16, 16]}>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="日波动率：衡量股价单日波动幅度，反映短期风险水平">
                          <div>
                            <Statistic
                              title={<span>日波动率 <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.risk.daily_volatility}
                              precision={2}
                              suffix="%"
                            />
                          </div>
                        </Tooltip>
                      </Col>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="年化波动率：将日波动率换算为年度指标，便于与其他投资品种比较。通常>40%为高波动，<20%为低波动">
                          <div>
                            <Statistic
                              title={<span>年化波动率 <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.risk.annualized_volatility}
                              precision={2}
                              suffix="%"
                            />
                          </div>
                        </Tooltip>
                      </Col>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="最大回撤：近20个交易日内从最高点到最低点的最大跌幅，反映最坏情况下的损失程度">
                          <div>
                            <Statistic
                              title={<span>20日最大回撤 <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.risk.max_drawdown_20d}
                              precision={2}
                              suffix="%"
                              valueStyle={{ color: colors.error }}
                            />
                          </div>
                        </Tooltip>
                      </Col>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="VaR (在险价值)：在95%置信度下，持有1天可能遭受的最大损失。例如VaR为-3%表示有5%概率损失超过3%">
                          <div>
                            <Statistic
                              title={<span>VaR (95%) <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.risk.var_95}
                              precision={2}
                              suffix="%"
                            />
                          </div>
                        </Tooltip>
                      </Col>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="CVaR (条件在险价值)：当损失超过VaR时的平均损失，比VaR更能反映极端风险">
                          <div>
                            <Statistic
                              title={<span>CVaR (95%) <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.risk.cvar_95}
                              precision={2}
                              suffix="%"
                            />
                          </div>
                        </Tooltip>
                      </Col>
                      <Col xs={12} sm={8} lg={4}>
                        <Tooltip title="波动率水平综合评估：高、中、低三档，帮助快速判断股票风险等级">
                          <div>
                            <Statistic
                              title={<span>波动率水平 <QuestionCircleOutlined style={{ fontSize: 12, color: colors.textSecondary }} /></span>}
                              value={prediction.price_range.risk_assessment?.volatility_level || '-'}
                            />
                          </div>
                        </Tooltip>
                      </Col>
                    </Row>
                  </Card>
                </div>
              )
            },
            {
              key: 'sentiment',
              label: '情感分析',
              children: sentiment && (
                <div className="animate-fade-in">
                  <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                    <Col xs={24} sm={8}>
                      <Card hoverable>
                        <Statistic
                          title="个股情绪"
                          value={sentiment.stock_sentiment?.label || '无数据'}
                          valueStyle={{
                            color: (sentiment.stock_sentiment?.score || 0) > 0 ? colors.success :
                              (sentiment.stock_sentiment?.score || 0) < 0 ? colors.error : colors.neutral
                          }}
                        />
                        <Progress
                          percent={Math.abs((sentiment.stock_sentiment?.score || 0) * 100)}
                          strokeColor={(sentiment.stock_sentiment?.score || 0) > 0 ? colors.success : colors.error}
                          format={() => `${((sentiment.stock_sentiment?.score || 0) * 100).toFixed(0)}分`}
                        />
                        <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                          分析{sentiment.stock_sentiment?.news_count || 0}条新闻
                        </Text>
                      </Card>
                    </Col>
                    <Col xs={24} sm={8}>
                      <Card hoverable>
                        <Statistic
                          title="市场情绪"
                          value={sentiment.market_sentiment?.label || '无数据'}
                          valueStyle={{
                            color: (sentiment.market_sentiment?.score || 0) > 0 ? colors.success :
                              (sentiment.market_sentiment?.score || 0) < 0 ? colors.error : colors.neutral
                          }}
                        />
                        <Progress
                          percent={Math.abs((sentiment.market_sentiment?.score || 0) * 100)}
                          strokeColor={(sentiment.market_sentiment?.score || 0) > 0 ? colors.success : colors.error}
                          format={() => `${((sentiment.market_sentiment?.score || 0) * 100).toFixed(0)}分`}
                        />
                        <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                          分析{sentiment.market_sentiment?.news_count || 0}条新闻
                        </Text>
                      </Card>
                    </Col>
                    <Col xs={24} sm={8}>
                      <Card hoverable>
                        <Statistic
                          title="综合情绪"
                          value={sentiment.combined?.label || '无数据'}
                          valueStyle={{
                            color: sentiment.combined?.color === 'green' ? colors.success :
                              sentiment.combined?.color === 'red' ? colors.error : colors.neutral
                          }}
                        />
                        <div style={{ marginTop: 8 }}>
                          <Tag color={sentiment.combined?.color || 'default'}>
                            得分: {((sentiment.combined?.score || 0) * 100).toFixed(0)}
                          </Tag>
                        </div>
                      </Card>
                    </Col>
                  </Row>

                  <Alert
                    message="情绪分析建议"
                    description={sentiment.recommendation}
                    type="info"
                    showIcon
                    icon={<InfoCircleOutlined />}
                    style={{ marginBottom: 24 }}
                  />

                  <Card title="相关新闻">
                    <List
                      dataSource={sentiment.top_news || []}
                      renderItem={item => (
                        <List.Item>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <Text style={{ flex: 1, marginRight: 12 }}>{item.title}</Text>
                              <Tag color={
                                item.sentiment?.level > 0 ? 'green' :
                                  item.sentiment?.level < 0 ? 'red' : 'default'
                              }>
                                {item.sentiment?.label}
                              </Tag>
                            </div>
                            <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
                              {item.source} · {item.publish_time}
                            </Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </Card>
                </div>
              )
            },
            {
              key: 'signals',
              label: '信号详情',
              children: prediction && (
                <div className="animate-fade-in">
                  <Row gutter={[16, 16]}>
                    {Object.entries(prediction.signal.components || {}).map(([key, comp]) => (
                      <Col xs={24} sm={12} lg={8} key={key}>
                        <Card
                          hoverable
                          title={
                            <Space>
                              <span>
                                {key === 'technical' && '技术指标'}
                                {key === 'trend' && '趋势分析'}
                                {key === 'momentum' && '动量分析'}
                                {key === 'volatility' && '波动率'}
                                {key === 'volume' && '成交量'}
                              </span>
                              <Tag color={comp.score > 0 ? 'green' : comp.score < 0 ? 'red' : 'default'}>
                                {comp.score > 0 ? '+' : ''}{(comp.score * 100).toFixed(0)}
                              </Tag>
                            </Space>
                          }
                        >
                          <List
                            size="small"
                            dataSource={comp.reasons}
                            renderItem={reason => (
                              <List.Item style={{ padding: '8px 0' }}>
                                <Text style={{ fontSize: 13 }}>{reason}</Text>
                              </List.Item>
                            )}
                          />
                        </Card>
                      </Col>
                    ))}
                  </Row>

                  <Card title="技术指标信号" style={{ marginTop: 16 }}>
                    <Space wrap>
                      {prediction.direction.signals && Object.entries(prediction.direction.signals).map(([key, value]) => (
                        <Tag key={key} style={{ margin: 4, padding: '4px 12px' }}>
                          {key}: {value}
                        </Tag>
                      ))}
                    </Space>
                  </Card>
                </div>
              )
            }
          ]}
        />
      )}

      {!prediction && !loading && (
        <Card style={{ textAlign: 'center', padding: '60px 20px' }}>
          <RobotOutlined style={{ fontSize: 64, color: colors.neutral, marginBottom: 24 }} />
          <Paragraph style={{ color: colors.textSecondary, fontSize: 16, marginBottom: 8 }}>
            选择股票并点击"开始预测"获取智能分析结果
          </Paragraph>
          <Paragraph style={{ color: colors.neutral, fontSize: 13 }}>
            综合技术指标、趋势分析、波动率评估、情感分析提供全方位预测
          </Paragraph>
        </Card>
      )}

    </div>
  )
}
