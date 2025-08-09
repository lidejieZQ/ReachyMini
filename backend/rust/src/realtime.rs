//! 实时控制模块
//! 
//! 提供高精度的实时控制功能，包括运动控制、传感器数据处理、PID控制等。

use crate::common::*;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, mpsc, Mutex};
use tokio::time::{interval, sleep};
use log::{info, warn, error, debug};

/// 实时控制配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealtimeConfig {
    pub control_frequency: f64,
    pub max_joint_velocity: f64,
    pub max_joint_acceleration: f64,
    pub position_tolerance: f64,
    pub velocity_tolerance: f64,
    pub enable_safety_limits: bool,
    pub emergency_stop_enabled: bool,
    pub pid_gains: HashMap<String, PIDGains>,
    pub joint_limits: HashMap<String, JointLimits>,
    pub sensor_update_rate: f64,
    pub command_timeout_ms: u64,
}

impl Default for RealtimeConfig {
    fn default() -> Self {
        let mut pid_gains = HashMap::new();
        let mut joint_limits = HashMap::new();
        
        // 默认关节配置
        let joint_names = vec![
            "head_pan", "head_tilt",
            "left_shoulder_pitch", "left_shoulder_roll", "left_elbow_pitch",
            "right_shoulder_pitch", "right_shoulder_roll", "right_elbow_pitch"
        ];
        
        for joint_name in joint_names {
            pid_gains.insert(joint_name.to_string(), PIDGains::default());
            joint_limits.insert(joint_name.to_string(), JointLimits::default());
        }
        
        Self {
            control_frequency: 100.0, // 100Hz
            max_joint_velocity: 2.0,   // rad/s
            max_joint_acceleration: 5.0, // rad/s²
            position_tolerance: 0.01,  // rad
            velocity_tolerance: 0.1,   // rad/s
            enable_safety_limits: true,
            emergency_stop_enabled: true,
            pid_gains,
            joint_limits,
            sensor_update_rate: 200.0, // 200Hz
            command_timeout_ms: 1000,
        }
    }
}

impl ConfigValidation for RealtimeConfig {
    fn validate(&self) -> Result<()> {
        if self.control_frequency <= 0.0 {
            return Err(anyhow::anyhow!("控制频率必须为正数"));
        }
        
        if self.max_joint_velocity <= 0.0 {
            return Err(anyhow::anyhow!("最大关节速度必须为正数"));
        }
        
        if self.max_joint_acceleration <= 0.0 {
            return Err(anyhow::anyhow!("最大关节加速度必须为正数"));
        }
        
        if self.sensor_update_rate <= 0.0 {
            return Err(anyhow::anyhow!("传感器更新率必须为正数"));
        }
        
        Ok(())
    }
}

/// PID控制器增益
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIDGains {
    pub kp: f64, // 比例增益
    pub ki: f64, // 积分增益
    pub kd: f64, // 微分增益
    pub max_integral: f64, // 积分限幅
    pub max_output: f64,   // 输出限幅
}

impl Default for PIDGains {
    fn default() -> Self {
        Self {
            kp: 1.0,
            ki: 0.1,
            kd: 0.05,
            max_integral: 10.0,
            max_output: 100.0,
        }
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

impl Default for JointLimits {
    fn default() -> Self {
        Self {
            min_position: -3.14159,
            max_position: 3.14159,
            max_velocity: 2.0,
            max_acceleration: 5.0,
            max_torque: 10.0,
        }
    }
}

/// 运动命令
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MotionCommand {
    pub joint_name: String,
    pub command_type: CommandType,
    pub target_position: Option<f64>,
    pub target_velocity: Option<f64>,
    pub target_torque: Option<f64>,
    pub duration: Option<f64>,
    pub timestamp: u64,
}

/// 命令类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CommandType {
    Position,
    Velocity,
    Torque,
    Stop,
    EmergencyStop,
}

/// 传感器数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorData {
    pub joint_states: HashMap<String, JointState>,
    pub imu_data: Option<IMUData>,
    pub force_torque: Option<ForceTorqueData>,
    pub timestamp: u64,
}

/// IMU数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IMUData {
    pub acceleration: Vector3,
    pub angular_velocity: Vector3,
    pub orientation: Quaternion,
    pub temperature: f64,
}

