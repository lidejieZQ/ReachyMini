//! 通用模块
//! 
//! 提供整个系统共用的数据结构、工具函数和常量定义。

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use anyhow::Result;

/// 3D向量结构
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Vector3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vector3 {
    pub fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }
    
    pub fn zero() -> Self {
        Self::new(0.0, 0.0, 0.0)
    }
    
    pub fn magnitude(&self) -> f64 {
        (self.x * self.x + self.y * self.y + self.z * self.z).sqrt()
    }
    
    pub fn normalize(&self) -> Self {
        let mag = self.magnitude();
        if mag > 0.0 {
            Self::new(self.x / mag, self.y / mag, self.z / mag)
        } else {
            Self::zero()
        }
    }
    
    pub fn dot(&self, other: &Self) -> f64 {
        self.x * other.x + self.y * other.y + self.z * other.z
    }
    
    pub fn cross(&self, other: &Self) -> Self {
        Self::new(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )
    }
}

impl std::ops::Add for Vector3 {
    type Output = Self;
    
    fn add(self, other: Self) -> Self {
        Self::new(self.x + other.x, self.y + other.y, self.z + other.z)
    }
}

impl std::ops::Sub for Vector3 {
    type Output = Self;
    
    fn sub(self, other: Self) -> Self {
        Self::new(self.x - other.x, self.y - other.y, self.z - other.z)
    }
}

impl std::ops::Mul<f64> for Vector3 {
    type Output = Self;
    
    fn mul(self, scalar: f64) -> Self {
        Self::new(self.x * scalar, self.y * scalar, self.z * scalar)
    }
}

/// 四元数结构（用于旋转表示）
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Quaternion {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Quaternion {
    pub fn new(w: f64, x: f64, y: f64, z: f64) -> Self {
        Self { w, x, y, z }
    }
    
    pub fn identity() -> Self {
        Self::new(1.0, 0.0, 0.0, 0.0)
    }
    
    pub fn from_euler(roll: f64, pitch: f64, yaw: f64) -> Self {
        let cr = (roll * 0.5).cos();
        let sr = (roll * 0.5).sin();
        let cp = (pitch * 0.5).cos();
        let sp = (pitch * 0.5).sin();
        let cy = (yaw * 0.5).cos();
        let sy = (yaw * 0.5).sin();
        
        Self::new(
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        )
    }
    
    pub fn normalize(&self) -> Self {
        let norm = (self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z).sqrt();
        if norm > 0.0 {
            Self::new(self.w / norm, self.x / norm, self.y / norm, self.z / norm)
        } else {
            Self::identity()
        }
    }
}

/// 位姿结构（位置 + 方向）
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Pose {
    pub position: Vector3,
    pub orientation: Quaternion,
}

impl Pose {
    pub fn new(position: Vector3, orientation: Quaternion) -> Self {
        Self { position, orientation }
    }
    
    pub fn identity() -> Self {
        Self::new(Vector3::zero(), Quaternion::identity())
    }
}

/// 关节状态结构
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JointState {
    pub name: String,
    pub position: f64,
    pub velocity: f64,
    pub effort: f64,
    pub temperature: Option<f64>,
    pub is_moving: bool,
}

impl JointState {
    pub fn new(name: String) -> Self {
        Self {
            name,
            position: 0.0,
            velocity: 0.0,
            effort: 0.0,
            temperature: None,
            is_moving: false,
        }
    }
}

/// 机器人状态结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RobotState {
    pub joints: HashMap<String, JointState>,
    pub base_pose: Pose,
    pub is_connected: bool,
    pub battery_level: Option<f64>,
    pub timestamp: u64,
}

impl RobotState {
    pub fn new() -> Self {
        Self {
            joints: HashMap::new(),
            base_pose: Pose::identity(),
            is_connected: false,
            battery_level: None,
            timestamp: current_timestamp(),
        }
    }
    
    pub fn update_timestamp(&mut self) {
        self.timestamp = current_timestamp();
    }
}

impl Default for RobotState {
    fn default() -> Self {
        Self::new()
    }
}

/// 图像数据结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageData {
    pub width: u32,
    pub height: u32,
    pub channels: u32,
    pub data: Vec<u8>,
    pub format: ImageFormat,
    pub timestamp: u64,
}

