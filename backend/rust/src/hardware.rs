//! 硬件接口模块
//! 
//! 提供与Reachy Mini机器人硬件的底层通信接口，包括串口通信、I2C、GPIO等。

use crate::common::*;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, mpsc, Mutex};
use tokio::time::{interval, timeout};
use log::{info, warn, error, debug};

/// 硬件配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareConfig {
    pub serial_port: String,
    pub baud_rate: u32,
    pub i2c_bus: u8,
    pub gpio_pins: HashMap<String, u8>,
    pub servo_config: ServoConfig,
    pub sensor_config: SensorConfig,
    pub communication_timeout_ms: u64,
    pub retry_attempts: u32,
    pub heartbeat_interval_ms: u64,
}

impl Default for HardwareConfig {
    fn default() -> Self {
        let mut gpio_pins = HashMap::new();
        gpio_pins.insert("led_power".to_string(), 18);
        gpio_pins.insert("emergency_stop".to_string(), 19);
        gpio_pins.insert("status_led".to_string(), 20);
        
        Self {
            serial_port: "/dev/ttyUSB0".to_string(),
            baud_rate: 115200,
            i2c_bus: 1,
            gpio_pins,
            servo_config: ServoConfig::default(),
            sensor_config: SensorConfig::default(),
            communication_timeout_ms: 1000,
            retry_attempts: 3,
            heartbeat_interval_ms: 1000,
        }
    }
}

impl ConfigValidation for HardwareConfig {
    fn validate(&self) -> Result<()> {
        if self.serial_port.is_empty() {
            return Err(anyhow::anyhow!("串口路径不能为空"));
        }
        
        if self.baud_rate == 0 {
            return Err(anyhow::anyhow!("波特率必须大于0"));
        }
        
        if self.communication_timeout_ms == 0 {
            return Err(anyhow::anyhow!("通信超时时间必须大于0"));
        }
        
        self.servo_config.validate()?;
        self.sensor_config.validate()?;
        
        Ok(())
    }
}

/// 舵机配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServoConfig {
    pub servo_ids: Vec<u8>,
    pub position_limits: HashMap<u8, (i16, i16)>, // (min, max)
    pub speed_limits: HashMap<u8, u16>,
    pub torque_limits: HashMap<u8, u16>,
    pub temperature_limit: u8,
    pub voltage_limits: (f32, f32), // (min, max)
}

impl Default for ServoConfig {
    fn default() -> Self {
        let servo_ids = vec![1, 2, 3, 4, 5, 6, 7, 8]; // 8个舵机
        let mut position_limits = HashMap::new();
        let mut speed_limits = HashMap::new();
        let mut torque_limits = HashMap::new();
        
        for &id in &servo_ids {
            position_limits.insert(id, (-1800, 1800)); // ±180度
            speed_limits.insert(id, 1000); // 最大速度
            torque_limits.insert(id, 1000); // 最大扭矩
        }
        
        Self {
            servo_ids,
            position_limits,
            speed_limits,
            torque_limits,
            temperature_limit: 70, // 70°C
            voltage_limits: (6.0, 12.0), // 6V-12V
        }
    }
}

impl ConfigValidation for ServoConfig {
    fn validate(&self) -> Result<()> {
        if self.servo_ids.is_empty() {
            return Err(anyhow::anyhow!("舵机ID列表不能为空"));
        }
        
        if self.temperature_limit == 0 {
            return Err(anyhow::anyhow!("温度限制必须大于0"));
        }
        
        if self.voltage_limits.0 >= self.voltage_limits.1 {
            return Err(anyhow::anyhow!("电压限制范围无效"));
        }
        
        Ok(())
    }
}

/// 传感器配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorConfig {
    pub imu_address: u8,
    pub force_sensor_addresses: Vec<u8>,
    pub temperature_sensor_addresses: Vec<u8>,
    pub update_rate_hz: f64,
    pub calibration_samples: u32,
}

impl Default for SensorConfig {
    fn default() -> Self {
        Self {
            imu_address: 0x68, // MPU6050默认地址
            force_sensor_addresses: vec![0x48, 0x49], // 力传感器地址
            temperature_sensor_addresses: vec![0x4A], // 温度传感器地址
            update_rate_hz: 100.0,
            calibration_samples: 100,
        }
    }
}

