//! Python绑定模块
//! 
//! 为Python提供Rust功能的接口

#[cfg(feature = "python-bindings")]
use pyo3::prelude::*;
#[cfg(feature = "python-bindings")]
use pyo3::types::PyModule;
#[cfg(feature = "python-bindings")]
use pyo3::Bound;

#[cfg(feature = "python-bindings")]
use crate::{ReachyMiniSystem, Config, SystemStatus};

#[cfg(feature = "python-bindings")]
#[pyclass]
struct PyReachyMiniSystem {
    inner: ReachyMiniSystem,
}

#[cfg(feature = "python-bindings")]
#[pymethods]
impl PyReachyMiniSystem {
    #[new]
    fn new(name: String, version: String) -> PyResult<Self> {
        let config = Config { name, version };
        
        let rt = tokio::runtime::Runtime::new().unwrap();
        let inner = rt.block_on(async {
            ReachyMiniSystem::new(config).await
        }).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        Ok(Self { inner })
    }
    
    fn start(&self) -> PyResult<()> {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            self.inner.start().await
        }).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        Ok(())
    }
    
    fn stop(&self) -> PyResult<()> {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            self.inner.stop().await
        }).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        Ok(())
    }
    
    fn is_running(&self) -> PyResult<bool> {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(async {
            self.inner.is_running().await
        });
        
        Ok(result)
    }
    
    fn get_status(&self) -> PyResult<String> {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let status = rt.block_on(async {
            self.inner.get_status().await
        }).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        let json = serde_json::to_string(&status)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        Ok(json)
    }
}

#[cfg(feature = "python-bindings")]
#[pyfunction]
fn init_logging() -> PyResult<()> {
    crate::init_logging();
    Ok(())
}

#[cfg(feature = "python-bindings")]
#[pyfunction]
fn get_system_info() -> PyResult<String> {
    use serde_json::json;
    
    let info = json!({
        "name": "ReachyMini Rust System",
        "version": "0.1.0",
        "status": "running",
        "features": [
            "python-bindings",
            "async-runtime",
            "logging"
        ],
        "timestamp": chrono::Utc::now().to_rfc3339()
    });
    
    Ok(info.to_string())
}

#[cfg(feature = "python-bindings")]
#[pyfunction]
fn validate_config(config_json: String) -> PyResult<bool> {
    use serde_json::Value;
    
    // 尝试解析JSON配置
    match serde_json::from_str::<Value>(&config_json) {
        Ok(config) => {
            // 基本的配置验证逻辑
            if let Some(obj) = config.as_object() {
                // 检查必需的配置节
                let required_sections = ["vision", "realtime", "hardware", "ai"];
                for section in &required_sections {
                    if !obj.contains_key(*section) {
                        return Ok(false);
                    }
                }
                Ok(true)
            } else {
                Ok(false)
            }
        },
        Err(_) => Ok(false)
    }
}

#[cfg(feature = "python-bindings")]
#[pymodule]
fn reachy_mini_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyReachyMiniSystem>()?;
    m.add_function(wrap_pyfunction!(init_logging, m)?)?;
    m.add_function(wrap_pyfunction!(get_system_info, m)?)?;
    m.add_function(wrap_pyfunction!(validate_config, m)?)?;
    Ok(())
}

// 确保模块在没有python-bindings特性时也能编译
#[cfg(not(feature = "python-bindings"))]
pub fn reachy_mini_rust() {
    // 空函数
}

// 如果没有启用python-bindings特性，提供空的实现
#[cfg(not(feature = "python-bindings"))]
pub fn dummy() {
    // 空函数，防止编译器警告
}