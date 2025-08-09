//! 配置管理模块
//! 
//! 提供统一的配置管理功能，支持从文件、环境变量等多种来源加载配置。

use crate::common::*;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use log::{info, warn, error, debug};

/// 全局配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub system: SystemConfig,
    pub vision: VisionConfig,
    pub realtime: RealtimeConfig,
    pub hardware: HardwareConfig,
    pub ai: AIConfig,
    pub logging: LoggingConfig,
    pub network: NetworkConfig,
    pub security: SecurityConfig,
    pub performance: PerformanceConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            system: SystemConfig::default(),
            vision: VisionConfig::default(),
            realtime: RealtimeConfig::default(),
            hardware: HardwareConfig::default(),
            ai: AIConfig::default(),
            logging: LoggingConfig::default(),
            network: NetworkConfig::default(),
            security: SecurityConfig::default(),
            performance: PerformanceConfig::default(),
        }
    }
}

impl ConfigValidation for Config {
    fn validate(&self) -> Result<()> {
        self.system.validate()?;
        self.vision.validate()?;
        self.realtime.validate()?;
        self.hardware.validate()?;
        self.ai.validate()?;
        self.logging.validate()?;
        self.network.validate()?;
        self.security.validate()?;
        self.performance.validate()?;
        Ok(())
    }
}

/// 系统配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemConfig {
    pub name: String,
    pub version: String,
    pub environment: Environment,
    pub debug_mode: bool,
    pub max_threads: usize,
    pub work_directory: PathBuf,
    pub data_directory: PathBuf,
    pub log_directory: PathBuf,
    pub temp_directory: PathBuf,
    pub shutdown_timeout_ms: u64,
}

impl Default for SystemConfig {
    fn default() -> Self {
        Self {
            name: "ReachyMini".to_string(),
            version: "1.0.0".to_string(),
            environment: Environment::Development,
            debug_mode: true,
            max_threads: num_cpus::get(),
            work_directory: PathBuf::from("."),
            data_directory: PathBuf::from("./data"),
            log_directory: PathBuf::from("./logs"),
            temp_directory: PathBuf::from("./temp"),
            shutdown_timeout_ms: 5000,
        }
    }
}

impl ConfigValidation for SystemConfig {
    fn validate(&self) -> Result<()> {
        if self.name.is_empty() {
            return Err(anyhow::anyhow!("系统名称不能为空"));
        }
        
        if self.version.is_empty() {
            return Err(anyhow::anyhow!("系统版本不能为空"));
        }
        
        if self.max_threads == 0 {
            return Err(anyhow::anyhow!("最大线程数必须大于0"));
        }
        
        if self.shutdown_timeout_ms == 0 {
            return Err(anyhow::anyhow!("关闭超时时间必须大于0"));
        }
        
        Ok(())
    }
}

/// 运行环境
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Environment {
    Development,
    Testing,
    Staging,
    Production,
}

/// 视觉配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisionConfig {
    pub enabled: bool,
    pub camera_id: u32,
    pub resolution: (u32, u32),
    pub fps: u32,
    pub buffer_size: usize,
    pub processing_threads: usize,
    pub face_detection: FaceDetectionConfig,
    pub feature_detection: FeatureDetectionConfig,
    pub calibration: CameraCalibrationConfig,
}

impl Default for VisionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            camera_id: 0,
            resolution: (640, 480),
            fps: 30,
            buffer_size: 10,
            processing_threads: 2,
            face_detection: FaceDetectionConfig::default(),
            feature_detection: FeatureDetectionConfig::default(),
            calibration: CameraCalibrationConfig::default(),
        }
    }
}

impl ConfigValidation for VisionConfig {
    fn validate(&self) -> Result<()> {
        if self.resolution.0 == 0 || self.resolution.1 == 0 {
            return Err(anyhow::anyhow!("分辨率必须大于0"));
        }
        
        if self.fps == 0 {
            return Err(anyhow::anyhow!("帧率必须大于0"));
        }
        
        if self.buffer_size == 0 {
            return Err(anyhow::anyhow!("缓冲区大小必须大于0"));
        }
        
        if self.processing_threads == 0 {
            return Err(anyhow::anyhow!("处理线程数必须大于0"));
        }
        
        self.face_detection.validate()?;
        self.feature_detection.validate()?;
        self.calibration.validate()?;
        
        Ok(())
    }
}

/// 人脸检测配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaceDetectionConfig {
    pub enabled: bool,
    pub model_path: String,
    pub confidence_threshold: f32,
    pub nms_threshold: f32,
    pub max_faces: usize,
}

impl Default for FaceDetectionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            model_path: "models/face_detection.xml".to_string(),
            confidence_threshold: 0.7,
            nms_threshold: 0.4,
            max_faces: 10,
        }
    }
}

impl ConfigValidation for FaceDetectionConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.model_path.is_empty() {
            return Err(anyhow::anyhow!("人脸检测模型路径不能为空"));
        }
        
        if self.confidence_threshold < 0.0 || self.confidence_threshold > 1.0 {
            return Err(anyhow::anyhow!("置信度阈值必须在0-1之间"));
        }
        
        if self.nms_threshold < 0.0 || self.nms_threshold > 1.0 {
            return Err(anyhow::anyhow!("NMS阈值必须在0-1之间"));
        }
        
        if self.max_faces == 0 {
            return Err(anyhow::anyhow!("最大人脸数必须大于0"));
        }
        
        Ok(())
    }
}

/// 特征检测配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureDetectionConfig {
    pub enabled: bool,
    pub detector_type: FeatureDetectorType,
    pub max_features: usize,
    pub quality_level: f64,
    pub min_distance: f64,
}

