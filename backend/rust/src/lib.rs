//! Reachy Mini Rust Library
//! 
//! 高性能Rust模块，为Reachy Mini机器人提供基础功能。
//! 
//! 这个库提供了以下核心功能：
//! - 系统生命周期管理
//! - 配置管理和验证
//! - 状态监控和报告
//! - Python绑定接口
//! - 异步任务处理
//! 
//! # 架构设计
//! 
//! 本库采用异步架构，使用Tokio运行时提供高性能的并发处理能力。
//! 通过PyO3提供Python绑定，使得Python代码可以调用Rust的高性能功能。
//! 
//! # 使用示例
//! 
//! ```rust
//! use reachy_mini_rust::{ReachyMiniSystem, Config};
//! 
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let config = Config {
//!         name: "Reachy Mini".to_string(),
//!         version: "1.0.0".to_string(),
//!     };
//!     
//!     let system = ReachyMiniSystem::new(config).await?;
//!     system.start().await?;
//!     
//!     // 系统运行逻辑...
//!     
//!     system.stop().await?;
//!     Ok(())
//! }
//! ```

// 条件编译：仅在启用python-bindings特性时编译Python绑定模块
#[cfg(feature = "python-bindings")]
mod python_bindings;

// 导出Python绑定接口
#[cfg(feature = "python-bindings")]
pub use python_bindings::*;

// 标准库和第三方依赖导入
use std::sync::Arc;           // 原子引用计数，用于多线程共享数据
use tokio::sync::RwLock;      // 异步读写锁，保护共享状态
use anyhow::Result;           // 错误处理类型
use log::{info, error};       // 日志记录宏

/// 全局配置结构
/// 
/// 存储系统的基本配置信息，包括系统名称和版本号。
/// 支持从JSON、TOML等格式反序列化。
/// 
/// # 字段说明
/// 
/// * `name` - 系统名称，用于标识和日志记录
/// * `version` - 系统版本号，用于版本管理和兼容性检查
#[derive(Debug, Clone, serde::Deserialize)]
pub struct Config {
    /// 系统名称
    pub name: String,
    /// 系统版本号
    pub version: String,
}

/// 主要的Reachy Mini系统结构
/// 
/// 这是整个Rust模块的核心结构，负责管理系统的生命周期和状态。
/// 使用异步设计，支持并发操作和状态管理。
/// 
/// # 设计特点
/// 
/// - **线程安全**: 使用Arc和RwLock确保多线程环境下的安全访问
/// - **异步支持**: 所有操作都是异步的，提供高性能的并发处理
/// - **状态管理**: 维护系统运行状态，支持启动、停止和状态查询
/// - **配置驱动**: 通过配置对象控制系统行为
/// 
/// # 生命周期
/// 
/// 1. `new()` - 创建系统实例
/// 2. `start()` - 启动系统服务
/// 3. `is_running()` - 查询运行状态
/// 4. `get_status()` - 获取详细状态
/// 5. `stop()` - 停止系统服务
pub struct ReachyMiniSystem {
    /// 系统配置，使用Arc实现多线程共享
    config: Arc<Config>,
    /// 系统运行状态，使用RwLock保护并发访问
    is_running: Arc<RwLock<bool>>,
}

impl ReachyMiniSystem {
    /// 创建新的Reachy Mini系统实例
    /// 
    /// 初始化系统的基本结构和状态，但不启动任何服务。
    /// 系统创建后处于停止状态，需要调用`start()`方法启动。
    /// 
    /// # 参数
    /// 
    /// * `config` - 系统配置对象
    /// 
    /// # 返回值
    /// 
    /// 返回`Result<Self>`，成功时包含系统实例，失败时包含错误信息。
    /// 
    /// # 示例
    /// 
    /// ```rust
    /// let config = Config {
    ///     name: "Reachy Mini".to_string(),
    ///     version: "1.0.0".to_string(),
    /// };
    /// let system = ReachyMiniSystem::new(config).await?;
    /// ```
    pub async fn new(config: Config) -> Result<Self> {
        info!("初始化Reachy Mini系统: {} v{}", config.name, config.version);
        
        // 将配置包装为Arc，支持多线程共享
        let config = Arc::new(config);
        // 初始化运行状态为false（停止状态）
        let is_running = Arc::new(RwLock::new(false));
        
        Ok(Self {
            config,
            is_running,
        })
    }
    
    /// 启动系统
    /// 
    /// 启动所有系统服务和组件。这个方法会：
    /// 1. 检查系统是否已经在运行
    /// 2. 初始化各个子系统
    /// 3. 设置运行状态为true
    /// 4. 记录启动日志
    /// 
    /// # 返回值
    /// 
    /// 返回`Result<()>`，成功时返回Ok(())，失败时返回错误信息。
    /// 
    /// # 错误处理
    /// 
    /// 如果系统已经在运行，此方法会直接返回成功。
    /// 如果启动过程中出现错误，会记录错误日志并返回错误。
    pub async fn start(&self) -> Result<()> {
        info!("启动Reachy Mini系统: {}", self.config.name);
        
        // 获取写锁并更新运行状态
        let mut running = self.is_running.write().await;
        
        // 检查是否已经在运行
        if *running {
            info!("系统已经在运行中");
            return Ok(());
        }
        
        // 设置运行状态为true
        *running = true;
        
        info!("✅ Reachy Mini系统启动完成");
        Ok(())
    }
    
    /// 停止系统
    pub async fn stop(&self) -> Result<()> {
        info!("停止Reachy Mini系统...");
        
        let mut running = self.is_running.write().await;
        *running = false;
        
        info!("Reachy Mini系统已停止");
        Ok(())
    }
    
    /// 检查系统是否运行中
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
    
    /// 获取系统状态
    pub async fn get_status(&self) -> Result<SystemStatus> {
        Ok(SystemStatus {
            is_running: self.is_running().await,
            name: self.config.name.clone(),
            version: self.config.version.clone(),
            timestamp: chrono::Utc::now(),
        })
    }
}

/// 系统状态结构
#[derive(Debug, Clone, serde::Serialize)]
pub struct SystemStatus {
    pub is_running: bool,
    pub name: String,
    pub version: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// 初始化日志系统
pub fn init_logging() -> Result<()> {
    env_logger::init();
    info!("日志系统初始化完成");
    Ok(())
}

/// 加载配置文件
pub fn load_config(config_content: &str) -> Result<Config> {
    let config: Config = serde_json::from_str(config_content)
        .map_err(|e| anyhow::anyhow!("配置解析失败: {}", e))?;
    Ok(config)
}

/// 错误类型定义
#[derive(Debug, thiserror::Error)]
pub enum ReachyMiniError {
    #[error("配置错误: {0}")]
    Config(String),
    
    #[error("系统错误: {0}")]
    System(String),
}

pub type ReachyMiniResult<T> = std::result::Result<T, ReachyMiniError>;

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_system_creation() {
        let config = Config {
            name: "test".to_string(),
            version: "0.1.0".to_string(),
        };
        
        let system = ReachyMiniSystem::new(config).await.unwrap();
        assert!(!system.is_running().await);
    }
    
    #[tokio::test]
    async fn test_system_lifecycle() {
        let config = Config {
            name: "test".to_string(),
            version: "0.1.0".to_string(),
        };
        
        let system = ReachyMiniSystem::new(config).await.unwrap();
        
        system.start().await.unwrap();
        assert!(system.is_running().await);
        
        system.stop().await.unwrap();
        assert!(!system.is_running().await);
    }
}