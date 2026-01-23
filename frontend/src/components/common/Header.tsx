import { useState } from 'react'
import { Layout, Input, AutoComplete, Space, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { searchStocks } from '../../api/stocks'
import type { StockSearchResult } from '../../types/stock'

const { Header: AntHeader } = Layout
const { Text } = Typography

export default function Header() {
  const [options, setOptions] = useState<{ value: string; label: React.ReactNode }[]>([])
  // loading 状态仅用于控制加载流程，UI 不显示
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSearch = async (value: string) => {
    if (!value || value.length < 1) {
      setOptions([])
      return
    }

    setLoading(true)
    try {
      const results = await searchStocks(value)
      setOptions(
        results.map((stock: StockSearchResult) => ({
          value: stock.code,
          label: (
            <Space>
              <Text strong style={{ color: 'var(--color-text-primary, #f1f5f9)' }}>
                {stock.code}
              </Text>
              <Text style={{ color: 'var(--color-text-secondary, #94a3b8)' }}>
                {stock.name}
              </Text>
              <Text style={{ fontSize: 12, color: 'var(--color-text-tertiary, #64748b)' }}>
                {stock.market}
              </Text>
            </Space>
          ),
        }))
      )
    } catch (error) {
      console.error('Search error:', error)
      setOptions([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (value: string) => {
    navigate(`/stock/${value}`)
  }

  return (
    <AntHeader style={{
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--color-bg-container, #1e293b)',
      borderBottom: '1px solid var(--color-border, #334155)',
    }}>
      <AutoComplete
        style={{ width: 420 }}
        options={options}
        onSearch={handleSearch}
        onSelect={handleSelect}
        placeholder="搜索股票代码或名称..."
      >
        <Input
          prefix={<SearchOutlined style={{ color: 'var(--color-text-tertiary, #64748b)' }} />}
          size="large"
          allowClear
          style={{
            background: 'var(--color-bg-base, #0f172a)',
            borderColor: 'var(--color-border, #334155)',
          }}
        />
      </AutoComplete>
      <Space>
        <Text style={{ color: 'var(--color-text-secondary, #94a3b8)', fontSize: 13 }}>
          A股智能分析系统
        </Text>
      </Space>
    </AntHeader>
  )
}