impl Default for FeatureDetectionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            detector_type: FeatureDetectorType::SIFT,
            max_features: 1000,
            quality_level: 0.01,
            min_distance: 10.0,
        }
    }
}

impl ConfigValidation for FeatureDetectionConfig {
    fn validate(&self) -> Result<()> {
        if self.max_features == 0 {
            return Err(anyhow::anyhow!("最大特征点数必须大于0"));
        }
        
        if self.quality_level <= 0.0 || self.quality_level > 1.0 {
            return Err(anyhow::anyhow!("质量水平必须在0-1之间"));
        }
        
        if self.min_distance <= 0.0 {
            return Err(anyhow::anyhow!("最小距离必须大于0"));
        }
        
        Ok(())
    }
}

/// 特征检测器类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FeatureDetectorType {
    SIFT,
    SURF,
    ORB,
    FAST,
    BRIEF,
}

/// 相机标定配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CameraCalibrationConfig {
    pub enabled: bool,
    pub calibration_file: String,
    pub board_size: (i32, i32),
    pub square_size: f32,
    pub auto_calibrate: bool,
}

impl Default for CameraCalibrationConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            calibration_file: "calibration.yaml".to_string(),
            board_size: (9, 6),
            square_size: 25.0,
            auto_calibrate: false,
        }
    }
}

impl ConfigValidation for CameraCalibrationConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.calibration_file.is_empty() {
            return Err(anyhow::anyhow!("标定文件路径不能为空"));
        }
        
        if self.board_size.0 <= 0 || self.board_size.1 <= 0 {
            return Err(anyhow::anyhow!("棋盘格大小必须大于0"));
        }
        
        if self.square_size <= 0.0 {
            return Err(anyhow::anyhow!("方格大小必须大于0"));
        }
        
        Ok(())
    }
}

/// 实时控制配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealtimeConfig {
    pub enabled: bool,
    pub control_frequency: f64,
    pub sensor_frequency: f64,
    pub max_acceleration: f64,
    pub max_velocity: f64,
    pub position_tolerance: f64,
    pub velocity_tolerance: f64,
    pub pid_gains: HashMap<String, PIDGains>,
    pub joint_limits: HashMap<String, JointLimits>,
    pub safety: SafetyConfig,
}

impl Default for RealtimeConfig {
    fn default() -> Self {
        let mut pid_gains = HashMap::new();
        let mut joint_limits = HashMap::new();
        
        // 默认PID参数
        let default_pid = PIDGains {
            kp: 1.0,
            ki: 0.1,
            kd: 0.01,
            max_integral: 10.0,
            max_output: 100.0,
        };
        
        // 默认关节限制
        let default_limits = JointLimits {
            min_position: -180.0,
            max_position: 180.0,
            max_velocity: 90.0,
            max_acceleration: 180.0,
            max_torque: 10.0,
        };
        
        // 为所有关节设置默认值
        let joint_names = vec![
            "head_pan", "head_tilt",
            "left_shoulder_pitch", "left_shoulder_roll", "left_elbow_pitch",
            "right_shoulder_pitch", "right_shoulder_roll", "right_elbow_pitch",
        ];
        
        for joint_name in joint_names {
            pid_gains.insert(joint_name.to_string(), default_pid.clone());
            joint_limits.insert(joint_name.to_string(), default_limits.clone());
        }
        
        Self {
            enabled: true,
            control_frequency: 100.0, // 100Hz
            sensor_frequency: 1000.0, // 1kHz
            max_acceleration: 180.0,   // deg/s²
            max_velocity: 90.0,        // deg/s
            position_tolerance: 1.0,   // degrees
            velocity_tolerance: 5.0,   // deg/s
            pid_gains,
            joint_limits,
            safety: SafetyConfig::default(),
        }
    }
}

impl ConfigValidation for RealtimeConfig {
    fn validate(&self) -> Result<()> {
        if self.control_frequency <= 0.0 {
            return Err(anyhow::anyhow!("控制频率必须大于0"));
        }
        
        if self.sensor_frequency <= 0.0 {
            return Err(anyhow::anyhow!("传感器频率必须大于0"));
        }
        
        if self.max_acceleration <= 0.0 {
            return Err(anyhow::anyhow!("最大加速度必须大于0"));
        }
        
        if self.max_velocity <= 0.0 {
            return Err(anyhow::anyhow!("最大速度必须大于0"));
        }
        
        if self.position_tolerance <= 0.0 {
            return Err(anyhow::anyhow!("位置容差必须大于0"));
        }
        
        if self.velocity_tolerance <= 0.0 {
            return Err(anyhow::anyhow!("速度容差必须大于0"));
        }
        
        for (name, gains) in &self.pid_gains {
            gains.validate().map_err(|e| {
                anyhow::anyhow!("关节 '{}' 的PID参数无效: {}", name, e)
            })?;
        }
        
        for (name, limits) in &self.joint_limits {
            limits.validate().map_err(|e| {
                anyhow::anyhow!("关节 '{}' 的限制参数无效: {}", name, e)
            })?;
        }
        
        self.safety.validate()?;
        
        Ok(())
    }
}

/// PID控制器参数
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIDGains {
    pub kp: f64,
    pub ki: f64,
    pub kd: f64,
    pub max_integral: f64,
    pub max_output: f64,
}

impl ConfigValidation for PIDGains {
    fn validate(&self) -> Result<()> {
        if self.kp < 0.0 {
            return Err(anyhow::anyhow!("比例增益不能为负数"));
        }
        
        if self.ki < 0.0 {
            return Err(anyhow::anyhow!("积分增益不能为负数"));
        }
        
        if self.kd < 0.0 {
            return Err(anyhow::anyhow!("微分增益不能为负数"));
        }
        
        if self.max_integral <= 0.0 {
            return Err(anyhow::anyhow!("最大积分值必须大于0"));
        }
        
        if self.max_output <= 0.0 {
            return Err(anyhow::anyhow!("最大输出值必须大于0"));
        }
        
        Ok(())
    }
}