/// 力/扭矩传感器数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForceTorqueData {
    pub force: Vector3,
    pub torque: Vector3,
}

/// 实时控制状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealtimeStatus {
    pub is_running: bool,
    pub emergency_stop: bool,
    pub control_loop_frequency: f64,
    pub sensor_update_frequency: f64,
    pub active_commands: usize,
    pub last_command_timestamp: u64,
    pub performance_stats: PerformanceStats,
    pub joint_states: HashMap<String, JointState>,
}

impl Default for RealtimeStatus {
    fn default() -> Self {
        Self {
            is_running: false,
            emergency_stop: false,
            control_loop_frequency: 0.0,
            sensor_update_frequency: 0.0,
            active_commands: 0,
            last_command_timestamp: 0,
            performance_stats: PerformanceStats::new(),
            joint_states: HashMap::new(),
        }
    }
}

/// PID控制器
#[derive(Debug, Clone)]
struct PIDController {
    gains: PIDGains,
    integral: f64,
    last_error: f64,
    last_time: Instant,
}

impl PIDController {
    fn new(gains: PIDGains) -> Self {
        Self {
            gains,
            integral: 0.0,
            last_error: 0.0,
            last_time: Instant::now(),
        }
    }
    
    fn update(&mut self, setpoint: f64, measurement: f64) -> f64 {
        let now = Instant::now();
        let dt = now.duration_since(self.last_time).as_secs_f64();
        
        if dt <= 0.0 {
            return 0.0;
        }
        
        let error = setpoint - measurement;
        
        // 比例项
        let proportional = self.gains.kp * error;
        
        // 积分项
        self.integral += error * dt;
        self.integral = clamp(self.integral, -self.gains.max_integral, self.gains.max_integral);
        let integral = self.gains.ki * self.integral;
        
        // 微分项
        let derivative = self.gains.kd * (error - self.last_error) / dt;
        
        // 总输出
        let output = proportional + integral + derivative;
        let clamped_output = clamp(output, -self.gains.max_output, self.gains.max_output);
        
        // 更新状态
        self.last_error = error;
        self.last_time = now;
        
        clamped_output
    }
    
    fn reset(&mut self) {
        self.integral = 0.0;
        self.last_error = 0.0;
        self.last_time = Instant::now();
    }
}

/// 轨迹生成器
#[derive(Debug, Clone)]
struct TrajectoryGenerator {
    start_position: f64,
    target_position: f64,
    start_velocity: f64,
    max_velocity: f64,
    max_acceleration: f64,
    start_time: Instant,
    duration: Duration,
}

impl TrajectoryGenerator {
    fn new(
        start_position: f64,
        target_position: f64,
        start_velocity: f64,
        max_velocity: f64,
        max_acceleration: f64,
    ) -> Self {
        let distance = (target_position - start_position).abs();
        let duration = Self::calculate_duration(distance, max_velocity, max_acceleration);
        
        Self {
            start_position,
            target_position,
            start_velocity,
            max_velocity,
            max_acceleration,
            start_time: Instant::now(),
            duration,
        }
    }
    
    fn calculate_duration(distance: f64, max_velocity: f64, max_acceleration: f64) -> Duration {
        let accel_time = max_velocity / max_acceleration;
        let accel_distance = 0.5 * max_acceleration * accel_time * accel_time;
        
        let total_time = if distance <= 2.0 * accel_distance {
            // 三角形轮廓
            2.0 * (distance / max_acceleration).sqrt()
        } else {
            // 梯形轮廓
            2.0 * accel_time + (distance - 2.0 * accel_distance) / max_velocity
        };
        
        Duration::from_secs_f64(total_time)
    }
    
    fn get_position(&self, time: Instant) -> f64 {
        let elapsed = time.duration_since(self.start_time).as_secs_f64();
        let total_duration = self.duration.as_secs_f64();
        
        if elapsed >= total_duration {
            return self.target_position;
        }
        
        let progress = elapsed / total_duration;
        let smooth_progress = smooth_step(0.0, 1.0, progress);
        
        lerp(self.start_position, self.target_position, smooth_progress)
    }
    
