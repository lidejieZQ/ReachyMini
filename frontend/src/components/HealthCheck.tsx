/**
 * Reachy Mini 健康检查组件
 * 
 * 这个组件提供系统健康状态的实时监控界面，包括：
 * - 系统整体健康状态显示
 * - 各个组件的运行状态监控
 * - 系统配置信息展示
 * - 详细系统状态查看
 * - 自动刷新和手动刷新功能
 */

import { useState, useEffect } from 'react'
import './HealthCheck.css'

/**
 * 健康状态数据接口定义
 * 对应后端 /api/health 接口返回的数据结构
 */
interface HealthStatus {
  status: string;                           // 系统整体状态: 'healthy' | 'unhealthy'
  timestamp: number;                        // 状态更新时间戳
  components: Record<string, boolean>;      // 各组件状态映射
  config: {                                // 系统配置信息
    api_host: string;                      // API服务器地址
    api_port: number;                      // API服务器端口
    debug: boolean;                        // 调试模式状态
    database_url?: string;                 // 数据库连接URL（可选）
  };
}

/**
 * 健康检查主组件
 * 
 * 功能特性：
 * - 实时显示系统健康状态
 * - 10秒自动刷新机制
 * - 错误处理和重试
 * - 模态框显示详细系统信息
 * - 响应式设计适配不同屏幕
 */
