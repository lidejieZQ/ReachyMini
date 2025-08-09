import { useState, useEffect } from 'react'
import './App.css'
import HealthCheck from './components/HealthCheck'

interface SystemStatus {
  running: boolean;
  components: Record<string, boolean>;
  uptime?: number;
}

interface SystemInfo {
  message: string;
  version: string;
  status: string;
  docs?: string;
  health: string;
}

function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname)
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 监听路由变化
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname)
    }
    
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const fetchSystemInfo = async () => {
    try {
      const response = await fetch('/system/info')
      if (!response.ok) {
        throw new Error('Failed to fetch system info')
      }
      const data = await response.json()
      setSystemInfo(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/system/status')
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data)
      }
    } catch (err) {
      console.warn('Failed to fetch system status:', err)
    }
  }

  useEffect(() => {
    // 只在主页面加载数据
    if (currentPath === '/') {
      const loadData = async () => {
        setLoading(true)
        await Promise.all([fetchSystemInfo(), fetchSystemStatus()])
        setLoading(false)
      }

      loadData()
      
      // 定期更新状态
      const interval = setInterval(() => {
        fetchSystemStatus()
      }, 5000)

      return () => clearInterval(interval)
    }
  }, [currentPath])

  // 路由处理
  if (currentPath === '/health') {
    return <HealthCheck />
  }

  // 主页面逻辑
  if (loading && currentPath === '/') {
    return (
      <div className="app">
        <div className="loading">加载中...</div>
      </div>
    )
  }

  if (error && currentPath === '/') {
    return (
      <div className="app">
        <div className="error">
          <h2>连接错误</h2>
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>重新加载</button>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 Reachy Mini 控制系统</h1>
        <div className="status-indicator">
          <span className={`status-dot ${systemInfo?.status === 'running' ? 'running' : 'stopped'}`}></span>
          <span>{systemInfo?.status === 'running' ? '运行中' : '已停止'}</span>
        </div>
      </header>

      <main className="app-main">
        <div className="dashboard">
          <div className="card system-info">
            <h2>系统信息</h2>
            {systemInfo && (
              <div className="info-grid">
                <div className="info-item">
                  <label>系统名称:</label>
                  <span>{systemInfo.message}</span>
                </div>
                <div className="info-item">
                  <label>版本:</label>
                  <span>{systemInfo.version}</span>
                </div>
                <div className="info-item">
                  <label>状态:</label>
                  <span className={`status ${systemInfo.status}`}>{systemInfo.status}</span>
                </div>
                {systemInfo.docs && (
                  <div className="info-item">
                    <label>API文档:</label>
                    <a href={systemInfo.docs} target="_blank" rel="noopener noreferrer">
                      查看文档
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>

          {systemStatus && (
            <div className="card system-status">
              <h2>组件状态</h2>
              <div className="components-grid">
                {Object.entries(systemStatus.components).map(([component, status]) => (
                  <div key={component} className="component-item">
                    <span className={`component-dot ${status ? 'active' : 'inactive'}`}></span>
                    <span className="component-name">{component}</span>
                    <span className={`component-status ${status ? 'active' : 'inactive'}`}>
                      {status ? '正常' : '异常'}
                    </span>
                  </div>
                ))}
              </div>
              {systemStatus.uptime && (
                <div className="uptime">
                  <label>运行时间:</label>
                  <span>{Math.floor(systemStatus.uptime / 60)} 分钟</span>
                </div>
              )}
            </div>
          )}

          <div className="card quick-actions">
            <h2>快速操作</h2>
            <div className="actions-grid">
              <button className="action-btn health" onClick={() => window.open('/health', '_blank')}>
                🏥 健康检查
              </button>
              {systemInfo?.docs && (
                <button className="action-btn docs" onClick={() => window.open(systemInfo.docs, '_blank')}>
                  📚 API文档
                </button>
              )}
              <button className="action-btn refresh" onClick={() => window.location.reload()}>
                🔄 刷新页面
              </button>
            </div>
          </div>

          <div className="card robot-control">
            <h2>机器人控制</h2>
            <div className="control-panel">
              <p className="coming-soon">🚧 控制面板开发中...</p>
              <div className="placeholder-controls">
                <button className="control-btn" disabled>启动机器人</button>
                <button className="control-btn" disabled>停止机器人</button>
                <button className="control-btn" disabled>重置位置</button>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>© 2024 Reachy Mini Control System - Powered by React + Vite</p>
      </footer>
    </div>
  )
}

export default App