/// 图像格式枚举
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ImageFormat {
    RGB8,
    BGR8,
    RGBA8,
    BGRA8,
    Gray8,
    Gray16,
}

impl ImageData {
    pub fn new(width: u32, height: u32, channels: u32, format: ImageFormat) -> Self {
        let data_size = (width * height * channels) as usize;
        Self {
            width,
            height,
            channels,
            data: vec![0; data_size],
            format,
            timestamp: current_timestamp(),
        }
    }
    
    pub fn from_raw(width: u32, height: u32, channels: u32, data: Vec<u8>, format: ImageFormat) -> Self {
        Self {
            width,
            height,
            channels,
            data,
            format,
            timestamp: current_timestamp(),
        }
    }
    
    pub fn size(&self) -> usize {
        self.data.len()
    }
    
    pub fn is_valid(&self) -> bool {
        let expected_size = (self.width * self.height * self.channels) as usize;
        self.data.len() == expected_size
    }
}

/// 性能统计结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceStats {
    pub fps: f64,
    pub avg_processing_time: Duration,
    pub max_processing_time: Duration,
    pub min_processing_time: Duration,
    pub total_frames: u64,
    pub dropped_frames: u64,
    pub cpu_usage: f64,
    pub memory_usage: u64,
    pub timestamp: u64,
}

impl PerformanceStats {
    pub fn new() -> Self {
        Self {
            fps: 0.0,
            avg_processing_time: Duration::from_millis(0),
            max_processing_time: Duration::from_millis(0),
            min_processing_time: Duration::from_millis(u64::MAX),
            total_frames: 0,
            dropped_frames: 0,
            cpu_usage: 0.0,
            memory_usage: 0,
            timestamp: current_timestamp(),
        }
    }
    
    pub fn update_frame_stats(&mut self, processing_time: Duration) {
        self.total_frames += 1;
        
        if processing_time > self.max_processing_time {
            self.max_processing_time = processing_time;
        }
        
        if processing_time < self.min_processing_time {
            self.min_processing_time = processing_time;
        }
        
        // 简单的移动平均
        let alpha = 0.1;
        let new_avg = self.avg_processing_time.as_secs_f64() * (1.0 - alpha) + 
                     processing_time.as_secs_f64() * alpha;
        self.avg_processing_time = Duration::from_secs_f64(new_avg);
        
        // 计算FPS
        if self.avg_processing_time.as_secs_f64() > 0.0 {
            self.fps = 1.0 / self.avg_processing_time.as_secs_f64();
        }
        
        self.timestamp = current_timestamp();
    }
    
    pub fn increment_dropped_frames(&mut self) {
        self.dropped_frames += 1;
        self.timestamp = current_timestamp();
    }
}

impl Default for PerformanceStats {
    fn default() -> Self {
        Self::new()
    }
}

/// 配置验证trait
pub trait ConfigValidation {
    fn validate(&self) -> Result<()>;
}

/// 状态管理trait
pub trait StateManager {
    type State;
    
    fn get_state(&self) -> Self::State;
    fn set_state(&mut self, state: Self::State);
}

/// 生命周期管理trait
pub trait LifecycleManager {
    async fn start(&mut self) -> Result<()>;
    async fn stop(&mut self) -> Result<()>;
    async fn restart(&mut self) -> Result<()> {
        self.stop().await?;
        self.start().await
    }
    fn is_running(&self) -> bool;
}

/// 工具函数

/// 获取当前时间戳（毫秒）
pub fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

/// 获取当前时间戳（微秒）
pub fn current_timestamp_micros() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_micros() as u64
}

/// 角度转弧度
pub fn degrees_to_radians(degrees: f64) -> f64 {
    degrees * std::f64::consts::PI / 180.0
}

/// 弧度转角度
pub fn radians_to_degrees(radians: f64) -> f64 {
    radians * 180.0 / std::f64::consts::PI
}

/// 限制值在指定范围内
pub fn clamp<T: PartialOrd>(value: T, min: T, max: T) -> T {
    if value < min {
        min
    } else if value > max {
        max
    } else {
        value
    }
}