impl ConfigValidation for SensorConfig {
    fn validate(&self) -> Result<()> {
        if self.update_rate_hz <= 0.0 {
            return Err(anyhow::anyhow!("传感器更新率必须大于0"));
        }
        
        if self.calibration_samples == 0 {
            return Err(anyhow::anyhow!("校准样本数必须大于0"));
        }
        
        Ok(())
    }
}

/// 硬件状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareStatus {
    pub is_connected: bool,
    pub serial_connected: bool,
    pub i2c_connected: bool,
    pub servo_status: HashMap<u8, ServoStatus>,
    pub sensor_status: SensorStatus,
    pub last_heartbeat: u64,
    pub communication_errors: u64,
    pub performance_stats: PerformanceStats,
}

impl Default for HardwareStatus {
    fn default() -> Self {
        Self {
            is_connected: false,
            serial_connected: false,
            i2c_connected: false,
            servo_status: HashMap::new(),
            sensor_status: SensorStatus::default(),
            last_heartbeat: 0,
            communication_errors: 0,
            performance_stats: PerformanceStats::new(),
        }
    }
}

/// 舵机状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServoStatus {
    pub id: u8,
    pub position: i16,
    pub speed: i16,
    pub load: i16,
    pub voltage: f32,
    pub temperature: u8,
    pub is_moving: bool,
    pub error_flags: u8,
    pub last_update: u64,
}

impl Default for ServoStatus {
    fn default() -> Self {
        Self {
            id: 0,
            position: 0,
            speed: 0,
            load: 0,
            voltage: 0.0,
            temperature: 0,
            is_moving: false,
            error_flags: 0,
            last_update: 0,
        }
    }
}

/// 传感器状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorStatus {
    pub imu_connected: bool,
    pub force_sensors_connected: Vec<bool>,
    pub temperature_sensors_connected: Vec<bool>,
    pub last_imu_update: u64,
    pub last_force_update: u64,
    pub last_temperature_update: u64,
    pub calibration_status: CalibrationStatus,
}

impl Default for SensorStatus {
    fn default() -> Self {
        Self {
            imu_connected: false,
            force_sensors_connected: Vec::new(),
            temperature_sensors_connected: Vec::new(),
            last_imu_update: 0,
            last_force_update: 0,
            last_temperature_update: 0,
            calibration_status: CalibrationStatus::NotCalibrated,
        }
    }
}

/// 校准状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CalibrationStatus {
    NotCalibrated,
    Calibrating,
    Calibrated,
    CalibrationFailed,
}

/// 硬件命令
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HardwareCommand {
    ServoMove {
        id: u8,
        position: i16,
        speed: Option<u16>,
    },
    ServoStop {
        id: u8,
    },
    ServoSetTorque {
        id: u8,
        enabled: bool,
    },
    ReadServoStatus {
        id: u8,
    },
    ReadAllServos,
    ReadIMU,
    ReadForceSensors,
    ReadTemperature,
    SetLED {
        pin: u8,
        state: bool,
    },
    EmergencyStop,
    Reset,
    Calibrate,
}

/// 硬件响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HardwareResponse {
    ServoStatus(ServoStatus),
    AllServoStatus(Vec<ServoStatus>),
    IMUData {
        acceleration: Vector3,
        angular_velocity: Vector3,
        orientation: Quaternion,
        temperature: f32,
    },
    ForceData(Vec<Vector3>),
    TemperatureData(Vec<f32>),
    CommandAck,
    Error(String),
}

/// 硬件错误
#[derive(Debug, thiserror::Error)]
pub enum HardwareError {
    #[error("串口错误: {0}")]
    Serial(String),
    
    #[error("I2C错误: {0}")]
    I2C(String),
    
    #[error("GPIO错误: {0}")]
    GPIO(String),
    
    #[error("舵机错误: {0}")]
    Servo(String),
    
    #[error("传感器错误: {0}")]
    Sensor(String),
    
    #[error("通信超时")]
    Timeout,
    
    #[error("协议错误: {0}")]
    Protocol(String),
    
    #[error("硬件未连接")]
    NotConnected,
}