/// 关节限制
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JointLimits {
    pub min_position: f64,
    pub max_position: f64,
    pub max_velocity: f64,
    pub max_acceleration: f64,
    pub max_torque: f64,
}

impl ConfigValidation for JointLimits {
    fn validate(&self) -> Result<()> {
        if self.min_position >= self.max_position {
            return Err(anyhow::anyhow!("最小位置必须小于最大位置"));
        }
        
        if self.max_velocity <= 0.0 {
            return Err(anyhow::anyhow!("最大速度必须大于0"));
        }
        
        if self.max_acceleration <= 0.0 {
            return Err(anyhow::anyhow!("最大加速度必须大于0"));
        }
        
        if self.max_torque <= 0.0 {
            return Err(anyhow::anyhow!("最大扭矩必须大于0"));
        }
        
        Ok(())
    }
}

/// 安全配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetyConfig {
    pub emergency_stop_enabled: bool,
    pub collision_detection: bool,
    pub force_limit: f64,
    pub temperature_limit: f64,
    pub voltage_range: (f64, f64),
    pub watchdog_timeout_ms: u64,
}

impl Default for SafetyConfig {
    fn default() -> Self {
        Self {
            emergency_stop_enabled: true,
            collision_detection: true,
            force_limit: 50.0,      // N
            temperature_limit: 80.0, // °C
            voltage_range: (11.0, 13.0), // V
            watchdog_timeout_ms: 1000,
        }
    }
}

impl ConfigValidation for SafetyConfig {
    fn validate(&self) -> Result<()> {
        if self.force_limit <= 0.0 {
            return Err(anyhow::anyhow!("力限制必须大于0"));
        }
        
        if self.temperature_limit <= 0.0 {
            return Err(anyhow::anyhow!("温度限制必须大于0"));
        }
        
        if self.voltage_range.0 >= self.voltage_range.1 {
            return Err(anyhow::anyhow!("电压范围无效"));
        }
        
        if self.watchdog_timeout_ms == 0 {
            return Err(anyhow::anyhow!("看门狗超时时间必须大于0"));
        }
        
        Ok(())
    }
}

/// 硬件配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareConfig {
    pub enabled: bool,
    pub serial_port: String,
    pub baud_rate: u32,
    pub timeout_ms: u64,
    pub retry_count: u32,
    pub heartbeat_interval_ms: u64,
    pub servos: HashMap<String, ServoConfig>,
    pub sensors: HashMap<String, SensorConfig>,
    pub gpio: GPIOConfig,
}

impl Default for HardwareConfig {
    fn default() -> Self {
        let mut servos = HashMap::new();
        let mut sensors = HashMap::new();
        
        // 默认舵机配置
        let servo_names = vec![
            "head_pan", "head_tilt",
            "left_shoulder_pitch", "left_shoulder_roll", "left_elbow_pitch",
            "right_shoulder_pitch", "right_shoulder_roll", "right_elbow_pitch",
        ];
        
        for (i, name) in servo_names.iter().enumerate() {
            servos.insert(name.to_string(), ServoConfig {
                id: i as u8 + 1,
                min_angle: -180.0,
                max_angle: 180.0,
                center_offset: 0.0,
                direction: 1,
                max_speed: 100,
                max_torque: 1023,
                enabled: true,
            });
        }
        
        // 默认传感器配置
        sensors.insert("imu".to_string(), SensorConfig {
            sensor_type: SensorType::IMU,
            address: 0x68,
            frequency: 100.0,
            enabled: true,
            calibration_file: Some("imu_calibration.yaml".to_string()),
        });
        
        sensors.insert("force_torque".to_string(), SensorConfig {
            sensor_type: SensorType::ForceTorque,
            address: 0x40,
            frequency: 50.0,
            enabled: true,
            calibration_file: Some("ft_calibration.yaml".to_string()),
        });
        
        Self {
            enabled: true,
            serial_port: "/dev/ttyUSB0".to_string(),
            baud_rate: 115200,
            timeout_ms: 1000,
            retry_count: 3,
            heartbeat_interval_ms: 100,
            servos,
            sensors,
            gpio: GPIOConfig::default(),
        }
    }
}

impl ConfigValidation for HardwareConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.serial_port.is_empty() {
            return Err(anyhow::anyhow!("串口路径不能为空"));
        }
        
        if self.baud_rate == 0 {
            return Err(anyhow::anyhow!("波特率必须大于0"));
        }
        
        if self.timeout_ms == 0 {
            return Err(anyhow::anyhow!("超时时间必须大于0"));
        }
        
        if self.heartbeat_interval_ms == 0 {
            return Err(anyhow::anyhow!("心跳间隔必须大于0"));
        }
        
        for (name, servo) in &self.servos {
            servo.validate().map_err(|e| {
                anyhow::anyhow!("舵机 '{}' 配置无效: {}", name, e)
            })?;
        }
        
        for (name, sensor) in &self.sensors {
            sensor.validate().map_err(|e| {
                anyhow::anyhow!("传感器 '{}' 配置无效: {}", name, e)
            })?;
        }
        
        self.gpio.validate()?;
        
        Ok(())
    }
}

/// 舵机配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServoConfig {
    pub id: u8,
    pub min_angle: f64,
    pub max_angle: f64,
    pub center_offset: f64,
    pub direction: i8,
    pub max_speed: u16,
    pub max_torque: u16,
    pub enabled: bool,
}

