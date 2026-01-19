import { useState, useEffect } from 'react'
import type { TableProps } from 'antd'
import type { SorterResult } from 'antd/es/table/interface'
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Select,
  InputNumber,
  Space,
  Tag,
  Typography,
  message,
  Tooltip,
  Dropdown,
  Checkbox
} from 'antd'
import {
  FilterOutlined,
  PlusOutlined,
  DeleteOutlined,
  SearchOutlined,
  DownOutlined,
  BankOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  filterStocks,
  getPresets,
  getScreenerFields,
  getMarketBoards,
  ScreenerCondition,
  ScreenerResult,
  ScreenerPreset,
  ScreenerField,
  MarketBoard
} from '../api/screener'

const { Title, Text } = Typography

const OPERATORS = [
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'between', label: '介于' },
]

// 板块颜色映射
const BOARD_COLORS: Record<string, string> = {
  '沪市主板': 'blue',
  '深市主板': 'cyan',
  '创业板': 'orange',
  '科创板': 'purple',
  '北交所': 'green',
}

export default function Screener() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [fields, setFields] = useState<ScreenerField[]>([])
  const [presets, setPresets] = useState<ScreenerPreset[]>([])
  const [boards, setBoards] = useState<MarketBoard[]>([])
  const [conditions, setConditions] = useState<ScreenerCondition[]>([])
  const [results, setResults] = useState<ScreenerResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [sortBy, setSortBy] = useState('market_cap')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedBoards, setSelectedBoards] = useState<string[]>([])
  const [excludeBoards, setExcludeBoards] = useState<string[]>([])
  const [initialized, setInitialized] = useState(false)

  // 预设条件配置
  const PRESET_CONFIGS: Record<string, { conditions: ScreenerCondition[]; sortBy: string; sortOrder: 'asc' | 'desc'; title: string }> = {
    gainers: {
      conditions: [{ field: 'change_pct', operator: 'gt', value: 0 }],
      sortBy: 'change_pct',
      sortOrder: 'desc',
      title: '涨幅榜'
    },
    losers: {
      conditions: [{ field: 'change_pct', operator: 'lt', value: 0 }],
      sortBy: 'change_pct',
      sortOrder: 'asc',
      title: '跌幅榜'
    },
    volume: {
      conditions: [{ field: 'volume_ratio', operator: 'gt', value: 2 }],
      sortBy: 'volume_ratio',
      sortOrder: 'desc',
      title: '放量异动'
    }
  }

  // Load fields, presets and boards
  useEffect(() => {
    const loadData = async () => {
      try {
        const [fieldsData, presetsData, boardsData] = await Promise.all([
          getScreenerFields(),
          getPresets(),
          getMarketBoards()
        ])
        setFields(fieldsData)
        setPresets(presetsData)
        setBoards(boardsData)
        setInitialized(true)
      } catch (error) {
        console.error('Error loading screener data:', error)
      }
    }
    loadData()
  }, [])

  // 处理 URL 预设参数
  useEffect(() => {
    if (!initialized) return

    const preset = searchParams.get('preset')
    if (preset && PRESET_CONFIGS[preset]) {
      const config = PRESET_CONFIGS[preset]
      setConditions(config.conditions)
      setSortBy(config.sortBy)
      setSortOrder(config.sortOrder)

      // 自动执行搜索
      const autoSearch = async () => {
        setLoading(true)
        try {
          const response = await filterStocks({
            conditions: config.conditions,
            sort_by: config.sortBy,
            sort_order: config.sortOrder,
            page: 1,
            page_size: pageSize
          })
          setResults(response.data)
          setTotal(response.total)
          setPage(1)
          message.success(`已加载${config.title}数据`)
        } catch (error) {
          console.error('Error filtering stocks:', error)
          message.error('加载失败')
        } finally {
          setLoading(false)
        }
      }
      autoSearch()
    }
  }, [initialized, searchParams])

  const handleSearch = async (currentPage = page) => {
    setLoading(true)
    try {
      const response = await filterStocks({
        conditions,
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        page_size: pageSize,
        market_boards: selectedBoards.length > 0 ? selectedBoards : undefined,
        exclude_boards: excludeBoards.length > 0 ? excludeBoards : undefined
      })
      setResults(response.data)
      setTotal(response.total)
      setPage(currentPage)
    } catch (error) {
      console.error('Error filtering stocks:', error)
      message.error('筛选失败')
    } finally {
      setLoading(false)
    }
  }

  const addCondition = () => {
    setConditions([
      ...conditions,
      { field: 'pe', operator: 'lt', value: 20 }
    ])
  }

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index))
  }

  const updateCondition = (index: number, updates: Partial<ScreenerCondition>) => {
    setConditions(conditions.map((c, i) => i === index ? { ...c, ...updates } : c))
  }

  const applyPreset = (preset: ScreenerPreset) => {
    setConditions(preset.conditions)
    setSelectedBoards(preset.market_boards || [])
    setExcludeBoards(preset.exclude_boards || [])
    message.success(`已应用预设：${preset.name}`)
  }

  const handleBoardChange = (boardKey: string, checked: boolean) => {
    if (checked) {
      setSelectedBoards([...selectedBoards, boardKey])
      // Remove from exclude if it was there
      setExcludeBoards(excludeBoards.filter(b => b !== boardKey))
    } else {
      setSelectedBoards(selectedBoards.filter(b => b !== boardKey))
    }
  }

  const handleExcludeBoardChange = (boardKey: string, checked: boolean) => {
    if (checked) {
      setExcludeBoards([...excludeBoards, boardKey])
      // Remove from selected if it was there
      setSelectedBoards(selectedBoards.filter(b => b !== boardKey))
    } else {
      setExcludeBoards(excludeBoards.filter(b => b !== boardKey))
    }
  }

  const clearBoardFilters = () => {
    setSelectedBoards([])
    setExcludeBoards([])
  }

  // Quick select: Main boards only
  const selectMainBoards = () => {
    setSelectedBoards(['sh_main', 'sz_main'])
    setExcludeBoards([])
  }

  // Quick select: Exclude STAR and GEM
  const excludeStarGem = () => {
    setSelectedBoards([])
    setExcludeBoards(['star', 'gem'])
  }

  // 处理表格排序变化
  const handleTableChange: TableProps<ScreenerResult>['onChange'] = (_pagination, _filters, sorter) => {
    const sorterResult = sorter as SorterResult<ScreenerResult>
    if (sorterResult.field && sorterResult.order) {
      const newSortBy = sorterResult.field as string
      const newSortOrder = sorterResult.order === 'ascend' ? 'asc' : 'desc'
      setSortBy(newSortBy)
      setSortOrder(newSortOrder)
      // 触发搜索
      setLoading(true)
      filterStocks({
        conditions,
        sort_by: newSortBy,
        sort_order: newSortOrder,
        page: 1,
        page_size: pageSize,
        market_boards: selectedBoards.length > 0 ? selectedBoards : undefined,
        exclude_boards: excludeBoards.length > 0 ? excludeBoards : undefined
      }).then(response => {
        setResults(response.data)
        setTotal(response.total)
        setPage(1)
      }).catch(error => {
        console.error('Error filtering stocks:', error)
        message.error('排序失败')
      }).finally(() => {
        setLoading(false)
      })
    }
  }

  const columns = [
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
      width: 100,
    },
    {
      title: '板块',
      dataIndex: 'board',
      key: 'board',
      width: 80,
      render: (board: string) => (
        <Tag color={BOARD_COLORS[board] || 'default'} style={{ margin: 0 }}>
          {board}
        </Tag>
      )
    },
    {
      title: '现价',
      dataIndex: 'price',
      key: 'price',
      width: 80,
      render: (v: number) => v?.toFixed(2) ?? '-'
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 90,
      sorter: true,
      render: (v: number) => v != null ? (
        <span style={{ color: v >= 0 ? '#ef4444' : '#10b981' }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      ) : '-'
    },
    {
      title: '市盈率',
      dataIndex: 'pe',
      key: 'pe',
      width: 80,
      sorter: true,
      render: (v: number) => v?.toFixed(2) ?? '-'
    },
    {
      title: '市净率',
      dataIndex: 'pb',
      key: 'pb',
      width: 80,
      sorter: true,
      render: (v: number) => v?.toFixed(2) ?? '-'
    },
    {
      title: '总市值(亿)',
      dataIndex: 'market_cap',
      key: 'market_cap',
      width: 100,
      sorter: true,
      render: (v: number) => v?.toFixed(2) ?? '-'
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      width: 80,
      sorter: true,
      render: (v: number) => v ? `${v.toFixed(2)}%` : '-'
    },
    {
      title: '量比',
      dataIndex: 'volume_ratio',
      key: 'volume_ratio',
      width: 70,
      sorter: true,
      render: (v: number) => v?.toFixed(2) ?? '-'
    },
  ]

  const presetMenuItems = presets.map((preset, index) => ({
    key: index.toString(),
    label: (
      <div onClick={() => applyPreset(preset)}>
        <div style={{ fontWeight: 500 }}>{preset.name}</div>
        <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
          {preset.description}
          {preset.market_boards && preset.market_boards.length > 0 && (
            <span style={{ marginLeft: 4 }}>
              [{boards.filter(b => preset.market_boards?.includes(b.key)).map(b => b.name).join(', ')}]
            </span>
          )}
        </div>
      </div>
    )
  }))

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <FilterOutlined style={{ marginRight: 8, color: 'var(--color-primary)' }} />
        选股筛选
      </Title>

      {/* Board Filter */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Space>
              <BankOutlined style={{ color: 'var(--color-primary)' }} />
              <Text strong>板块筛选：</Text>
            </Space>
          </Col>
          <Col flex="auto">
            <Space wrap size={[8, 8]}>
              {boards.map(board => {
                const isSelected = selectedBoards.includes(board.key)
                const isExcluded = excludeBoards.includes(board.key)
                return (
                  <Tooltip key={board.key} title={board.description}>
                    <Tag.CheckableTag
                      checked={isSelected}
                      onChange={(checked) => handleBoardChange(board.key, checked)}
                      style={{
                        padding: '4px 12px',
                        border: isExcluded ? '1px dashed #ef4444' : isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                        background: isSelected ? 'rgba(59, 130, 246, 0.15)' : isExcluded ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                        color: isSelected ? 'var(--color-primary)' : isExcluded ? '#ef4444' : 'var(--color-text-secondary)',
                        textDecoration: isExcluded ? 'line-through' : 'none'
                      }}
                    >
                      {board.name}
                    </Tag.CheckableTag>
                  </Tooltip>
                )
              })}
            </Space>
          </Col>
          <Col>
            <Space>
              <Button size="small" onClick={selectMainBoards}>
                仅主板
              </Button>
              <Button size="small" onClick={excludeStarGem}>
                排除科创/创业
              </Button>
              <Button size="small" onClick={clearBoardFilters}>
                清除
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Exclude boards */}
        <Row style={{ marginTop: 12 }}>
          <Col>
            <Space>
              <Text style={{ color: 'var(--color-text-tertiary)' }}>排除板块：</Text>
              {boards.map(board => (
                <Checkbox
                  key={board.key}
                  checked={excludeBoards.includes(board.key)}
                  onChange={(e) => handleExcludeBoardChange(board.key, e.target.checked)}
                  style={{ color: excludeBoards.includes(board.key) ? '#ef4444' : 'var(--color-text-secondary)' }}
                >
                  {board.name}
                </Checkbox>
              ))}
            </Space>
          </Col>
        </Row>

        {/* Current selection summary */}
        {(selectedBoards.length > 0 || excludeBoards.length > 0) && (
          <Row style={{ marginTop: 12 }}>
            <Col>
              <Space>
                {selectedBoards.length > 0 && (
                  <Text style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>
                    包含: {boards.filter(b => selectedBoards.includes(b.key)).map(b => b.name).join(', ')}
                  </Text>
                )}
                {excludeBoards.length > 0 && (
                  <Text style={{ color: '#ef4444', fontSize: 12 }}>
                    排除: {boards.filter(b => excludeBoards.includes(b.key)).map(b => b.name).join(', ')}
                  </Text>
                )}
              </Space>
            </Col>
          </Row>
        )}
      </Card>

      {/* Condition Builder */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <Button icon={<PlusOutlined />} onClick={addCondition}>
                添加条件
              </Button>
              <Dropdown menu={{ items: presetMenuItems }} trigger={['click']}>
                <Button>
                  预设条件 <DownOutlined />
                </Button>
              </Dropdown>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                value={sortBy}
                onChange={setSortBy}
                style={{ width: 120 }}
                options={fields.map(f => ({ value: f.field, label: f.name }))}
              />
              <Select
                value={sortOrder}
                onChange={setSortOrder}
                style={{ width: 80 }}
                options={[
                  { value: 'desc', label: '降序' },
                  { value: 'asc', label: '升序' },
                ]}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={() => handleSearch(1)}
                loading={loading}
              >
                筛选
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Conditions List */}
        {conditions.map((condition, index) => (
          <Row key={index} gutter={8} style={{ marginBottom: 8 }} align="middle">
            <Col>
              <Select
                value={condition.field}
                onChange={(value) => updateCondition(index, { field: value })}
                style={{ width: 120 }}
                options={fields.map(f => ({ value: f.field, label: f.name }))}
              />
            </Col>
            <Col>
              <Select
                value={condition.operator}
                onChange={(value) => updateCondition(index, { operator: value })}
                style={{ width: 100 }}
                options={OPERATORS}
              />
            </Col>
            <Col>
              {condition.operator === 'between' ? (
                <Space>
                  <InputNumber
                    value={(condition.value as number[])?.[0]}
                    onChange={(v) => updateCondition(index, {
                      value: [v ?? 0, (condition.value as number[])?.[1] ?? 0]
                    })}
                    style={{ width: 80 }}
                  />
                  <Text style={{ color: 'var(--color-text-tertiary)' }}>至</Text>
                  <InputNumber
                    value={(condition.value as number[])?.[1]}
                    onChange={(v) => updateCondition(index, {
                      value: [(condition.value as number[])?.[0] ?? 0, v ?? 0]
                    })}
                    style={{ width: 80 }}
                  />
                </Space>
              ) : (
                <InputNumber
                  value={condition.value as number}
                  onChange={(v) => updateCondition(index, { value: v ?? 0 })}
                  style={{ width: 100 }}
                />
              )}
            </Col>
            <Col>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeCondition(index)}
              />
            </Col>
          </Row>
        ))}

        {conditions.length === 0 && (
          <div style={{ textAlign: 'center', padding: 20, color: 'var(--color-text-tertiary)' }}>
            点击"添加条件"或选择"预设条件"开始筛选（可直接点击筛选按钮使用板块筛选）
          </div>
        )}
      </Card>

      {/* Results Table */}
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Text>
            共找到 <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{total}</span> 只股票
          </Text>
        </div>
        <Table
          dataSource={results}
          columns={columns}
          rowKey="code"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPageSize(ps)
              handleSearch(p)
            }
          }}
          size="small"
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}
