import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import Sidebar from './components/common/Sidebar'
import Header from './components/common/Header'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Screener from './pages/Screener'
import Portfolio from './pages/Portfolio'
import Backtest from './pages/Backtest'
import Prediction from './pages/Prediction'

const { Content } = Layout

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Sidebar collapsed={sidebarCollapsed} onCollapse={setSidebarCollapsed} />
        <Layout style={{
          marginLeft: sidebarCollapsed ? 80 : 200,
          transition: 'margin-left 0.2s',
        }}>
          <Header />
          <Content style={{
            margin: 16,
            padding: 0,
            background: 'var(--color-bg-container, #1e293b)',
            borderRadius: 12,
            overflow: 'hidden'
          }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/stock/:code" element={<StockDetail />} />
              <Route path="/screener" element={<Screener />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/prediction" element={<Prediction />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </BrowserRouter>
  )
}

export default App