/// 硬件接口
pub struct HardwareInterface {
    config: HardwareConfig,
    status: Arc<RwLock<HardwareStatus>>,
    command_queue: Arc<Mutex<mpsc::UnboundedReceiver<HardwareCommand>>>,
    command_sender: mpsc::UnboundedSender<HardwareCommand>,
    response_sender: Arc<Mutex<Option<mpsc::UnboundedSender<HardwareResponse>>>>,
    communication_handle: Option<tokio::task::JoinHandle<()>>,
    heartbeat_handle: Option<tokio::task::JoinHandle<()>>,
    is_running: Arc<RwLock<bool>>,
}

impl HardwareInterface {
    /// 创建新的硬件接口
    pub async fn new(config: HardwareConfig) -> Result<Self> {
        config.validate()?;
        
        info!("初始化硬件接口...");
        
        let status = Arc::new(RwLock::new(HardwareStatus::default()));
        let is_running = Arc::new(RwLock::new(false));
        
        let (command_sender, command_receiver) = mpsc::unbounded_channel();
        let command_queue = Arc::new(Mutex::new(command_receiver));
        
        let interface = Self {
            config,
            status,
            command_queue,
            command_sender,
            response_sender: Arc::new(Mutex::new(None)),
            communication_handle: None,
            heartbeat_handle: None,
            is_running,
        };
        
        info!("硬件接口初始化完成");
        Ok(interface)
    }
    
    /// 启动硬件接口
    pub async fn start(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if *is_running {
            return Ok(());
        }
        
        info!("启动硬件接口...");
        
        // 初始化硬件连接
        self.initialize_hardware().await?;
        
        // 启动通信循环
        self.start_communication_loop().await?;
        
        // 启动心跳循环
        self.start_heartbeat_loop().await?;
        
        *is_running = true;
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_connected = true;
        }
        
