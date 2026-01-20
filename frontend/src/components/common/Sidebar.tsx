import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  StockOutlined,
  FilterOutlined,
  FolderOutlined,
  ExperimentOutlined,
  RobotOutlined,
  UnorderedListOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Sider } = Layout

interface SidebarProps {
  collapsed: boolean
  onCollapse: (collapsed: boolean) => void
}

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/screener',
    icon: <FilterOutlined />,
    label: '选股器',
  },
  {
    key: '/portfolio',
    icon: <FolderOutlined />,
    label: '投资组合',
  },
  {
    key: '/backtest',
    icon: <ExperimentOutlined />,
    label: '策略回测',
  },
  {
    key: '/prediction',
    icon: <RobotOutlined />,
    label: '智能预测',
  },
  {
    key: '/prediction-records',
    icon: <UnorderedListOutlined />,
    label: '预测记录',
  },
]

export default function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      style={{
        background: 'var(--color-bg-container, #1e293b)',
        borderRight: '1px solid var(--color-border, #334155)',
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 100,
      }}
      trigger={
        <div style={{
          background: 'var(--color-bg-container, #1e293b)',
          borderTop: '1px solid var(--color-border, #334155)',
          color: 'var(--color-text-secondary, #94a3b8)',
          transition: 'all 0.2s',
        }}>
          {collapsed ? '›' : '‹'}
        </div>
      }
    >
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottom: '1px solid var(--color-border, #334155)',
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, transparent 100%)',
      }}>
        <StockOutlined style={{ fontSize: 26, color: 'var(--color-primary, #3b82f6)' }} />
        {!collapsed && (
          <span style={{
            marginLeft: 12,
            fontSize: 17,
            fontWeight: 600,
            color: 'var(--color-text-primary, #f1f5f9)',
            letterSpacing: '0.5px'
          }}>
            股票分析
          </span>
        )}
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{
          borderRight: 0,
          background: 'transparent',
          padding: '8px 0',
        }}
      />
    </Sider>
  )
}