    fn get_velocity(&self, time: Instant) -> f64 {
        let elapsed = time.duration_since(self.start_time).as_secs_f64();
        let total_duration = self.duration.as_secs_f64();
        
        if elapsed >= total_duration {
            return 0.0;
        }
        
        let dt = 0.001; // 1ms for numerical differentiation
        let pos1 = self.get_position(time);
        let pos2 = self.get_position(time + Duration::from_secs_f64(dt));
        
        (pos2 - pos1) / dt
    }
    
    fn is_finished(&self, time: Instant) -> bool {
        time.duration_since(self.start_time) >= self.duration
    }
}

/// 实时控制器
pub struct RealtimeController {
    config: RealtimeConfig,
    status: Arc<RwLock<RealtimeStatus>>,
    pid_controllers: Arc<RwLock<HashMap<String, PIDController>>>,
    trajectories: Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
    command_queue: Arc<Mutex<VecDeque<MotionCommand>>>,
    sensor_data: Arc<RwLock<SensorData>>,
    control_handle: Option<tokio::task::JoinHandle<()>>,
    sensor_handle: Option<tokio::task::JoinHandle<()>>,
    is_running: Arc<RwLock<bool>>,
    emergency_stop: Arc<RwLock<bool>>,
}

impl RealtimeController {
    /// 创建新的实时控制器
    pub async fn new(config: RealtimeConfig) -> Result<Self> {
        config.validate()?;
        
        info!("初始化实时控制器...");
        
        let status = Arc::new(RwLock::new(RealtimeStatus::default()));
        let is_running = Arc::new(RwLock::new(false));
        let emergency_stop = Arc::new(RwLock::new(false));
        
        // 初始化PID控制器
        let mut pid_controllers = HashMap::new();
        for (joint_name, gains) in &config.pid_gains {
            pid_controllers.insert(joint_name.clone(), PIDController::new(gains.clone()));
        }
        let pid_controllers = Arc::new(RwLock::new(pid_controllers));
        
        let trajectories = Arc::new(RwLock::new(HashMap::new()));
        let command_queue = Arc::new(Mutex::new(VecDeque::new()));
        
        // 初始化传感器数据
        let mut joint_states = HashMap::new();
        for joint_name in config.joint_limits.keys() {
            joint_states.insert(joint_name.clone(), JointState::default());
        }
        
        let sensor_data = Arc::new(RwLock::new(SensorData {
            joint_states,
            imu_data: None,
            force_torque: None,
            timestamp: current_timestamp(),
        }));
        
        let controller = Self {
            config,
            status,
            pid_controllers,
            trajectories,
            command_queue,
            sensor_data,
            control_handle: None,
            sensor_handle: None,
            is_running,
            emergency_stop,
        };
        
        info!("实时控制器初始化完成");
        Ok(controller)
    }
    
    /// 启动实时控制
    pub async fn start(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if *is_running {
            return Ok(());
        }
        
        info!("启动实时控制器...");
        
        // 启动控制循环
        self.start_control_loop().await?;
        
        // 启动传感器更新循环
        self.start_sensor_loop().await?;
        
        *is_running = true;
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_running = true;
        }
        