impl ConfigValidation for ServoConfig {
    fn validate(&self) -> Result<()> {
        if self.min_angle >= self.max_angle {
            return Err(anyhow::anyhow!("最小角度必须小于最大角度"));
        }
        
        if self.direction != 1 && self.direction != -1 {
            return Err(anyhow::anyhow!("方向必须是1或-1"));
        }
        
        if self.max_speed == 0 {
            return Err(anyhow::anyhow!("最大速度必须大于0"));
        }
        
        if self.max_torque == 0 {
            return Err(anyhow::anyhow!("最大扭矩必须大于0"));
        }
        
        Ok(())
    }
}

/// 传感器配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorConfig {
    pub sensor_type: SensorType,
    pub address: u8,
    pub frequency: f64,
    pub enabled: bool,
    pub calibration_file: Option<String>,
}

impl ConfigValidation for SensorConfig {
    fn validate(&self) -> Result<()> {
        if self.frequency <= 0.0 {
            return Err(anyhow::anyhow!("传感器频率必须大于0"));
        }
        
        Ok(())
    }
}

/// 传感器类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SensorType {
    IMU,
    ForceTorque,
    Temperature,
    Voltage,
    Current,
}

/// GPIO配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GPIOConfig {
    pub enabled: bool,
    pub pins: HashMap<String, GPIOPinConfig>,
}

impl Default for GPIOConfig {
    fn default() -> Self {
        let mut pins = HashMap::new();
        
        // LED控制引脚
        pins.insert("led_red".to_string(), GPIOPinConfig {
            pin: 18,
            mode: GPIOMode::Output,
            pull: GPIOPull::None,
            initial_state: false,
        });
        
        pins.insert("led_green".to_string(), GPIOPinConfig {
            pin: 19,
            mode: GPIOMode::Output,
            pull: GPIOPull::None,
            initial_state: false,
        });
        
        pins.insert("led_blue".to_string(), GPIOPinConfig {
            pin: 20,
            mode: GPIOMode::Output,
            pull: GPIOPull::None,
            initial_state: false,
        });
        
        // 紧急停止按钮
        pins.insert("emergency_stop".to_string(), GPIOPinConfig {
            pin: 21,
            mode: GPIOMode::Input,
            pull: GPIOPull::Up,
            initial_state: false,
        });
        
        Self {
            enabled: true,
            pins,
        }
    }
}

impl ConfigValidation for GPIOConfig {
    fn validate(&self) -> Result<()> {
        for (name, pin_config) in &self.pins {
            pin_config.validate().map_err(|e| {
                anyhow::anyhow!("GPIO引脚 '{}' 配置无效: {}", name, e)
            })?;
        }
        
        Ok(())
    }
}

/// GPIO引脚配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GPIOPinConfig {
    pub pin: u8,
    pub mode: GPIOMode,
    pub pull: GPIOPull,
    pub initial_state: bool,
}

impl ConfigValidation for GPIOPinConfig {
    fn validate(&self) -> Result<()> {
        if self.pin > 40 {
            return Err(anyhow::anyhow!("GPIO引脚号不能超过40"));
        }
        
        Ok(())
    }
}

/// GPIO模式
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GPIOMode {
    Input,
    Output,
    PWM,
}

/// GPIO上拉/下拉
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GPIOPull {
    None,
    Up,
    Down,
}

/// AI配置（从ai.rs重新导出）
use crate::ai::AIConfig;

/// 日志配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub level: LogLevel,
    pub console_output: bool,
    pub file_output: bool,
    pub log_directory: PathBuf,
    pub max_file_size_mb: u64,
    pub max_files: u32,
    pub rotation_interval: RotationInterval,
    pub modules: HashMap<String, LogLevel>,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        let mut modules = HashMap::new();
        modules.insert("reachy_mini".to_string(), LogLevel::Info);
        modules.insert("vision".to_string(), LogLevel::Debug);
        modules.insert("realtime".to_string(), LogLevel::Warn);
        modules.insert("hardware".to_string(), LogLevel::Info);
        modules.insert("ai".to_string(), LogLevel::Info);
        
        Self {
            level: LogLevel::Info,
            console_output: true,
            file_output: true,
            log_directory: PathBuf::from("./logs"),
            max_file_size_mb: 100,
            max_files: 10,
            rotation_interval: RotationInterval::Daily,
            modules,
        }
    }
}

impl ConfigValidation for LoggingConfig {
    fn validate(&self) -> Result<()> {
        if self.max_file_size_mb == 0 {
            return Err(anyhow::anyhow!("最大文件大小必须大于0"));
        }
        
        if self.max_files == 0 {
            return Err(anyhow::anyhow!("最大文件数必须大于0"));
        }
        
        Ok(())
    }
}

/// 日志级别
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogLevel {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
}

/// 日志轮转间隔
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RotationInterval {
    Hourly,
    Daily,
    Weekly,
    Monthly,
}

/// 网络配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkConfig {
    pub enabled: bool,
    pub bind_address: String,
    pub port: u16,
    pub max_connections: usize,
    pub timeout_ms: u64,
    pub websocket: WebSocketConfig,
    pub http: HttpConfig,
    pub cors: CorsConfig,
}

impl Default for NetworkConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            bind_address: "0.0.0.0".to_string(),
            port: 8080,
            max_connections: 100,
            timeout_ms: 30000,
            websocket: WebSocketConfig::default(),
            http: HttpConfig::default(),
            cors: CorsConfig::default(),
        }
    }
}

impl ConfigValidation for NetworkConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.bind_address.is_empty() {
            return Err(anyhow::anyhow!("绑定地址不能为空"));
        }
        
        if self.port == 0 {
            return Err(anyhow::anyhow!("端口号不能为0"));
        }
        
        if self.max_connections == 0 {
            return Err(anyhow::anyhow!("最大连接数必须大于0"));
        }
        
        if self.timeout_ms == 0 {
            return Err(anyhow::anyhow!("超时时间必须大于0"));
        }
        
        self.websocket.validate()?;
        self.http.validate()?;
        self.cors.validate()?;
        
        Ok(())
    }
}

