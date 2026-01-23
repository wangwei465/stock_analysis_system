import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Table,
  Typography,
  Select,
  Button,
  Popconfirm,
  message,
  Space,
  Tag,
  Input,
  Row,
  Col
} from 'antd'
import type { TableProps } from 'antd'
import { RobotOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import {
  listPredictionRecords,
  updatePredictionRecord,
  deletePredictionRecord,
  PredictionRecord,
  AccuracyStatus
} from '../api/predictionRecords'

const { Title, Text } = Typography

const ACCURACY_OPTIONS: { label: string; value: AccuracyStatus | 'all' }[] = [
  { label: '全部', value: 'all' },
  { label: '未验证', value: 'unknown' },
  { label: '准确', value: 'accurate' },
  { label: '不准确', value: 'inaccurate' },
]

const DIRECTION_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '看涨', value: '看涨' },
  { label: '看跌', value: '看跌' },
  { label: '震荡', value: '震荡' },
]

const RECOMMENDATION_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '强烈买入', value: '强烈买入' },
  { label: '买入', value: '买入' },
  { label: '持有', value: '持有' },
  { label: '卖出', value: '卖出' },
  { label: '强烈卖出', value: '强烈卖出' },
]

const DIRECTION_COLOR: Record<string, string> = {
  '看涨': 'green',
  '看跌': 'red',
  '震荡': 'orange',
}

const RECOMMENDATION_COLOR: Record<string, string> = {
  '强烈买入': 'green',
  '买入': 'cyan',
  '持有': 'blue',
  '卖出': 'orange',
  '强烈卖出': 'red',
}