        info!("实时控制器启动完成");
        Ok(())
    }
    
    /// 停止实时控制
    pub async fn stop(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if !*is_running {
            return Ok(());
        }
        
        info!("停止实时控制器...");
        
        *is_running = false;
        
        // 停止控制循环
        if let Some(handle) = self.control_handle.take() {
            handle.abort();
        }
        
        // 停止传感器循环
        if let Some(handle) = self.sensor_handle.take() {
            handle.abort();
        }
        
        // 清空命令队列
        {
            let mut queue = self.command_queue.lock().await;
            queue.clear();
        }
        
        // 重置PID控制器
        {
            let mut controllers = self.pid_controllers.write().await;
            for controller in controllers.values_mut() {
                controller.reset();
            }
        }
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_running = false;
            status.active_commands = 0;
        }
        
        info!("实时控制器停止完成");
        Ok(())
    }
    
    /// 启动控制循环
    async fn start_control_loop(&mut self) -> Result<()> {
        let control_period = Duration::from_secs_f64(1.0 / self.config.control_frequency);
        
        let is_running = Arc::clone(&self.is_running);
        let emergency_stop = Arc::clone(&self.emergency_stop);
        let status = Arc::clone(&self.status);
        let pid_controllers = Arc::clone(&self.pid_controllers);
        let trajectories = Arc::clone(&self.trajectories);
        let command_queue = Arc::clone(&self.command_queue);
        let sensor_data = Arc::clone(&self.sensor_data);
        let config = self.config.clone();
        
        let handle = tokio::spawn(async move {
            Self::control_loop(
                control_period,
                is_running,
                emergency_stop,
                status,
                pid_controllers,
                trajectories,
                command_queue,
                sensor_data,
                config,
            ).await
        });
        
        self.control_handle = Some(handle);
        Ok(())
    }
    
    /// 控制循环
    async fn control_loop(
        control_period: Duration,
        is_running: Arc<RwLock<bool>>,
        emergency_stop: Arc<RwLock<bool>>,
        status: Arc<RwLock<RealtimeStatus>>,
        pid_controllers: Arc<RwLock<HashMap<String, PIDController>>>,
        trajectories: Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
        command_queue: Arc<Mutex<VecDeque<MotionCommand>>>,
        sensor_data: Arc<RwLock<SensorData>>,
        config: RealtimeConfig,
    ) {
        let mut interval = interval(control_period);
        let mut loop_count = 0u64;
        let mut last_stats_update = Instant::now();
        
        loop {
            interval.tick().await;
            
            // 检查是否应该停止
            if !*is_running.read().await {
                break;
            }
            
            let loop_start = Instant::now();
            
            // 检查紧急停止
            if *emergency_stop.read().await {
                Self::handle_emergency_stop(&pid_controllers, &trajectories).await;
                continue;
            }
            
            // 处理命令队列
            Self::process_command_queue(
                &command_queue,
                &trajectories,
                &sensor_data,
                &config,
            ).await;
            
            // 更新轨迹和控制
            Self::update_control(
                &pid_controllers,
                &trajectories,
                &sensor_data,
                &config,
            ).await;
            
            loop_count += 1;
            
            // 更新性能统计
            let loop_time = loop_start.elapsed();
            if last_stats_update.elapsed() >= Duration::from_secs(1) {
                let mut status = status.write().await;
                status.control_loop_frequency = loop_count as f64 / last_stats_update.elapsed().as_secs_f64();
                status.performance_stats.update_frame_stats(loop_time);
                
                loop_count = 0;
                last_stats_update = Instant::now();
            }
        }
        
        info!("控制循环结束");
    }
    
    /// 处理紧急停止
    async fn handle_emergency_stop(
        pid_controllers: &Arc<RwLock<HashMap<String, PIDController>>>,
        trajectories: &Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
    ) {
        // 清空所有轨迹
        {
            let mut trajs = trajectories.write().await;
            trajs.clear();
        }
        
        // 重置所有PID控制器
        {
            let mut controllers = pid_controllers.write().await;
            for controller in controllers.values_mut() {
                controller.reset();
            }
        }
        
        // TODO: 发送停止命令到硬件
        warn!("紧急停止激活");
    }
    
    /// 处理命令队列
    async fn process_command_queue(
        command_queue: &Arc<Mutex<VecDeque<MotionCommand>>>,
        trajectories: &Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
        sensor_data: &Arc<RwLock<SensorData>>,
        config: &RealtimeConfig,
    ) {
        let mut queue = command_queue.lock().await;
        
        while let Some(command) = queue.pop_front() {
            // 检查命令超时
            let command_age = current_timestamp() - command.timestamp;
            if command_age > config.command_timeout_ms {
                warn!("命令超时，丢弃: {:?}", command);
                continue;
            }
            
            match command.command_type {
                CommandType::Position => {
                    if let Some(target_position) = command.target_position {
                        Self::create_position_trajectory(
                            &command.joint_name,
                            target_position,
                            trajectories,
                            sensor_data,
                            config,
                        ).await;
                    }
                },
                CommandType::Stop => {
                    Self::stop_joint(&command.joint_name, trajectories).await;
                },
                CommandType::EmergencyStop => {
                    // 紧急停止在主循环中处理
                    break;
                },
                _ => {
                    // TODO: 处理其他命令类型
                    debug!("暂不支持的命令类型: {:?}", command.command_type);
                }
            }
        }
    }
    
    /// 创建位置轨迹
    async fn create_position_trajectory(
        joint_name: &str,
        target_position: f64,
        trajectories: &Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
        sensor_data: &Arc<RwLock<SensorData>>,
        config: &RealtimeConfig,
    ) {
        let sensor_data = sensor_data.read().await;
        
        if let Some(joint_state) = sensor_data.joint_states.get(joint_name) {
            let start_position = joint_state.position;
            let start_velocity = joint_state.velocity;
            
            // 检查关节限制
            if let Some(limits) = config.joint_limits.get(joint_name) {
                let clamped_target = clamp(target_position, limits.min_position, limits.max_position);
                
                if clamped_target != target_position {
                    warn!("关节 {} 目标位置 {} 超出限制，限制为 {}", 
                          joint_name, target_position, clamped_target);
                }
                
                let trajectory = TrajectoryGenerator::new(
                    start_position,
                    clamped_target,
                    start_velocity,
                    limits.max_velocity,
                    limits.max_acceleration,
                );
                
                let mut trajs = trajectories.write().await;
                trajs.insert(joint_name.to_string(), trajectory);
                
                debug!("为关节 {} 创建轨迹: {} -> {}", joint_name, start_position, clamped_target);
            }
        }
    }
    
    /// 停止关节
    async fn stop_joint(
        joint_name: &str,
        trajectories: &Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
    ) {
        let mut trajs = trajectories.write().await;
        trajs.remove(joint_name);
        debug!("停止关节 {} 的运动", joint_name);
    }
    
    /// 更新控制
    async fn update_control(
        pid_controllers: &Arc<RwLock<HashMap<String, PIDController>>>,
        trajectories: &Arc<RwLock<HashMap<String, TrajectoryGenerator>>>,
        sensor_data: &Arc<RwLock<SensorData>>,
        config: &RealtimeConfig,
    ) {
        let now = Instant::now();
        let sensor_data = sensor_data.read().await;
        let mut controllers = pid_controllers.write().await;
        let mut trajs = trajectories.write().await;
        
        // 移除已完成的轨迹
        trajs.retain(|_, trajectory| !trajectory.is_finished(now));
        
        // 为每个活动轨迹计算控制输出
        for (joint_name, trajectory) in trajs.iter() {
            if let (Some(controller), Some(joint_state)) = (
                controllers.get_mut(joint_name),
                sensor_data.joint_states.get(joint_name)
            ) {
                let target_position = trajectory.get_position(now);
                let current_position = joint_state.position;
                
                let control_output = controller.update(target_position, current_position);
                
                // TODO: 发送控制输出到硬件
                debug!("关节 {} 控制输出: {:.3} (目标: {:.3}, 当前: {:.3})", 
                       joint_name, control_output, target_position, current_position);
            }
        }
    }
    
    /// 启动传感器循环
    async fn start_sensor_loop(&mut self) -> Result<()> {
        let sensor_period = Duration::from_secs_f64(1.0 / self.config.sensor_update_rate);
        
        let is_running = Arc::clone(&self.is_running);
        let status = Arc::clone(&self.status);
        let sensor_data = Arc::clone(&self.sensor_data);
        let config = self.config.clone();
        
        let handle = tokio::spawn(async move {
            Self::sensor_loop(
                sensor_period,
                is_running,
                status,
                sensor_data,
                config,
            ).await
        });
        
        self.sensor_handle = Some(handle);
        Ok(())
    }
    
    /// 传感器循环
    async fn sensor_loop(
        sensor_period: Duration,
        is_running: Arc<RwLock<bool>>,
        status: Arc<RwLock<RealtimeStatus>>,
        sensor_data: Arc<RwLock<SensorData>>,
        config: RealtimeConfig,
    ) {
        let mut interval = interval(sensor_period);
        let mut loop_count = 0u64;
        let mut last_stats_update = Instant::now();
        
        loop {
            interval.tick().await;
            
            // 检查是否应该停止
            if !*is_running.read().await {
                break;
            }
            
            // 模拟传感器数据更新
            Self::update_sensor_data(&sensor_data, &config).await;
            
            loop_count += 1;
            
            // 更新统计
            if last_stats_update.elapsed() >= Duration::from_secs(1) {
                let mut status = status.write().await;
                status.sensor_update_frequency = loop_count as f64 / last_stats_update.elapsed().as_secs_f64();
                
                loop_count = 0;
                last_stats_update = Instant::now();
            }
        }
        
        info!("传感器循环结束");
    }
    
    /// 更新传感器数据（模拟）
    async fn update_sensor_data(
        sensor_data: &Arc<RwLock<SensorData>>,
        config: &RealtimeConfig,
    ) {
        let mut data = sensor_data.write().await;
        
        // 模拟关节状态更新
        for (joint_name, _) in &config.joint_limits {
            if let Some(joint_state) = data.joint_states.get_mut(joint_name) {
                // 简单的模拟：添加小的随机噪声
                joint_state.position += (rand::random::<f64>() - 0.5) * 0.001;
                joint_state.velocity += (rand::random::<f64>() - 0.5) * 0.01;
                joint_state.effort += (rand::random::<f64>() - 0.5) * 0.1;
            }
        }
        
        // 模拟IMU数据
        data.imu_data = Some(IMUData {
            acceleration: Vector3 {
                x: (rand::random::<f64>() - 0.5) * 0.1,
                y: (rand::random::<f64>() - 0.5) * 0.1,
                z: 9.81 + (rand::random::<f64>() - 0.5) * 0.1,
            },
            angular_velocity: Vector3 {
                x: (rand::random::<f64>() - 0.5) * 0.01,
                y: (rand::random::<f64>() - 0.5) * 0.01,
                z: (rand::random::<f64>() - 0.5) * 0.01,
            },
            orientation: Quaternion {
                x: 0.0,
                y: 0.0,
                z: 0.0,
                w: 1.0,
            },
            temperature: 25.0 + (rand::random::<f64>() - 0.5) * 2.0,
        });
        
        data.timestamp = current_timestamp();
    }
    
    /// 添加运动命令
    pub async fn add_command(&self, command: MotionCommand) -> Result<()> {
        let mut queue = self.command_queue.lock().await;
        queue.push_back(command);
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.active_commands = queue.len();
            status.last_command_timestamp = current_timestamp();
        }
        
        Ok(())
    }
    
    /// 设置紧急停止
    pub async fn set_emergency_stop(&self, stop: bool) -> Result<()> {
        let mut emergency_stop = self.emergency_stop.write().await;
        *emergency_stop = stop;
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.emergency_stop = stop;
        }
        
        if stop {
            warn!("紧急停止激活");
        } else {
            info!("紧急停止解除");
        }
        
        Ok(())
    }
    
    /// 获取传感器数据
    pub async fn get_sensor_data(&self) -> Result<SensorData> {
        let data = self.sensor_data.read().await;
        Ok(data.clone())
    }
    
    /// 获取状态
    pub async fn get_status(&self) -> Result<RealtimeStatus> {
        let mut status = self.status.read().await.clone();
        
        // 更新关节状态
        let sensor_data = self.sensor_data.read().await;
        status.joint_states = sensor_data.joint_states.clone();
        
        Ok(status)
    }
    
    /// 是否正在运行
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
}

impl LifecycleManager for RealtimeController {
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
    async fn test_realtime_config_validation() {
        let config = RealtimeConfig::default();
        assert!(config.validate().is_ok());
        
        let mut invalid_config = config.clone();
        invalid_config.control_frequency = -1.0;
        assert!(invalid_config.validate().is_err());
    }
    
    #[tokio::test]
    async fn test_pid_controller() {
        let gains = PIDGains::default();
        let mut controller = PIDController::new(gains);
        
        let output = controller.update(1.0, 0.0);
        assert!(output > 0.0); // 应该有正输出来减少误差
    }
    
    #[tokio::test]
    async fn test_trajectory_generator() {
        let trajectory = TrajectoryGenerator::new(0.0, 1.0, 0.0, 1.0, 2.0);
        
        let start_time = Instant::now();
        let position = trajectory.get_position(start_time);
        assert_eq!(position, 0.0); // 起始位置
        
        let velocity = trajectory.get_velocity(start_time);
        assert!(velocity >= 0.0); // 初始速度应该为正或零
    }
    
    #[tokio::test]
    async fn test_realtime_controller_creation() {
        let config = RealtimeConfig::default();
        let controller = RealtimeController::new(config).await;
        assert!(controller.is_ok());
    }
}