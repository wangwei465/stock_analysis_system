import { useState, useEffect, useRef } from 'react'
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
  Select,
  Tabs,
  Tag
} from 'antd'
import {
  FolderOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  UploadOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  getPortfolios,
  createPortfolio,
  updatePortfolio,
  deletePortfolio,
  addPosition,
  updatePosition,
  deletePosition,
  getPortfolioPerformance,
  getTransactions,
  createTransaction,
  deleteTransaction,
  batchDeleteTransactions,
  importTransactions,
  getExportTransactionsUrl,
  Portfolio,
  PositionDetail,
  PortfolioPerformance,
  Transaction,
  TradeType
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
  const [editPositionModalOpen, setEditPositionModalOpen] = useState(false)
  const [editingPosition, setEditingPosition] = useState<PositionDetail | null>(null)
  const [stockOptions, setStockOptions] = useState<{ value: string; label: string }[]>([])
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [positionForm] = Form.useForm()
  const [editPositionForm] = Form.useForm()
  const [transactionForm] = Form.useForm()

  // Transaction states
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [transactionsLoading, setTransactionsLoading] = useState(false)
  const [addTransactionModalOpen, setAddTransactionModalOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('positions')
  const [selectedTradeType, setSelectedTradeType] = useState<TradeType>('BUY')
  const [selectedTransactionIds, setSelectedTransactionIds] = useState<number[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load portfolios
  useEffect(() => {
    loadPortfolios()
  }, [])

  // Load performance when portfolio selected
  useEffect(() => {
    if (selectedPortfolio) {
      loadPerformance(selectedPortfolio)
      loadTransactions(selectedPortfolio)
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

  const loadTransactions = async (id: number) => {
    setTransactionsLoading(true)
    try {
      const data = await getTransactions(id, 100)
      setTransactions(data)
    } catch (error) {
      console.error('Error loading transactions:', error)
    } finally {
      setTransactionsLoading(false)
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

  const handleEditPosition = (position: PositionDetail) => {
    setEditingPosition(position)
    editPositionForm.setFieldsValue({
      quantity: position.quantity,
      avg_cost: position.avg_cost
    })
    setEditPositionModalOpen(true)
  }

  const handleUpdatePosition = async (values: any) => {
    if (!selectedPortfolio || !editingPosition) return

    try {
      await updatePosition(selectedPortfolio, editingPosition.id, {
        quantity: values.quantity,
        avg_cost: values.avg_cost
      })
      message.success('持仓更新成功')
      setEditPositionModalOpen(false)
      setEditingPosition(null)
      editPositionForm.resetFields()
      await loadPerformance(selectedPortfolio)
    } catch (error) {
      message.error('更新失败')
    }
  }

  const handleAddTransaction = async (values: any) => {
    if (!selectedPortfolio) return

    try {
      const [code, name] = values.stock.split('|')
      const isBuySell = ['BUY', 'SELL'].includes(values.trade_type)
      await createTransaction(selectedPortfolio, {
        code,
        name,
        trade_type: values.trade_type,
        quantity: isBuySell ? values.quantity : undefined,
        price: isBuySell ? values.price : values.amount,
        commission: values.commission || 0,
        trade_date: values.trade_date?.format('YYYY-MM-DD')
      })
      message.success('交易记录添加成功')
      setAddTransactionModalOpen(false)
      transactionForm.resetFields()
      setSelectedTradeType('BUY')
      await Promise.all([loadTransactions(selectedPortfolio), loadPerformance(selectedPortfolio)])
    } catch (error) {
      message.error('添加失败')
    }
  }

  const handleDeleteTransaction = async (transactionId: number) => {
    if (!selectedPortfolio) return

    try {
      await deleteTransaction(selectedPortfolio, transactionId)
      message.success('交易记录已删除')
      setSelectedTransactionIds(ids => ids.filter(id => id !== transactionId))
      await Promise.all([loadTransactions(selectedPortfolio), loadPerformance(selectedPortfolio)])
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleBatchDeleteTransactions = async () => {
    if (!selectedPortfolio || selectedTransactionIds.length === 0) return

    try {
      const result = await batchDeleteTransactions(selectedPortfolio, selectedTransactionIds)
      message.success(`成功删除 ${result.deleted} 条交易记录`)
      setSelectedTransactionIds([])
      await Promise.all([loadTransactions(selectedPortfolio), loadPerformance(selectedPortfolio)])
    } catch (error) {
      message.error('批量删除失败')
    }
  }

  const handleImportTransactions = async (file: File) => {
    if (!selectedPortfolio) return

    try {
      const result = await importTransactions(selectedPortfolio, file)
      if (result.total_errors > 0) {
        message.warning(`导入完成：成功 ${result.imported} 条，失败 ${result.total_errors} 条`)
      } else {
        message.success(`成功导入 ${result.imported} 条交易记录`)
      }
      await Promise.all([loadTransactions(selectedPortfolio), loadPerformance(selectedPortfolio)])
    } catch (error) {
      message.error('导入失败')
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
      width: 100,
      render: (_: any, record: PositionDetail) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEditPosition(record)}
          />
          <Popconfirm
            title="确定删除该持仓？"
            onConfirm={() => handleDeletePosition(record.id)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
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
                <Tabs
                  activeKey={activeTab}
                  onChange={setActiveTab}
                  items={[
                    {
                      key: 'positions',
                      label: '持仓明细',
                      children: (
                        <>
                          <div style={{ marginBottom: 16 }}>
                            <Button
                              icon={<PlusOutlined />}
                              onClick={() => setAddPositionModalOpen(true)}
                            >
                              添加持仓
                            </Button>
                          </div>
                          <Table
                            dataSource={performance.positions}
                            columns={columns}
                            rowKey="id"
                            loading={loading}
                            pagination={false}
                            size="small"
                          />
                        </>
                      )
                    },
                    {
                      key: 'transactions',
                      label: '交易记录',
                      children: (
                        <>
                          <div style={{ marginBottom: 16 }}>
                            <Space>
                              <Button
                                icon={<PlusOutlined />}
                                onClick={() => setAddTransactionModalOpen(true)}
                              >
                                添加交易
                              </Button>
                              <input
                                type="file"
                                ref={fileInputRef}
                                accept=".csv"
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                  const file = e.target.files?.[0]
                                  if (file) {
                                    handleImportTransactions(file)
                                    e.target.value = ''
                                  }
                                }}
                              />
                              <Button
                                icon={<UploadOutlined />}
                                onClick={() => fileInputRef.current?.click()}
                              >
                                导入CSV
                              </Button>
                              <Button
                                icon={<DownloadOutlined />}
                                onClick={() => window.open(getExportTransactionsUrl(selectedPortfolio), '_blank')}
                              >
                                导出CSV
                              </Button>
                              {selectedTransactionIds.length > 0 && (
                                <Popconfirm
                                  title={`确定删除选中的 ${selectedTransactionIds.length} 条交易记录？`}
                                  onConfirm={handleBatchDeleteTransactions}
                                >
                                  <Button danger icon={<DeleteOutlined />}>
                                    批量删除 ({selectedTransactionIds.length})
                                  </Button>
                                </Popconfirm>
                              )}
                            </Space>
                          </div>
                          <Table
                            dataSource={transactions}
                            columns={[
                              {
                                title: '日期',
                                dataIndex: 'trade_date',
                                key: 'trade_date',
                                width: 100,
                              },
                              {
                                title: '股票代码',
                                dataIndex: 'code',
                                key: 'code',
                                width: 100,
                              },
                              {
                                title: '类型',
                                dataIndex: 'trade_type',
                                key: 'trade_type',
                                width: 80,
                                render: (v: string) => {
                                  const typeMap: Record<string, { color: string; label: string }> = {
                                    BUY: { color: 'red', label: '买入' },
                                    SELL: { color: 'green', label: '卖出' },
                                    DIVIDEND: { color: 'gold', label: '分红' },
                                    TAX: { color: 'orange', label: '税补缴' }
                                  }
                                  const t = typeMap[v] || { color: 'default', label: v }
                                  return <Tag color={t.color}>{t.label}</Tag>
                                }
                              },
                              {
                                title: '数量',
                                dataIndex: 'quantity',
                                key: 'quantity',
                                width: 80,
                                render: (v: number | null) => v ? v.toLocaleString() : '-'
                              },
                              {
                                title: '价格/金额',
                                dataIndex: 'price',
                                key: 'price',
                                width: 100,
                                render: (v: number, record: Transaction) => {
                                  if (['DIVIDEND', 'TAX'].includes(record.trade_type)) {
                                    return `¥${v.toLocaleString()}`
                                  }
                                  return v.toFixed(2)
                                }
                              },
                              {
                                title: '总金额',
                                key: 'amount',
                                width: 100,
                                render: (_: any, record: Transaction) => {
                                  if (['DIVIDEND', 'TAX'].includes(record.trade_type)) {
                                    return '-'
                                  }
                                  return `¥${((record.quantity || 0) * record.price).toLocaleString()}`
                                }
                              },
                              {
                                title: '佣金',
                                dataIndex: 'commission',
                                key: 'commission',
                                width: 80,
                                render: (v: number) => v > 0 ? `¥${v.toFixed(2)}` : '-'
                              },
                              {
                                title: '操作',
                                key: 'action',
                                width: 60,
                                render: (_: any, record: Transaction) => (
                                  <Popconfirm
                                    title="确定删除该交易记录？"
                                    onConfirm={() => handleDeleteTransaction(record.id)}
                                  >
                                    <Button type="text" danger icon={<DeleteOutlined />} />
                                  </Popconfirm>
                                )
                              }
                            ]}
                            rowKey="id"
                            loading={transactionsLoading}
                            pagination={{ pageSize: 20 }}
                            size="small"
                            rowSelection={{
                              selectedRowKeys: selectedTransactionIds,
                              onChange: (keys) => setSelectedTransactionIds(keys as number[])
                            }}
                          />
                        </>
                      )
                    }
                  ]}
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

      {/* Edit Position Modal */}
      <Modal
        title={`编辑持仓 - ${editingPosition?.name || ''}`}
        open={editPositionModalOpen}
        onCancel={() => {
          setEditPositionModalOpen(false)
          setEditingPosition(null)
          editPositionForm.resetFields()
        }}
        onOk={() => editPositionForm.submit()}
      >
        <Form form={editPositionForm} layout="vertical" onFinish={handleUpdatePosition}>
          <Form.Item
            name="quantity"
            label="持仓数量"
            rules={[{ required: true, message: '请输入数量' }]}
          >
            <InputNumber style={{ width: '100%' }} min={1} step={100} />
          </Form.Item>
          <Form.Item
            name="avg_cost"
            label="成本价"
            rules={[{ required: true, message: '请输入成本价' }]}
          >
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
          </Form.Item>
          {editingPosition && (
            <div style={{ marginBottom: 16, padding: 12, background: '#303030', borderRadius: 8 }}>
              <Text type="secondary">当前市价: ¥{editingPosition.current_price.toFixed(2)}</Text>
              <br />
              <Text type="secondary">
                预计盈亏: {(() => {
                  const qty = editPositionForm.getFieldValue('quantity') || editingPosition.quantity
                  const cost = editPositionForm.getFieldValue('avg_cost') || editingPosition.avg_cost
                  const pnl = qty * editingPosition.current_price - qty * cost
                  return (
                    <span style={{ color: pnl >= 0 ? '#ef4444' : '#10b981' }}>
                      {pnl >= 0 ? '+' : ''}¥{pnl.toFixed(2)}
                    </span>
                  )
                })()}
              </Text>
            </div>
          )}
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

      {/* Add Transaction Modal */}
      <Modal
        title="添加交易记录"
        open={addTransactionModalOpen}
        onCancel={() => {
          setAddTransactionModalOpen(false)
          transactionForm.resetFields()
          setSelectedTradeType('BUY')
        }}
        onOk={() => transactionForm.submit()}
      >
        <Form form={transactionForm} layout="vertical" onFinish={handleAddTransaction}>
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
            name="trade_type"
            label="交易类型"
            rules={[{ required: true, message: '请选择交易类型' }]}
            initialValue="BUY"
          >
            <Select
              onChange={(v: TradeType) => setSelectedTradeType(v)}
              options={[
                { value: 'BUY', label: '买入' },
                { value: 'SELL', label: '卖出' },
                { value: 'DIVIDEND', label: '分红' },
                { value: 'TAX', label: '股息红利税补缴' }
              ]}
            />
          </Form.Item>
          {['BUY', 'SELL'].includes(selectedTradeType) && (
            <>
              <Form.Item
                name="quantity"
                label="数量"
                rules={[{ required: true, message: '请输入数量' }]}
              >
                <InputNumber style={{ width: '100%' }} min={100} step={100} />
              </Form.Item>
              <Form.Item
                name="price"
                label="价格"
                rules={[{ required: true, message: '请输入价格' }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
              </Form.Item>
              <Form.Item name="commission" label="佣金">
                <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
              </Form.Item>
            </>
          )}
          {['DIVIDEND', 'TAX'].includes(selectedTradeType) && (
            <Form.Item
              name="amount"
              label={selectedTradeType === 'DIVIDEND' ? '分红金额' : '税补缴金额'}
              rules={[{ required: true, message: '请输入金额' }]}
            >
              <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} prefix="¥" />
            </Form.Item>
          )}
          <Form.Item name="trade_date" label="日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