/// WebSocket配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSocketConfig {
    pub enabled: bool,
    pub path: String,
    pub max_frame_size: usize,
    pub max_message_size: usize,
    pub ping_interval_ms: u64,
    pub pong_timeout_ms: u64,
}

impl Default for WebSocketConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            path: "/ws".to_string(),
            max_frame_size: 1024 * 1024,     // 1MB
            max_message_size: 10 * 1024 * 1024, // 10MB
            ping_interval_ms: 30000,          // 30s
            pong_timeout_ms: 10000,           // 10s
        }
    }
}

impl ConfigValidation for WebSocketConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.path.is_empty() {
            return Err(anyhow::anyhow!("WebSocket路径不能为空"));
        }
        
        if self.max_frame_size == 0 {
            return Err(anyhow::anyhow!("最大帧大小必须大于0"));
        }
        
        if self.max_message_size == 0 {
            return Err(anyhow::anyhow!("最大消息大小必须大于0"));
        }
        
        if self.ping_interval_ms == 0 {
            return Err(anyhow::anyhow!("Ping间隔必须大于0"));
        }
        
        if self.pong_timeout_ms == 0 {
            return Err(anyhow::anyhow!("Pong超时时间必须大于0"));
        }
        
        Ok(())
    }
}

/// HTTP配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HttpConfig {
    pub enabled: bool,
    pub max_request_size: usize,
    pub request_timeout_ms: u64,
    pub keep_alive: bool,
    pub compression: bool,
    pub static_files: Option<StaticFilesConfig>,
}

impl Default for HttpConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_request_size: 10 * 1024 * 1024, // 10MB
            request_timeout_ms: 30000,           // 30s
            keep_alive: true,
            compression: true,
            static_files: Some(StaticFilesConfig::default()),
        }
    }
}

impl ConfigValidation for HttpConfig {
    fn validate(&self) -> Result<()> {
        if self.max_request_size == 0 {
            return Err(anyhow::anyhow!("最大请求大小必须大于0"));
        }
        
        if self.request_timeout_ms == 0 {
            return Err(anyhow::anyhow!("请求超时时间必须大于0"));
        }
        
        if let Some(ref static_config) = self.static_files {
            static_config.validate()?;
        }
        
        Ok(())
    }
}

/// 静态文件配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StaticFilesConfig {
    pub enabled: bool,
    pub path: String,
    pub directory: PathBuf,
    pub index_file: String,
    pub cache_max_age: u64,
}

impl Default for StaticFilesConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            path: "/".to_string(),
            directory: PathBuf::from("./frontend/dist"),
            index_file: "index.html".to_string(),
            cache_max_age: 3600, // 1 hour
        }
    }
}

impl ConfigValidation for StaticFilesConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.path.is_empty() {
            return Err(anyhow::anyhow!("静态文件路径不能为空"));
        }
        
        if self.enabled && self.index_file.is_empty() {
            return Err(anyhow::anyhow!("索引文件名不能为空"));
        }
        
        Ok(())
    }
}

/// CORS配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorsConfig {
    pub enabled: bool,
    pub allowed_origins: Vec<String>,
    pub allowed_methods: Vec<String>,
    pub allowed_headers: Vec<String>,
    pub max_age: u64,
}

impl Default for CorsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            allowed_origins: vec!["*".to_string()],
            allowed_methods: vec![
                "GET".to_string(),
                "POST".to_string(),
                "PUT".to_string(),
                "DELETE".to_string(),
                "OPTIONS".to_string(),
            ],
            allowed_headers: vec![
                "Content-Type".to_string(),
                "Authorization".to_string(),
                "X-Requested-With".to_string(),
            ],
            max_age: 3600,
        }
    }
}

impl ConfigValidation for CorsConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.allowed_origins.is_empty() {
            return Err(anyhow::anyhow!("允许的源不能为空"));
        }
        
        if self.enabled && self.allowed_methods.is_empty() {
            return Err(anyhow::anyhow!("允许的方法不能为空"));
        }
        
        Ok(())
    }
}

/// 安全配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub enabled: bool,
    pub authentication: AuthConfig,
    pub rate_limiting: RateLimitConfig,
    pub encryption: EncryptionConfig,
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            enabled: false, // 开发环境默认关闭
            authentication: AuthConfig::default(),
            rate_limiting: RateLimitConfig::default(),
            encryption: EncryptionConfig::default(),
        }
    }
}

impl ConfigValidation for SecurityConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled {
            self.authentication.validate()?;
            self.rate_limiting.validate()?;
            self.encryption.validate()?;
        }
        
        Ok(())
    }
}

/// 认证配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    pub enabled: bool,
    pub jwt_secret: String,
    pub token_expiry_hours: u64,
    pub refresh_token_expiry_days: u64,
}

impl Default for AuthConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            jwt_secret: "your-secret-key".to_string(),
            token_expiry_hours: 24,
            refresh_token_expiry_days: 30,
        }
    }
}

impl ConfigValidation for AuthConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.jwt_secret.len() < 32 {
            return Err(anyhow::anyhow!("JWT密钥长度必须至少32个字符"));
        }
        
        if self.token_expiry_hours == 0 {
            return Err(anyhow::anyhow!("令牌过期时间必须大于0"));
        }
        
        if self.refresh_token_expiry_days == 0 {
            return Err(anyhow::anyhow!("刷新令牌过期时间必须大于0"));
        }
        
        Ok(())
    }
}

