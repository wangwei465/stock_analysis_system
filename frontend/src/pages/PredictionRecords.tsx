import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Typography,
  Select,
  Button,
  Popconfirm,
  message,
  Space,
  Tag
} from 'antd'
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  listPredictionRecords,
  updatePredictionRecord,
  deletePredictionRecord,
  PredictionRecord,
  AccuracyStatus
} from '../api/predictionRecords'

const { Title, Text } = Typography

const colors = {
  textSecondary: '#94a3b8',
}

const ACCURACY_OPTIONS: { label: string; value: AccuracyStatus }[] = [
  { label: '未验证', value: 'unknown' },
  { label: '准确', value: 'accurate' },
  { label: '不准确', value: 'inaccurate' },
]

const ACCURACY_COLOR: Record<AccuracyStatus, string> = {
  unknown: 'default',
  accurate: 'green',
  inaccurate: 'red',
}

export default function PredictionRecords() {
  const [records, setRecords] = useState<PredictionRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

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

  const sortedRecords = [...records].sort((a, b) => {
    const timeA = new Date(a.created_at || a.prediction_date).getTime() || 0
    const timeB = new Date(b.created_at || b.prediction_date).getTime() || 0
    return timeB - timeA
  })

  const columns = [
    {
      title: '日期',
      dataIndex: 'prediction_date',
      key: 'prediction_date',
      width: 120,
    },
    {
      title: '股票',
      key: 'stock',
      width: 180,
      render: (_: unknown, record: PredictionRecord) => (
        <div>
          <div>{record.stock_name}</div>
          <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
            {record.stock_code}
          </Text>
        </div>
      ),
    },
    {
      title: '预测周期',
      dataIndex: 'forward_days',
      key: 'forward_days',
      width: 110,
      render: (value: number) => `${value}天`,
    },
    {
      title: '当前价格',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 110,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '方向预测',
      dataIndex: 'direction',
      key: 'direction',
      width: 110,
    },
    {
      title: '交易信号',
      dataIndex: 'signal',
      key: 'signal',
      width: 110,
    },
    {
      title: '综合建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 120,
    },
    {
      title: '预期价格',
      dataIndex: 'expected_price',
      key: 'expected_price',
      width: 110,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '支撑位',
      dataIndex: 'support',
      key: 'support',
      width: 110,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '阻力位',
      dataIndex: 'resistance',
      key: 'resistance',
      width: 110,
      render: (value: number | null) => formatNumber(value),
    },
    {
      title: '是否准确',
      dataIndex: 'accuracy',
      key: 'accuracy',
      width: 130,
      render: (value: AccuracyStatus, record: PredictionRecord) => (
        <Space>
          <Tag color={ACCURACY_COLOR[value]}>{ACCURACY_OPTIONS.find((o) => o.value === value)?.label}</Tag>
          <Select
            size="small"
            value={value}
            onChange={(next) => handleAccuracyChange(record.id, next as AccuracyStatus)}
            options={ACCURACY_OPTIONS}
            disabled={updatingId === record.id}
            style={{ width: 100 }}
          />
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_: unknown, record: PredictionRecord) => (
        <Popconfirm
          title="确认删除该记录？"
          onConfirm={() => handleDeleteRecord(record.id)}
          okText="删除"
          cancelText="取消"
        >
          <Button type="link" danger loading={deletingId === record.id}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <RobotOutlined style={{ marginRight: 8 }} />
        预测记录
      </Title>

      <Card
        title="预测记录列表"
        extra={(
          <Button icon={<ReloadOutlined />} onClick={fetchRecords}>
            刷新
          </Button>
        )}
      >
        <Table
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={sortedRecords}
          loading={loading}
          pagination={{ pageSize: 8 }}
          scroll={{ x: 1400 }}
          locale={{ emptyText: '暂无预测记录' }}
        />
      </Card>
    </div>
  )
}
