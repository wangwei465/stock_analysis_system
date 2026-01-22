import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import updateLocale from 'dayjs/plugin/updateLocale'
import App from './App'
import './styles/globals.css'

// 配置 dayjs 中文 locale，星期从周一开始
dayjs.extend(updateLocale)
dayjs.locale('zh-cn')
dayjs.updateLocale('zh-cn', {
  weekStart: 1, // 周一为一周的第一天
})

// 现代深色主题配置
const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    // 品牌色 - 使用现代蓝色
    colorPrimary: '#3b82f6',
    colorInfo: '#3b82f6',

    // 成功/警告/错误色
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',

    // 背景色系
    colorBgContainer: '#1e293b',
    colorBgElevated: '#334155',
    colorBgLayout: '#0f172a',
    colorBgSpotlight: '#1e293b',

    // 边框色
    colorBorder: '#334155',
    colorBorderSecondary: '#475569',

    // 文字色 - 提高对比度
    colorText: '#f1f5f9',
    colorTextSecondary: '#94a3b8',
    colorTextTertiary: '#64748b',
    colorTextQuaternary: '#475569',

    // 圆角
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,

    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,

    // 阴影
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2)',
    boxShadowSecondary: '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.3)',
  },
  components: {
    Card: {
      colorBgContainer: '#1e293b',
      colorBorderSecondary: '#334155',
    },
    Menu: {
      colorItemBg: 'transparent',
      colorItemBgSelected: 'rgba(59, 130, 246, 0.15)',
      colorItemTextSelected: '#3b82f6',
      colorItemBgHover: 'rgba(59, 130, 246, 0.1)',
    },
    Table: {
      colorBgContainer: '#1e293b',
      headerBg: '#0f172a',
      headerColor: '#f1f5f9',
      rowHoverBg: 'rgba(59, 130, 246, 0.08)',
    },
    Input: {
      colorBgContainer: '#0f172a',
      colorBorder: '#334155',
      activeBorderColor: '#3b82f6',
      hoverBorderColor: '#475569',
    },
    Select: {
      colorBgContainer: '#0f172a',
      colorBgElevated: '#1e293b',
      colorBorder: '#334155',
      optionSelectedBg: 'rgba(59, 130, 246, 0.15)',
    },
    Button: {
      primaryShadow: '0 2px 4px rgba(59, 130, 246, 0.3)',
    },
    Tabs: {
      colorBorderSecondary: '#334155',
      itemSelectedColor: '#3b82f6',
      itemHoverColor: '#60a5fa',
    },
    Slider: {
      trackBg: '#3b82f6',
      trackHoverBg: '#60a5fa',
      handleColor: '#3b82f6',
      handleActiveColor: '#60a5fa',
      railBg: '#334155',
      railHoverBg: '#475569',
    },
    Progress: {
      defaultColor: '#3b82f6',
    },
    Statistic: {
      contentFontSize: 24,
      titleFontSize: 14,
    },
    Tag: {
      defaultBg: '#334155',
      defaultColor: '#f1f5f9',
    },
    Alert: {
      colorInfoBg: 'rgba(59, 130, 246, 0.1)',
      colorInfoBorder: 'rgba(59, 130, 246, 0.3)',
      colorSuccessBg: 'rgba(16, 185, 129, 0.1)',
      colorSuccessBorder: 'rgba(16, 185, 129, 0.3)',
      colorWarningBg: 'rgba(245, 158, 11, 0.1)',
      colorWarningBorder: 'rgba(245, 158, 11, 0.3)',
      colorErrorBg: 'rgba(239, 68, 68, 0.1)',
      colorErrorBorder: 'rgba(239, 68, 68, 0.3)',
    },
    List: {
      colorSplit: '#334155',
    },
    Divider: {
      colorSplit: '#334155',
    },
    Spin: {
      colorPrimary: '#3b82f6',
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={darkTheme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