/// 限流配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub enabled: bool,
    pub requests_per_minute: u32,
    pub burst_size: u32,
    pub whitelist: Vec<String>,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            requests_per_minute: 60,
            burst_size: 10,
            whitelist: vec!["127.0.0.1".to_string()],
        }
    }
}

impl ConfigValidation for RateLimitConfig {
    fn validate(&self) -> Result<()> {
        if self.requests_per_minute == 0 {
            return Err(anyhow::anyhow!("每分钟请求数必须大于0"));
        }
        
        if self.burst_size == 0 {
            return Err(anyhow::anyhow!("突发大小必须大于0"));
        }
        
        Ok(())
    }
}

/// 加密配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptionConfig {
    pub enabled: bool,
    pub algorithm: String,
    pub key_size: u32,
}

impl Default for EncryptionConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            algorithm: "AES-256-GCM".to_string(),
            key_size: 256,
        }
    }
}

impl ConfigValidation for EncryptionConfig {
    fn validate(&self) -> Result<()> {
        if self.enabled && self.algorithm.is_empty() {
            return Err(anyhow::anyhow!("加密算法不能为空"));
        }
        
        if self.key_size == 0 {
            return Err(anyhow::anyhow!("密钥大小必须大于0"));
        }
        
        Ok(())
    }
}

/// 性能配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    pub thread_pool_size: usize,
    pub async_runtime_threads: usize,
    pub memory_pool_size_mb: usize,
    pub gc_interval_ms: u64,
    pub profiling_enabled: bool,
    pub metrics_enabled: bool,
    pub cache: CacheConfig,
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            thread_pool_size: num_cpus::get(),
            async_runtime_threads: num_cpus::get(),
            memory_pool_size_mb: 512,
            gc_interval_ms: 60000, // 1 minute
            profiling_enabled: false,
            metrics_enabled: true,
            cache: CacheConfig::default(),
        }
    }
}

impl ConfigValidation for PerformanceConfig {
    fn validate(&self) -> Result<()> {
        if self.thread_pool_size == 0 {
            return Err(anyhow::anyhow!("线程池大小必须大于0"));
        }
        
        if self.async_runtime_threads == 0 {
            return Err(anyhow::anyhow!("异步运行时线程数必须大于0"));
        }
        
        if self.memory_pool_size_mb == 0 {
            return Err(anyhow::anyhow!("内存池大小必须大于0"));
        }
        
        if self.gc_interval_ms == 0 {
            return Err(anyhow::anyhow!("垃圾回收间隔必须大于0"));
        }
        
        self.cache.validate()?;
        
        Ok(())
    }
}

/// 缓存配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub enabled: bool,
    pub max_size_mb: usize,
    pub ttl_seconds: u64,
    pub cleanup_interval_ms: u64,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_size_mb: 256,
            ttl_seconds: 3600, // 1 hour
            cleanup_interval_ms: 300000, // 5 minutes
        }
    }
}

impl ConfigValidation for CacheConfig {
    fn validate(&self) -> Result<()> {
        if self.max_size_mb == 0 {
            return Err(anyhow::anyhow!("缓存最大大小必须大于0"));
        }
        
        if self.ttl_seconds == 0 {
            return Err(anyhow::anyhow!("TTL必须大于0"));
        }
        
        if self.cleanup_interval_ms == 0 {
            return Err(anyhow::anyhow!("清理间隔必须大于0"));
        }
        
        Ok(())
    }
}

/// 配置管理器
pub struct ConfigManager {
    config: Config,
    config_path: PathBuf,
    watchers: Vec<Box<dyn ConfigWatcher>>,
}

/// 配置监听器
pub trait ConfigWatcher: Send + Sync {
    fn on_config_changed(&self, config: &Config) -> Result<()>;
}

impl ConfigManager {
    /// 创建新的配置管理器
    pub fn new() -> Self {
        Self {
            config: Config::default(),
            config_path: PathBuf::from("config.yaml"),
            watchers: Vec::new(),
        }
    }
    
    /// 从文件加载配置
    pub fn load_from_file<P: AsRef<Path>>(&mut self, path: P) -> Result<()> {
        let path = path.as_ref();
        self.config_path = path.to_path_buf();
        
        info!("从文件加载配置: {}", path.display());
        
        if !path.exists() {
            warn!("配置文件不存在，使用默认配置: {}", path.display());
            self.save_to_file(path)?;
            return Ok(());
        }
        
        let content = fs::read_to_string(path)
            .map_err(|e| anyhow::anyhow!("读取配置文件失败: {}", e))?;
        
        self.config = serde_yaml::from_str(&content)
            .map_err(|e| anyhow::anyhow!("解析配置文件失败: {}", e))?;
        
        // 验证配置
        self.config.validate()?;
        
        // 应用环境变量覆盖
        self.apply_env_overrides()?;
        
        info!("配置加载完成");
        Ok(())
    }
    
    /// 保存配置到文件
    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let path = path.as_ref();
        
        info!("保存配置到文件: {}", path.display());
        
