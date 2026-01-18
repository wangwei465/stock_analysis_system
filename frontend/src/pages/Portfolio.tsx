import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Space,
  Typography,
  Statistic,
  Progress,
  Empty,
  Popconfirm,
  message,
  Select
} from 'antd'
import {
  FolderOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  getPortfolios,
  createPortfolio,
  updatePortfolio,
  deletePortfolio,
  addPosition,
  deletePosition,
  getPortfolioPerformance,
  Portfolio,
  PositionDetail,
  PortfolioPerformance
} from '../api/portfolio'
import { searchStocks } from '../api/stocks'

const { Title, Text } = Typography

export default function PortfolioPage() {
  const navigate = useNavigate()
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null)
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingPortfolio, setEditingPortfolio] = useState<Portfolio | null>(null)
  const [addPositionModalOpen, setAddPositionModalOpen] = useState(false)
  const [stockOptions, setStockOptions] = useState<{ value: string; label: string }[]>([])
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [positionForm] = Form.useForm()

  // Load portfolios
  useEffect(() => {
    loadPortfolios()
  }, [])

  // Load performance when portfolio selected
  useEffect(() => {
    if (selectedPortfolio) {
      loadPerformance(selectedPortfolio)
    }
  }, [selectedPortfolio])

  const loadPortfolios = async () => {
    try {
      const data = await getPortfolios()
      setPortfolios(data)
      if (data.length > 0 && !selectedPortfolio) {
        setSelectedPortfolio(data[0].id)
      }
    } catch (error) {
      console.error('Error loading portfolios:', error)
    }
  }

  const loadPerformance = async (id: number) => {
    setLoading(true)
    try {
      const data = await getPortfolioPerformance(id)
      setPerformance(data)
    } catch (error) {
      console.error('Error loading performance:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePortfolio = async (values: any) => {
    try {
      const portfolio = await createPortfolio(values)
      message.success('组合创建成功')
      setCreateModalOpen(false)
      form.resetFields()
      await loadPortfolios()
      setSelectedPortfolio(portfolio.id)
    } catch (error) {
      message.error('创建失败')
    }
  }

  const handleDeletePortfolio = async (id: number) => {
    try {
      await deletePortfolio(id)
      message.success('组合已删除')
      setSelectedPortfolio(null)
      setPerformance(null)
      await loadPortfolios()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleEditPortfolio = (portfolio: Portfolio, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingPortfolio(portfolio)
    editForm.setFieldsValue({
      name: portfolio.name,
      description: portfolio.description,
      initial_capital: portfolio.initial_capital
    })
    setEditModalOpen(true)
  }

  const handleUpdatePortfolio = async (values: any) => {
    if (!editingPortfolio) return
    try {
      await updatePortfolio(editingPortfolio.id, values)
      message.success('组合更新成功')
      setEditModalOpen(false)
      setEditingPortfolio(null)
      editForm.resetFields()

      // 并行刷新列表和性能数据
      const refreshTasks: Promise<void>[] = [loadPortfolios()]
      if (selectedPortfolio === editingPortfolio.id) {
        refreshTasks.push(loadPerformance(editingPortfolio.id))
      }
      await Promise.all(refreshTasks)
    } catch (error) {
      message.error('更新失败')
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
        value: `${s.code}|${s.name}`,
        label: `${s.code} - ${s.name}`
      })))
    } catch (error) {
      console.error('Search error:', error)
    }
  }

  const handleAddPosition = async (values: any) => {
    if (!selectedPortfolio) return

    try {
      const [code, name] = values.stock.split('|')
      await addPosition(selectedPortfolio, {
        code,
        name,
        quantity: values.quantity,
        avg_cost: values.avg_cost,
        buy_date: values.buy_date?.format('YYYY-MM-DD'),
        notes: values.notes
      })
      message.success('持仓添加成功')
      setAddPositionModalOpen(false)
      positionForm.resetFields()
      await loadPerformance(selectedPortfolio)
    } catch (error) {
      message.error('添加失败')
    }
  }

  const handleDeletePosition = async (positionId: number) => {
    if (!selectedPortfolio) return

    try {
      await deletePosition(selectedPortfolio, positionId)
      message.success('持仓已删除')
      await loadPerformance(selectedPortfolio)
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '股票',
      key: 'stock',
      width: 150,
      render: (_: any, record: PositionDetail) => (
        <div>
          <a onClick={() => navigate(`/stock/${record.code}`)}>{record.name}</a>
          <div style={{ fontSize: 12, color: '#888' }}>{record.code}</div>
        </div>
      )
    },
    {
      title: '持仓',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
      render: (v: number) => v.toLocaleString()
    },
    {
      title: '成本价',
      dataIndex: 'avg_cost',
      key: 'avg_cost',
      width: 80,
      render: (v: number) => v.toFixed(2)
    },
    {
      title: '现价',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 80,
      render: (v: number) => v.toFixed(2)
    },
    {
      title: '市值',
      dataIndex: 'value',
      key: 'value',
      width: 100,
      render: (v: number) => `¥${v.toLocaleString()}`
    },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (v: number, record: PositionDetail) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v.toLocaleString()}
          <div style={{ fontSize: 12 }}>
            ({record.pnl_pct >= 0 ? '+' : ''}{record.pnl_pct.toFixed(2)}%)
          </div>
        </span>
      )
    },
    {
      title: '当日盈亏',
      dataIndex: 'daily_pnl',
      key: 'daily_pnl',
      width: 100,
      render: (v: number, record: PositionDetail) => (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v.toLocaleString()}
          <div style={{ fontSize: 12 }}>
            ({record.daily_pnl_pct >= 0 ? '+' : ''}{record.daily_pnl_pct.toFixed(2)}%)
          </div>
        </span>
      )
    },
    {
      title: '占比',
      dataIndex: 'weight',
      key: 'weight',
      width: 100,
      render: (v: number) => <Progress percent={v} size="small" />
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      render: (_: any, record: PositionDetail) => (
        <Popconfirm
          title="确定删除该持仓？"
          onConfirm={() => handleDeletePosition(record.id)}
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ]

  return (
    <div style={{ padding: 16 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            <FolderOutlined style={{ marginRight: 8 }} />
            投资组合
          </Title>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            新建组合
          </Button>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* Portfolio List */}
        <Col xs={24} md={6}>
          <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
            {portfolios.length === 0 ? (
              <Empty description="暂无组合" />
            ) : (
              <div>
                {portfolios.map(p => (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPortfolio(p.id)}
                    style={{
                      padding: '12px',
                      marginBottom: 8,
                      borderRadius: 8,
                      cursor: 'pointer',
                      background: selectedPortfolio === p.id ? '#177ddc' : '#303030',
                      border: selectedPortfolio === p.id ? '1px solid #177ddc' : '1px solid #404040'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontWeight: 500 }}>{p.name}</div>
                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(e) => handleEditPortfolio(p, e)}
                        style={{ color: selectedPortfolio === p.id ? '#fff' : '#888' }}
                      />
                    </div>
                    <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                      初始资金: ¥{p.initial_capital.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>

        {/* Portfolio Detail */}
        <Col xs={24} md={18}>
          {selectedPortfolio && performance ? (
            <>
              {/* Summary Cards */}
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card style={{ background: '#1f1f1f', borderColor: '#303030', height: 120 }}>
                    <Statistic
                      title={<Text type="secondary">总市值</Text>}
                      value={performance.total_value}
                      prefix="¥"
                      precision={2}
                      valueStyle={{ color: '#fff', fontSize: 24 }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card style={{ background: '#1f1f1f', borderColor: '#303030', height: 120 }}>
                    <div>
                      <Text type="secondary">总盈亏</Text>
                      <div style={{
                        marginTop: 8,
                        color: performance.total_pnl >= 0 ? '#ef4444' : '#10b981',
                      }}>
                        <div style={{ fontSize: 24, fontWeight: 500, whiteSpace: 'nowrap' }}>
                          {performance.total_pnl >= 0 ? '+' : '-'}¥{Math.abs(performance.total_pnl).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div style={{ fontSize: 14, marginTop: 4 }}>
                          {performance.total_pnl >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                          {' '}{performance.total_pnl_pct >= 0 ? '+' : ''}{performance.total_pnl_pct.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card style={{ background: '#1f1f1f', borderColor: '#303030', height: 120 }}>
                    <Statistic
                      title={<Text type="secondary">可用资金</Text>}
                      value={performance.cash}
                      prefix="¥"
                      precision={2}
                      valueStyle={{ color: '#fff', fontSize: 24 }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card style={{ background: '#1f1f1f', borderColor: '#303030', height: 120 }}>
                    <Statistic
                      title={<Text type="secondary">持仓数量</Text>}
                      value={performance.positions.length}
                      suffix="只"
                      valueStyle={{ color: '#fff', fontSize: 24 }}
                    />
                  </Card>
                </Col>
              </Row>

              {/* Positions Table */}
              <Card
                style={{ background: '#1f1f1f', borderColor: '#303030' }}
                title={<Text style={{ color: '#fff' }}>持仓明细</Text>}
                extra={
                  <Space>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => setAddPositionModalOpen(true)}
                    >
                      添加持仓
                    </Button>
                    <Popconfirm
                      title="确定删除该组合？"
                      onConfirm={() => handleDeletePortfolio(selectedPortfolio)}
                    >
                      <Button danger icon={<DeleteOutlined />}>
                        删除组合
                      </Button>
                    </Popconfirm>
                  </Space>
                }
              >
                <Table
                  dataSource={performance.positions}
                  columns={columns}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                  size="small"
                />
              </Card>
            </>
          ) : (
            <Card style={{ background: '#1f1f1f', borderColor: '#303030' }}>
              <Empty description="请选择或创建一个投资组合" />
            </Card>
          )}
        </Col>
      </Row>

      {/* Create Portfolio Modal */}
      <Modal
        title="新建投资组合"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreatePortfolio}>
          <Form.Item
            name="name"
            label="组合名称"
            rules={[{ required: true, message: '请输入组合名称' }]}
          >
            <Input placeholder="如：价值投资组合" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="组合描述（可选）" />
          </Form.Item>
          <Form.Item
            name="initial_capital"
            label="初始资金"
            initialValue={1000000}
          >
            <InputNumber
              style={{ width: '100%' }}
              formatter={v => `¥ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={v => v!.replace(/¥\s?|(,*)/g, '') as any}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Position Modal */}
      <Modal
        title="添加持仓"
        open={addPositionModalOpen}
        onCancel={() => setAddPositionModalOpen(false)}
        onOk={() => positionForm.submit()}
      >
        <Form form={positionForm} layout="vertical" onFinish={handleAddPosition}>
          <Form.Item
            name="stock"
            label="股票"
            rules={[{ required: true, message: '请选择股票' }]}
          >
            <Select
              showSearch
              placeholder="搜索股票代码或名称"
              filterOption={false}
              onSearch={handleSearchStock}
              options={stockOptions}
            />
          </Form.Item>
          <Form.Item
            name="quantity"
            label="持仓数量"
            rules={[{ required: true, message: '请输入数量' }]}
          >
            <InputNumber style={{ width: '100%' }} min={100} step={100} />
          </Form.Item>
          <Form.Item
            name="avg_cost"
            label="成本价"
            rules={[{ required: true, message: '请输入成本价' }]}
          >
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
          </Form.Item>
          <Form.Item name="buy_date" label="买入日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea placeholder="备注（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Portfolio Modal */}
      <Modal
        title="编辑投资组合"
        open={editModalOpen}
        onCancel={() => {
          setEditModalOpen(false)
          setEditingPortfolio(null)
          editForm.resetFields()
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdatePortfolio}>
          <Form.Item
            name="name"
            label="组合名称"
            rules={[{ required: true, message: '请输入组合名称' }]}
          >
            <Input placeholder="如：价值投资组合" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="组合描述（可选）" />
          </Form.Item>
          <Form.Item
            name="initial_capital"
            label="初始资金"
          >
            <InputNumber
              style={{ width: '100%' }}
              formatter={v => `¥ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={v => v!.replace(/¥\s?|(,*)/g, '') as any}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