        info!("硬件接口启动完成");
        Ok(())
    }
    
    /// 停止硬件接口
    pub async fn stop(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if !*is_running {
            return Ok(());
        }
        
        info!("停止硬件接口...");
        
        *is_running = false;
        
        // 停止通信循环
        if let Some(handle) = self.communication_handle.take() {
            handle.abort();
        }
        
        // 停止心跳循环
        if let Some(handle) = self.heartbeat_handle.take() {
            handle.abort();
        }
        
        // 关闭硬件连接
        self.cleanup_hardware().await?;
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_connected = false;
            status.serial_connected = false;
            status.i2c_connected = false;
        }
        
        info!("硬件接口停止完成");
        Ok(())
    }
    
    /// 初始化硬件
    async fn initialize_hardware(&mut self) -> Result<()> {
        info!("初始化硬件连接...");
        
        // 初始化串口（模拟）
        match self.initialize_serial().await {
            Ok(_) => {
                let mut status = self.status.write().await;
                status.serial_connected = true;
                info!("串口连接成功: {}", self.config.serial_port);
            },
            Err(e) => {
                warn!("串口连接失败: {}", e);
            }
        }
        
        // 初始化I2C（模拟）
        match self.initialize_i2c().await {
            Ok(_) => {
                let mut status = self.status.write().await;
                status.i2c_connected = true;
                info!("I2C连接成功: bus {}", self.config.i2c_bus);
            },
            Err(e) => {
                warn!("I2C连接失败: {}", e);
            }
        }
        
        // 初始化GPIO（模拟）
        self.initialize_gpio().await?;
        
        // 初始化舵机状态
        self.initialize_servos().await?;
        
        // 初始化传感器
        self.initialize_sensors().await?;
        
        Ok(())
    }
    
    /// 初始化串口（模拟）
    async fn initialize_serial(&self) -> Result<()> {
        // 在实际实现中，这里会打开串口设备
        // 现在只是模拟成功
        debug!("模拟串口初始化: {} @ {}", self.config.serial_port, self.config.baud_rate);
        Ok(())
    }
    
    /// 初始化I2C（模拟）
    async fn initialize_i2c(&self) -> Result<()> {
        // 在实际实现中，这里会初始化I2C总线
        // 现在只是模拟成功
        debug!("模拟I2C初始化: bus {}", self.config.i2c_bus);
        Ok(())
    }
    
    /// 初始化GPIO（模拟）
    async fn initialize_gpio(&self) -> Result<()> {
        for (name, pin) in &self.config.gpio_pins {
            debug!("模拟GPIO初始化: {} -> pin {}", name, pin);
        }
        Ok(())
    }
    
    /// 初始化舵机
    async fn initialize_servos(&self) -> Result<()> {
        let mut status = self.status.write().await;
        
        for &servo_id in &self.config.servo_config.servo_ids {
            let servo_status = ServoStatus {
                id: servo_id,
                position: 0,
                speed: 0,
                load: 0,
                voltage: 8.0, // 模拟电压
                temperature: 25, // 模拟温度
                is_moving: false,
                error_flags: 0,
                last_update: current_timestamp(),
            };
            
            status.servo_status.insert(servo_id, servo_status);
            debug!("初始化舵机 {}", servo_id);
        }
        
        Ok(())
    }
    
    /// 初始化传感器
    async fn initialize_sensors(&self) -> Result<()> {
        let mut status = self.status.write().await;
        
        // 初始化IMU
        status.sensor_status.imu_connected = true;
        
        // 初始化力传感器
        status.sensor_status.force_sensors_connected = 
            vec![true; self.config.sensor_config.force_sensor_addresses.len()];
        
        // 初始化温度传感器
        status.sensor_status.temperature_sensors_connected = 
            vec![true; self.config.sensor_config.temperature_sensor_addresses.len()];
        
        info!("传感器初始化完成");
        Ok(())
    }
    
    /// 启动通信循环
    async fn start_communication_loop(&mut self) -> Result<()> {
        let command_queue = Arc::clone(&self.command_queue);
        let status = Arc::clone(&self.status);
        let is_running = Arc::clone(&self.is_running);
        let config = self.config.clone();
        
        let handle = tokio::spawn(async move {
            Self::communication_loop(
                command_queue,
                status,
                is_running,
                config,
            ).await
        });
        
        self.communication_handle = Some(handle);
        Ok(())
    }
    
    /// 通信循环
    async fn communication_loop(
        command_queue: Arc<Mutex<mpsc::UnboundedReceiver<HardwareCommand>>>,
        status: Arc<RwLock<HardwareStatus>>,
        is_running: Arc<RwLock<bool>>,
        config: HardwareConfig,
    ) {
        let mut queue = command_queue.lock().await;
        let timeout_duration = Duration::from_millis(config.communication_timeout_ms);
        
        loop {
            // 检查是否应该停止
            if !*is_running.read().await {
                break;
            }
            
            // 处理命令
            match timeout(Duration::from_millis(100), queue.recv()).await {
                Ok(Some(command)) => {
                    let start_time = Instant::now();
                    
                    match Self::process_command(command, &status, &config).await {
                        Ok(_) => {
                            debug!("命令处理成功");
                        },
                        Err(e) => {
                            error!("命令处理失败: {}", e);
                            
                            // 更新错误统计
                            let mut status = status.write().await;
                            status.communication_errors += 1;
                        }
                    }
                    
                    // 更新性能统计
                    let processing_time = start_time.elapsed();
                    let mut status = status.write().await;
                    status.performance_stats.update_frame_stats(processing_time);
                },
                Ok(None) => {
                    // 通道关闭
                    break;
                },
                Err(_) => {
                    // 超时，继续循环
                    continue;
                }
            }
        }
        
        info!("通信循环结束");
    }
    
    /// 处理硬件命令
    async fn process_command(
        command: HardwareCommand,
        status: &Arc<RwLock<HardwareStatus>>,
        config: &HardwareConfig,
    ) -> Result<()> {
        match command {
            HardwareCommand::ServoMove { id, position, speed } => {
                Self::process_servo_move(id, position, speed, status, config).await
            },
            HardwareCommand::ServoStop { id } => {
                Self::process_servo_stop(id, status).await
            },
            HardwareCommand::ReadServoStatus { id } => {
                Self::process_read_servo_status(id, status).await
            },
            HardwareCommand::ReadAllServos => {
                Self::process_read_all_servos(status).await
            },
            HardwareCommand::ReadIMU => {
                Self::process_read_imu(status).await
            },
            HardwareCommand::SetLED { pin, state } => {
                Self::process_set_led(pin, state).await
            },
            HardwareCommand::EmergencyStop => {
                Self::process_emergency_stop(status).await
            },
            _ => {
                debug!("暂不支持的命令: {:?}", command);
                Ok(())
            }
        }
    }
    
    /// 处理舵机移动命令
    async fn process_servo_move(
        id: u8,
        position: i16,
        speed: Option<u16>,
        status: &Arc<RwLock<HardwareStatus>>,
        config: &HardwareConfig,
    ) -> Result<()> {
        let mut status = status.write().await;
        
        if let Some(servo_status) = status.servo_status.get_mut(&id) {
            // 检查位置限制
            if let Some(&(min_pos, max_pos)) = config.servo_config.position_limits.get(&id) {
                let clamped_position = clamp(position, min_pos, max_pos);
                
                if clamped_position != position {
                    warn!("舵机 {} 位置 {} 超出限制，限制为 {}", id, position, clamped_position);
                }
                
                servo_status.position = clamped_position;
            } else {
                servo_status.position = position;
            }
            
            // 设置速度
            if let Some(spd) = speed {
                if let Some(&max_speed) = config.servo_config.speed_limits.get(&id) {
                    servo_status.speed = clamp(spd as i16, 0, max_speed as i16);
                }
            }
            
            servo_status.is_moving = true;
            servo_status.last_update = current_timestamp();
            
            debug!("舵机 {} 移动到位置 {}", id, servo_status.position);
        }
        
        Ok(())
    }
    
    /// 处理舵机停止命令
    async fn process_servo_stop(
        id: u8,
        status: &Arc<RwLock<HardwareStatus>>,
    ) -> Result<()> {
        let mut status = status.write().await;
        
        if let Some(servo_status) = status.servo_status.get_mut(&id) {
            servo_status.is_moving = false;
            servo_status.speed = 0;
            servo_status.last_update = current_timestamp();
            
            debug!("舵机 {} 停止", id);
        }
        
        Ok(())
    }
    
    /// 处理读取舵机状态命令
    async fn process_read_servo_status(
        id: u8,
        status: &Arc<RwLock<HardwareStatus>>,
    ) -> Result<()> {
        let mut status = status.write().await;
        
        if let Some(servo_status) = status.servo_status.get_mut(&id) {
            // 模拟读取硬件状态
            servo_status.voltage = 8.0 + (rand::random::<f32>() - 0.5) * 0.2;
            servo_status.temperature = 25 + (rand::random::<f32>() * 10.0) as u8;
            servo_status.load = (rand::random::<f32>() * 100.0) as i16;
            servo_status.last_update = current_timestamp();
            
            debug!("读取舵机 {} 状态", id);
        }
        
        Ok(())
    }
    
    /// 处理读取所有舵机状态命令
    async fn process_read_all_servos(
        status: &Arc<RwLock<HardwareStatus>>,
    ) -> Result<()> {
        let mut status = status.write().await;
        
        for servo_status in status.servo_status.values_mut() {
            // 模拟读取硬件状态
            servo_status.voltage = 8.0 + (rand::random::<f32>() - 0.5) * 0.2;
            servo_status.temperature = 25 + (rand::random::<f32>() * 10.0) as u8;
            servo_status.load = (rand::random::<f32>() * 100.0) as i16;
            servo_status.last_update = current_timestamp();
        }
        
        debug!("读取所有舵机状态");
        Ok(())
    }
    
    /// 处理读取IMU命令
    async fn process_read_imu(
        status: &Arc<RwLock<HardwareStatus>>,
    ) -> Result<()> {
        let mut status = status.write().await;
        status.sensor_status.last_imu_update = current_timestamp();
        
        debug!("读取IMU数据");
        Ok(())
    }
    
    /// 处理设置LED命令
    async fn process_set_led(
        pin: u8,
        state: bool,
    ) -> Result<()> {
        debug!("设置LED pin {} 状态: {}", pin, state);
        Ok(())
    }
    
    /// 处理紧急停止命令
    async fn process_emergency_stop(
        status: &Arc<RwLock<HardwareStatus>>,
    ) -> Result<()> {
        let mut status = status.write().await;
        
        // 停止所有舵机
        for servo_status in status.servo_status.values_mut() {
            servo_status.is_moving = false;
            servo_status.speed = 0;
            servo_status.last_update = current_timestamp();
        }
        
        warn!("执行紧急停止");
        Ok(())
    }
    
    /// 启动心跳循环
    async fn start_heartbeat_loop(&mut self) -> Result<()> {
        let heartbeat_interval = Duration::from_millis(self.config.heartbeat_interval_ms);
        let status = Arc::clone(&self.status);
        let is_running = Arc::clone(&self.is_running);
        
        let handle = tokio::spawn(async move {
            Self::heartbeat_loop(
                heartbeat_interval,
                status,
                is_running,
            ).await
        });
        
        self.heartbeat_handle = Some(handle);
        Ok(())
    }
    
    /// 心跳循环
    async fn heartbeat_loop(
        heartbeat_interval: Duration,
        status: Arc<RwLock<HardwareStatus>>,
        is_running: Arc<RwLock<bool>>,
    ) {
        let mut interval = interval(heartbeat_interval);
        
        loop {
            interval.tick().await;
            
            // 检查是否应该停止
            if !*is_running.read().await {
                break;
            }
            
            // 更新心跳时间戳
            {
                let mut status = status.write().await;
                status.last_heartbeat = current_timestamp();
            }
            
            debug!("心跳");
        }
        
        info!("心跳循环结束");
    }
    
    /// 清理硬件
    async fn cleanup_hardware(&self) -> Result<()> {
        info!("清理硬件连接...");
        
        // 在实际实现中，这里会关闭串口、I2C等连接
        // 现在只是模拟
        
        debug!("硬件连接清理完成");
        Ok(())
    }
    
    /// 发送命令
    pub async fn send_command(&self, command: HardwareCommand) -> Result<()> {
        self.command_sender.send(command)
            .map_err(|e| HardwareError::Protocol(format!("发送命令失败: {}", e)))?;
        Ok(())
    }
    
    /// 获取状态
    pub async fn get_status(&self) -> Result<HardwareStatus> {
        let status = self.status.read().await;
        Ok(status.clone())
    }
    
    /// 获取舵机状态
    pub async fn get_servo_status(&self, id: u8) -> Result<Option<ServoStatus>> {
        let status = self.status.read().await;
        Ok(status.servo_status.get(&id).cloned())
    }
    
    /// 获取所有舵机状态
    pub async fn get_all_servo_status(&self) -> Result<Vec<ServoStatus>> {
        let status = self.status.read().await;
        Ok(status.servo_status.values().cloned().collect())
    }
    
    /// 是否正在运行
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
    
    /// 是否已连接
    pub async fn is_connected(&self) -> bool {
        let status = self.status.read().await;
        status.is_connected
    }
}