        // 创建目录
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| anyhow::anyhow!("创建配置目录失败: {}", e))?;
        }
        
        let content = serde_yaml::to_string(&self.config)
            .map_err(|e| anyhow::anyhow!("序列化配置失败: {}", e))?;
        
        fs::write(path, content)
            .map_err(|e| anyhow::anyhow!("写入配置文件失败: {}", e))?;
        
        info!("配置保存完成");
        Ok(())
    }
    
    /// 应用环境变量覆盖
    fn apply_env_overrides(&mut self) -> Result<()> {
        debug!("应用环境变量覆盖...");
        
        // 系统配置
        if let Ok(debug_mode) = env::var("REACHY_DEBUG") {
            self.config.system.debug_mode = debug_mode.parse().unwrap_or(false);
        }
        
        if let Ok(max_threads) = env::var("REACHY_MAX_THREADS") {
            if let Ok(threads) = max_threads.parse::<usize>() {
                self.config.system.max_threads = threads;
            }
        }
        
        // 网络配置
        if let Ok(port) = env::var("REACHY_PORT") {
            if let Ok(port_num) = port.parse::<u16>() {
                self.config.network.port = port_num;
            }
        }
        
        if let Ok(bind_addr) = env::var("REACHY_BIND_ADDRESS") {
            self.config.network.bind_address = bind_addr;
        }
        
        // 日志配置
        if let Ok(log_level) = env::var("REACHY_LOG_LEVEL") {
            self.config.logging.level = match log_level.to_lowercase().as_str() {
                "trace" => LogLevel::Trace,
                "debug" => LogLevel::Debug,
                "info" => LogLevel::Info,
                "warn" => LogLevel::Warn,
                "error" => LogLevel::Error,
                _ => LogLevel::Info,
            };
        }
        
        // 硬件配置
        if let Ok(serial_port) = env::var("REACHY_SERIAL_PORT") {
            self.config.hardware.serial_port = serial_port;
        }
        
        if let Ok(baud_rate) = env::var("REACHY_BAUD_RATE") {
            if let Ok(rate) = baud_rate.parse::<u32>() {
                self.config.hardware.baud_rate = rate;
            }
        }
        
        debug!("环境变量覆盖完成");
        Ok(())
    }
    
    /// 获取配置
    pub fn get_config(&self) -> &Config {
        &self.config
    }
    
    /// 获取可变配置
    pub fn get_config_mut(&mut self) -> &mut Config {
        &mut self.config
    }
    
    /// 更新配置
    pub fn update_config(&mut self, new_config: Config) -> Result<()> {
        // 验证新配置
        new_config.validate()?;
        
        let old_config = self.config.clone();
        self.config = new_config;
        
        // 通知监听器
        for watcher in &self.watchers {
            if let Err(e) = watcher.on_config_changed(&self.config) {
                error!("配置变更通知失败: {}", e);
                // 回滚配置
                self.config = old_config;
                return Err(e);
            }
        }
        
        // 保存到文件
        self.save_to_file(&self.config_path)?;
        
        info!("配置更新完成");
        Ok(())
    }
    
    /// 添加配置监听器
    pub fn add_watcher(&mut self, watcher: Box<dyn ConfigWatcher>) {
        self.watchers.push(watcher);
    }
    
    /// 重新加载配置
    pub fn reload(&mut self) -> Result<()> {
        info!("重新加载配置...");
        self.load_from_file(&self.config_path.clone())?;
        
        // 通知监听器
        for watcher in &self.watchers {
            if let Err(e) = watcher.on_config_changed(&self.config) {
                error!("配置重载通知失败: {}", e);
            }
        }
        
        info!("配置重载完成");
        Ok(())
    }
    
    /// 验证配置
    pub fn validate(&self) -> Result<()> {
        self.config.validate()
    }
    
    /// 获取配置摘要
    pub fn get_summary(&self) -> ConfigSummary {
        ConfigSummary {
            system_name: self.config.system.name.clone(),
            version: self.config.system.version.clone(),
            environment: self.config.system.environment.clone(),
            debug_mode: self.config.system.debug_mode,
            vision_enabled: self.config.vision.enabled,
            realtime_enabled: self.config.realtime.enabled,
            hardware_enabled: self.config.hardware.enabled,
            ai_enabled: self.config.ai.enabled,
            network_port: self.config.network.port,
            log_level: self.config.logging.level.clone(),
        }
    }
}

/// 配置摘要
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigSummary {
    pub system_name: String,
    pub version: String,
    pub environment: Environment,
    pub debug_mode: bool,
    pub vision_enabled: bool,
    pub realtime_enabled: bool,
    pub hardware_enabled: bool,
    pub ai_enabled: bool,
    pub network_port: u16,
    pub log_level: LogLevel,
}

/// 全局配置实例
static mut GLOBAL_CONFIG: Option<ConfigManager> = None;
static CONFIG_INIT: std::sync::Once = std::sync::Once::new();

/// 初始化全局配置
pub fn init_global_config() -> Result<()> {
    CONFIG_INIT.call_once(|| {
        let mut config_manager = ConfigManager::new();
        
        // 尝试从默认路径加载配置
        let config_paths = vec![
            "config.yaml",
            "config/config.yaml",
            "/etc/reachy-mini/config.yaml",
            "~/.config/reachy-mini/config.yaml",
        ];
        
        for path in config_paths {
            if Path::new(path).exists() {
                if let Err(e) = config_manager.load_from_file(path) {
                    error!("加载配置文件失败 {}: {}", path, e);
                } else {
                    info!("成功加载配置文件: {}", path);
                    break;
                }
            }
        }
        
        unsafe {
            GLOBAL_CONFIG = Some(config_manager);
        }
    });
    
    Ok(())
}

/// 获取全局配置
pub fn get_global_config() -> Result<&'static Config> {
    unsafe {
        GLOBAL_CONFIG
            .as_ref()
            .map(|cm| cm.get_config())
            .ok_or_else(|| anyhow::anyhow!("全局配置未初始化"))
    }
}

/// 获取全局配置管理器
pub fn get_global_config_manager() -> Result<&'static mut ConfigManager> {
    unsafe {
        GLOBAL_CONFIG
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("全局配置管理器未初始化"))
    }
}

/// 重新加载全局配置
pub fn reload_global_config() -> Result<()> {
    let config_manager = get_global_config_manager()?;
    config_manager.reload()
}

/// 更新全局配置
pub fn update_global_config(new_config: Config) -> Result<()> {
    let config_manager = get_global_config_manager()?;
    config_manager.update_config(new_config)
}