function HealthCheck() {
  // 主要状态管理
  const [healthData, setHealthData] = useState<HealthStatus | null>(null)  // 健康检查数据
  const [loading, setLoading] = useState(true)                             // 加载状态
  const [error, setError] = useState<string | null>(null)                  // 错误信息
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())           // 最后更新时间
  
  // 系统状态模态框相关状态
  const [systemStatus, setSystemStatus] = useState<any>(null)              // 详细系统状态数据
  const [showSystemStatus, setShowSystemStatus] = useState(false)          // 模态框显示状态

  /**
   * 获取系统健康状态数据
   * 
   * 从后端 /api/health 接口获取系统健康信息，包括：
   * - 整体系统状态
   * - 各组件运行状态
   * - 系统配置信息
   * - 时间戳信息
   */
  const fetchHealthData = async () => {
    try {
      const response = await fetch('/api/health')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setHealthData(data)        // 更新健康数据
      setError(null)             // 清除错误状态
      setLastUpdate(new Date())  // 更新最后刷新时间
    } catch (err) {
      // 处理网络错误或API错误
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)  // 无论成功失败都结束加载状态
    }
  }

  /**
   * 获取详细系统状态信息
   * 
   * 从后端 /system/status 接口获取更详细的系统运行状态，
   * 用于在模态框中显示完整的系统信息
   */
  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/system/status')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setSystemStatus(data)        // 设置详细状态数据
      setShowSystemStatus(true)    // 显示模态框
    } catch (err) {
      // 处理获取系统状态时的错误
      setError(err instanceof Error ? err.message : '获取系统状态失败')
    }
  }

  /**
   * 组件挂载时的副作用处理
   * 
   * 1. 立即获取一次健康状态数据
   * 2. 设置10秒间隔的自动刷新定时器
   * 3. 组件卸载时清理定时器
   */
  useEffect(() => {
    fetchHealthData()  // 组件加载时立即获取数据
    
    // 设置自动刷新定时器，每10秒更新一次
    const interval = setInterval(fetchHealthData, 10000)
    
    // 清理函数：组件卸载时清除定时器
    return () => clearInterval(interval)
  }, [])  // 空依赖数组，只在组件挂载时执行一次

  /**
   * 根据状态获取对应的颜色
   * 
   * @param status 状态字符串
   * @returns 对应的十六进制颜色值
   */
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return '#27ae60'  // 绿色 - 健康状态
      case 'unhealthy':
        return '#e74c3c'  // 红色 - 不健康状态
      default:
        return '#f39c12'  // 橙色 - 未知状态
    }
  }

  /**
   * 格式化时间戳为本地时间字符串
   * 
   * @param timestamp Unix时间戳（秒）
   * @returns 格式化的中文时间字符串
   */
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('zh-CN')
  }

  if (loading) {
    return (
      <div className="health-check">
        <div className="health-header">
          <h1>🏥 系统健康检查</h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>正在检查系统健康状态...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="health-check">
      <div className="health-header">
        <h1>🏥 系统健康检查</h1>
        <div className="header-actions">
          <button className="refresh-btn" onClick={fetchHealthData}>
            🔄 刷新
          </button>
          <button className="back-btn" onClick={() => window.location.href = '/'}>
            ← 返回
          </button>
        </div>
      </div>

      {error && (
        <div className="error-card">
          <h2>❌ 连接错误</h2>
          <p>{error}</p>
          <button onClick={fetchHealthData}>重试</button>
        </div>
      )}

      {healthData && (
        <div className="health-content">
          <div className="status-overview">
            <div className="status-card">
              <div 
                className="status-indicator"
                style={{ backgroundColor: getStatusColor(healthData.status) }}
              ></div>
              <div className="status-info">
                <h2>系统状态</h2>
                <p className="status-text">{healthData.status.toUpperCase()}</p>
                <p className="status-desc">
                  {healthData.status === 'healthy' ? '所有系统正常运行' : '系统存在异常'}
                </p>
              </div>
            </div>

            <div className="timestamp-card">
              <h3>📅 检查时间</h3>
              <p className="timestamp">{formatTimestamp(healthData.timestamp)}</p>
              <p className="last-update">最后更新: {lastUpdate.toLocaleTimeString('zh-CN')}</p>
            </div>
          </div>

          <div className="components-section">
            <h2>🔧 组件状态</h2>
            <div className="components-grid">
              {Object.entries(healthData.components).map(([component, status]) => (
                <div key={component} className={`component-card ${status ? 'healthy' : 'unhealthy'}`}>
                  <div className="component-header">
                    <span className={`component-dot ${status ? 'active' : 'inactive'}`}></span>
                    <h3>{component}</h3>
                  </div>
                  <p className={`component-status ${status ? 'healthy' : 'unhealthy'}`}>
                    {status ? '✅ 正常' : '❌ 异常'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="config-section">
            <h2>⚙️ 系统配置</h2>
            <div className="config-grid">
              <div className="config-item">
                <label>API 主机:</label>
                <span>{healthData.config.api_host}</span>
              </div>
              <div className="config-item">
                <label>API 端口:</label>
                <span>{healthData.config.api_port}</span>
              </div>
              <div className="config-item">
                <label>调试模式:</label>
                <span className={healthData.config.debug ? 'enabled' : 'disabled'}>
                  {healthData.config.debug ? '✅ 启用' : '❌ 禁用'}
                </span>
              </div>
              {healthData.config.database_url && (
                <div className="config-item">
                  <label>数据库:</label>
                  <span className="database-url">
                    {healthData.config.database_url.replace(/\/\/.*@/, '//***@')}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="actions-section">
            <h2>🚀 快速操作</h2>
            <div className="actions-grid">
              <button className="action-btn docs" onClick={() => window.open('/docs', '_blank')}>
                📚 API 文档
              </button>
              <button className="action-btn system" onClick={fetchSystemStatus}>
                📊 系统状态
              </button>
              <button className="action-btn home" onClick={() => window.location.href = '/'}>
                🏠 返回首页
              </button>
            </div>
          </div>

          {/* 系统状态模态框 */}
          {showSystemStatus && systemStatus && (
            <div className="modal-overlay" onClick={() => setShowSystemStatus(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>📊 详细系统状态</h2>
                  <button className="modal-close" onClick={() => setShowSystemStatus(false)}>×</button>
                </div>
                <div className="modal-body">
                  <div className="system-info">
                    <div className="info-item">
                      <label>运行状态:</label>
                      <span className={systemStatus.running ? 'status-running' : 'status-stopped'}>
                        {systemStatus.running ? '✅ 运行中' : '❌ 已停止'}
                      </span>
                    </div>
                    <div className="info-item">
                      <label>运行时间:</label>
                      <span>{Math.floor(systemStatus.uptime || 0)}秒</span>
                    </div>
                  </div>
                  
                  <div className="components-detail">
                    <h3>组件详情</h3>
                    {Object.entries(systemStatus.components || {}).map(([component, status]) => (
                      <div key={component} className="component-detail-item">
                        <span className={`status-dot ${status ? 'active' : 'inactive'}`}></span>
                        <span className="component-name">{component}</span>
                        <span className={`component-status ${status ? 'healthy' : 'unhealthy'}`}>
                          {status ? '正常' : '异常'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default HealthCheck