impl LifecycleManager for HardwareInterface {
    async fn start(&mut self) -> Result<()> {
        self.start().await
    }
    
    async fn stop(&mut self) -> Result<()> {
        self.stop().await
    }
    
    fn is_running(&self) -> bool {
        // 注意：这是同步版本，异步版本在上面
        false // 占位符实现
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_hardware_config_validation() {
        let config = HardwareConfig::default();
        assert!(config.validate().is_ok());
        
        let mut invalid_config = config.clone();
        invalid_config.baud_rate = 0;
        assert!(invalid_config.validate().is_err());
    }
    
    #[tokio::test]
    async fn test_servo_config_validation() {
        let config = ServoConfig::default();
        assert!(config.validate().is_ok());
        
        let mut invalid_config = config.clone();
        invalid_config.servo_ids.clear();
        assert!(invalid_config.validate().is_err());
    }
    
    #[tokio::test]
    async fn test_hardware_interface_creation() {
        let config = HardwareConfig::default();
        let interface = HardwareInterface::new(config).await;
        assert!(interface.is_ok());
    }
    
    #[tokio::test]
    async fn test_servo_move_command() {
        let config = HardwareConfig::default();
        let mut interface = HardwareInterface::new(config).await.unwrap();
        
        let command = HardwareCommand::ServoMove {
            id: 1,
            position: 1000,
            speed: Some(500),
        };
        
        let result = interface.send_command(command).await;
        assert!(result.is_ok());
    }
}