/// 配置构建器
pub struct ConfigBuilder {
    config: Config,
}

impl ConfigBuilder {
    /// 创建新的配置构建器
    pub fn new() -> Self {
        Self {
            config: Config::default(),
        }
    }
    
    /// 设置系统配置
    pub fn system(mut self, system_config: SystemConfig) -> Self {
        self.config.system = system_config;
        self
    }
    
    /// 设置视觉配置
    pub fn vision(mut self, vision_config: VisionConfig) -> Self {
        self.config.vision = vision_config;
        self
    }
    
    /// 设置实时控制配置
    pub fn realtime(mut self, realtime_config: RealtimeConfig) -> Self {
        self.config.realtime = realtime_config;
        self
    }
    
    /// 设置硬件配置
    pub fn hardware(mut self, hardware_config: HardwareConfig) -> Self {
        self.config.hardware = hardware_config;
        self
    }
    
    /// 设置AI配置
    pub fn ai(mut self, ai_config: AIConfig) -> Self {
        self.config.ai = ai_config;
        self
    }
    
    /// 设置日志配置
    pub fn logging(mut self, logging_config: LoggingConfig) -> Self {
        self.config.logging = logging_config;
        self
    }
    
    /// 设置网络配置
    pub fn network(mut self, network_config: NetworkConfig) -> Self {
        self.config.network = network_config;
        self
    }
    
    /// 设置安全配置
    pub fn security(mut self, security_config: SecurityConfig) -> Self {
        self.config.security = security_config;
        self
    }
    
    /// 设置性能配置
    pub fn performance(mut self, performance_config: PerformanceConfig) -> Self {
        self.config.performance = performance_config;
        self
    }
    
    /// 构建配置
    pub fn build(self) -> Result<Config> {
        self.config.validate()?;
        Ok(self.config)
    }
}

impl Default for ConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_config_validation() {
        let config = Config::default();
        assert!(config.validate().is_ok());
    }
    
    #[test]
    fn test_system_config_validation() {
        let mut config = SystemConfig::default();
        assert!(config.validate().is_ok());
        
        config.name = String::new();
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_vision_config_validation() {
        let mut config = VisionConfig::default();
        assert!(config.validate().is_ok());
        
        config.resolution = (0, 0);
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_realtime_config_validation() {
        let config = RealtimeConfig::default();
        assert!(config.validate().is_ok());
    }
    
    #[test]
    fn test_hardware_config_validation() {
        let config = HardwareConfig::default();
        assert!(config.validate().is_ok());
    }
    
    #[test]
    fn test_logging_config_validation() {
        let mut config = LoggingConfig::default();
        assert!(config.validate().is_ok());
        
        config.max_file_size_mb = 0;
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_network_config_validation() {
        let mut config = NetworkConfig::default();
        assert!(config.validate().is_ok());
        
        config.port = 0;
        assert!(config.validate().is_err());
    }
    
    #[test]
    fn test_config_builder() {
        let config = ConfigBuilder::new()
            .system(SystemConfig {
                name: "TestSystem".to_string(),
                ..SystemConfig::default()
            })
            .build();
        
        assert!(config.is_ok());
        let config = config.unwrap();
        assert_eq!(config.system.name, "TestSystem");
    }
    
    #[test]
    fn test_config_manager() {
        let mut manager = ConfigManager::new();
        let config = manager.get_config();
        assert_eq!(config.system.name, "ReachyMini");
    }
    
    #[test]
    fn test_pid_gains_validation() {
        let gains = PIDGains {
            kp: 1.0,
            ki: 0.1,
            kd: 0.01,
            max_integral: 10.0,
            max_output: 100.0,
        };
        assert!(gains.validate().is_ok());
        
        let mut invalid_gains = gains.clone();
        invalid_gains.kp = -1.0;
        assert!(invalid_gains.validate().is_err());
    }
    
    #[test]
    fn test_joint_limits_validation() {
        let limits = JointLimits {
            min_position: -180.0,
            max_position: 180.0,
            max_velocity: 90.0,
            max_acceleration: 180.0,
            max_torque: 10.0,
        };
        assert!(limits.validate().is_ok());
        
        let mut invalid_limits = limits.clone();
        invalid_limits.min_position = 200.0;
        assert!(invalid_limits.validate().is_err());
    }
    
    #[test]
    fn test_servo_config_validation() {
        let config = ServoConfig {
            id: 1,
            min_angle: -180.0,
            max_angle: 180.0,
            center_offset: 0.0,
            direction: 1,
            max_speed: 100,
            max_torque: 1023,
            enabled: true,
        };
        assert!(config.validate().is_ok());
        
        let mut invalid_config = config.clone();
        invalid_config.direction = 0;
        assert!(invalid_config.validate().is_err());
    }
    
    #[test]
    fn test_environment_enum() {
        let env = Environment::Development;
        assert_eq!(env, Environment::Development);
        
        let env = Environment::Production;
        assert_eq!(env, Environment::Production);
    }
    
    #[test]
    fn test_feature_detector_type() {
        let detector = FeatureDetectorType::SIFT;
        match detector {
            FeatureDetectorType::SIFT => assert!(true),
            _ => assert!(false),
        }
    }
    
    #[test]
    fn test_sensor_type() {
        let sensor = SensorType::IMU;
        match sensor {
            SensorType::IMU => assert!(true),
            _ => assert!(false),
        }
    }
    
    #[test]
    fn test_gpio_mode() {
        let mode = GPIOMode::Output;
        match mode {
            GPIOMode::Output => assert!(true),
            _ => assert!(false),
        }
    }
    
    #[test]
    fn test_log_level() {
        let level = LogLevel::Info;
        match level {
            LogLevel::Info => assert!(true),
            _ => assert!(false),
        }
    }
}