/// 线性插值
pub fn lerp(a: f64, b: f64, t: f64) -> f64 {
    a + (b - a) * clamp(t, 0.0, 1.0)
}

/// 平滑步函数
pub fn smooth_step(edge0: f64, edge1: f64, x: f64) -> f64 {
    let t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

/// 计算两个向量之间的角度（弧度）
pub fn angle_between_vectors(v1: &Vector3, v2: &Vector3) -> f64 {
    let dot = v1.normalize().dot(&v2.normalize());
    dot.clamp(-1.0, 1.0).acos()
}

/// 系统常量
pub mod constants {
    use std::time::Duration;
    
    /// 默认超时时间
    pub const DEFAULT_TIMEOUT: Duration = Duration::from_secs(5);
    
    /// 默认重试次数
    pub const DEFAULT_RETRY_COUNT: u32 = 3;
    
    /// 默认缓冲区大小
    pub const DEFAULT_BUFFER_SIZE: usize = 1024 * 1024; // 1MB
    
    /// 最大图像尺寸
    pub const MAX_IMAGE_WIDTH: u32 = 1920;
    pub const MAX_IMAGE_HEIGHT: u32 = 1080;
    
    /// 关节限制
    pub const MAX_JOINT_VELOCITY: f64 = 3.14; // rad/s
    pub const MAX_JOINT_ACCELERATION: f64 = 10.0; // rad/s²
    
    /// 网络配置
    pub const DEFAULT_WEBSOCKET_PORT: u16 = 8765;
    pub const DEFAULT_HTTP_PORT: u16 = 8000;
    
    /// 性能配置
    pub const TARGET_FPS: f64 = 30.0;
    pub const MAX_PROCESSING_TIME_MS: u64 = 33; // ~30 FPS
}

/// 错误处理宏
#[macro_export]
macro_rules! ensure_running {
    ($is_running:expr, $msg:expr) => {
        if !$is_running {
            return Err(anyhow::anyhow!($msg));
        }
    };
}

#[macro_export]
macro_rules! log_and_return_error {
    ($error:expr, $msg:expr) => {
        log::error!("{}: {}", $msg, $error);
        return Err($error.into());
    };
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_vector3_operations() {
        let v1 = Vector3::new(1.0, 2.0, 3.0);
        let v2 = Vector3::new(4.0, 5.0, 6.0);
        
        let sum = v1 + v2;
        assert_eq!(sum, Vector3::new(5.0, 7.0, 9.0));
        
        let diff = v2 - v1;
        assert_eq!(diff, Vector3::new(3.0, 3.0, 3.0));
        
        let scaled = v1 * 2.0;
        assert_eq!(scaled, Vector3::new(2.0, 4.0, 6.0));
        
        let magnitude = v1.magnitude();
        assert!((magnitude - 3.7416573867739413).abs() < 1e-10);
    }
    
    #[test]
    fn test_quaternion_creation() {
        let q = Quaternion::identity();
        assert_eq!(q, Quaternion::new(1.0, 0.0, 0.0, 0.0));
        
        let q_euler = Quaternion::from_euler(0.0, 0.0, 0.0);
        assert!((q_euler.w - 1.0).abs() < 1e-10);
        assert!(q_euler.x.abs() < 1e-10);
        assert!(q_euler.y.abs() < 1e-10);
        assert!(q_euler.z.abs() < 1e-10);
    }
    
    #[test]
    fn test_image_data() {
        let img = ImageData::new(640, 480, 3, ImageFormat::RGB8);
        assert_eq!(img.width, 640);
        assert_eq!(img.height, 480);
        assert_eq!(img.channels, 3);
        assert_eq!(img.size(), 640 * 480 * 3);
        assert!(img.is_valid());
    }
    
    #[test]
    fn test_utility_functions() {
        assert!((degrees_to_radians(180.0) - std::f64::consts::PI).abs() < 1e-10);
        assert!((radians_to_degrees(std::f64::consts::PI) - 180.0).abs() < 1e-10);
        
        assert_eq!(clamp(5, 0, 10), 5);
        assert_eq!(clamp(-5, 0, 10), 0);
        assert_eq!(clamp(15, 0, 10), 10);
        
        assert!((lerp(0.0, 10.0, 0.5) - 5.0).abs() < 1e-10);
    }
}