export default function PredictionRecords() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<PredictionRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // 筛选状态
  const [keyword, setKeyword] = useState('')
  const [directionFilter, setDirectionFilter] = useState<string>('all')
  const [recommendationFilter, setRecommendationFilter] = useState<string>('all')
  const [accuracyFilter, setAccuracyFilter] = useState<string>('all')

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const data = await listPredictionRecords()
      setRecords(data)
    } catch (error) {
      console.error('Prediction records fetch error:', error)
      message.error('预测记录加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRecords()
  }, [])

  // 筛选后的数据
  const filteredRecords = useMemo(() => {
    return records.filter(record => {
      if (keyword && !record.stock_name.includes(keyword) && !record.stock_code.includes(keyword)) {
        return false
      }
      if (directionFilter !== 'all' && record.direction !== directionFilter) {
        return false
      }
      if (recommendationFilter !== 'all' && record.recommendation !== recommendationFilter) {
        return false
      }
      if (accuracyFilter !== 'all' && record.accuracy !== accuracyFilter) {
        return false
      }
      return true
    })
  }, [records, keyword, directionFilter, recommendationFilter, accuracyFilter])

  const formatNumber = (value: number | null) => {
    if (value === null) return '-'
    return value.toFixed(2)
  }

  const handleAccuracyChange = async (recordId: number, value: AccuracyStatus) => {
    setUpdatingId(recordId)
    try {
      const updated = await updatePredictionRecord(recordId, { accuracy: value })
      setRecords((prev) => prev.map((record) => (record.id === updated.id ? updated : record)))
      message.success('已更新准确度')
    } catch (error) {
      console.error('Prediction record update error:', error)
      message.error('准确度更新失败')
    } finally {
      setUpdatingId(null)
    }
  }

  const handleDeleteRecord = async (recordId: number) => {
    setDeletingId(recordId)
    try {
      await deletePredictionRecord(recordId)
      setRecords((prev) => prev.filter((record) => record.id !== recordId))
      message.success('记录已删除')
    } catch (error) {
      console.error('Prediction record delete error:', error)
      message.error('删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  const handleStockClick = (code: string) => {
    navigate(`/stock/${code}`)
  }

  const columns: TableProps<PredictionRecord>['columns'] = [
    {
      title: '日期',
      dataIndex: 'prediction_date',
      key: 'prediction_date',
      width: 110,
      sorter: (a, b) => new Date(a.prediction_date).getTime() - new Date(b.prediction_date).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: '股票',
      key: 'stock',
      width: 160,
      render: (_: unknown, record: PredictionRecord) => (
        <div
          style={{ cursor: 'pointer' }}
          onClick={() => handleStockClick(record.stock_code)}
        >
          <div style={{ color: '#3b82f6', fontWeight: 500 }}>{record.stock_name}</div>
          <Text style={{ color: '#94a3b8', fontSize: 12 }}>{record.stock_code}</Text>
        </div>
      ),
    },
    {
      title: '周期',
      dataIndex: 'forward_days',
      key: 'forward_days',
      width: 70,
      render: (value: number) => `${value}天`,
    },
    {
      title: '当前价',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 80,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '方向预测',
      dataIndex: 'direction',
      key: 'direction',
      width: 90,
      sorter: (a, b) => a.direction.localeCompare(b.direction),
      render: (value: string) => (
        <Tag color={DIRECTION_COLOR[value] || 'default'}>{value}</Tag>
      ),
    },
    {
      title: '信号',
      dataIndex: 'signal',
      key: 'signal',
      width: 80,
    },
    {
      title: '综合建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 100,
      sorter: (a, b) => a.recommendation.localeCompare(b.recommendation),
      render: (value: string) => (
        <Tag color={RECOMMENDATION_COLOR[value] || 'default'}>{value}</Tag>
      ),
    },
    {
      title: '预期价',
      dataIndex: 'expected_price',
      key: 'expected_price',
      width: 80,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '支撑/阻力',
      key: 'support_resistance',
      width: 110,
      render: (_: unknown, record: PredictionRecord) => (
        <div style={{ fontSize: 12 }}>
          <span style={{ color: '#10b981' }}>{formatNumber(record.support)}</span>
          <span style={{ color: '#94a3b8' }}> / </span>
          <span style={{ color: '#ef4444' }}>{formatNumber(record.resistance)}</span>
        </div>
      ),
    },
    {
      title: '是否准确',
      dataIndex: 'accuracy',
      key: 'accuracy',
      width: 150,
      sorter: (a, b) => a.accuracy.localeCompare(b.accuracy),
      render: (value: AccuracyStatus, record: PredictionRecord) => (
        <Select
          size="small"
          value={value}
          onChange={(next) => handleAccuracyChange(record.id, next as AccuracyStatus)}
          disabled={updatingId === record.id}
          style={{ width: 90 }}
        >
          <Select.Option value="unknown"><Tag color="default">未验证</Tag></Select.Option>
          <Select.Option value="accurate"><Tag color="green">准确</Tag></Select.Option>
          <Select.Option value="inaccurate"><Tag color="red">不准确</Tag></Select.Option>
        </Select>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 70,
      render: (_: unknown, record: PredictionRecord) => (
        <Popconfirm
          title="确认删除该记录？"
          onConfirm={() => handleDeleteRecord(record.id)}
          okText="删除"
          cancelText="取消"
        >
          <Button type="link" danger size="small" loading={deletingId === record.id}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  const resetFilters = () => {
    setKeyword('')
    setDirectionFilter('all')
    setRecommendationFilter('all')
    setAccuracyFilter('all')
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        <RobotOutlined style={{ marginRight: 8 }} />
        预测记录
      </Title>

      {/* 筛选区域 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="搜索股票名称/代码"
              prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="方向预测"
              value={directionFilter}
              onChange={setDirectionFilter}
              options={DIRECTION_OPTIONS}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="综合建议"
              value={recommendationFilter}
              onChange={setRecommendationFilter}
              options={RECOMMENDATION_OPTIONS}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="是否准确"
              value={accuracyFilter}
              onChange={setAccuracyFilter}
              options={ACCURACY_OPTIONS}
            />
          </Col>
          <Col xs={12} sm={6} md={6}>
            <Space>
              <Button onClick={resetFilters}>重置</Button>
              <Button icon={<ReloadOutlined />} onClick={fetchRecords}>刷新</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <Card
        size="small"
        title={<span>共 {filteredRecords.length} 条记录</span>}
      >
        <Table
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={filteredRecords}
          loading={loading}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
            showQuickJumper: true,
          }}
          scroll={{ x: 1200 }}
          locale={{ emptyText: '暂无预测记录' }}
        />
      </Card>
    </div>
  )
}
