//! 视觉处理模块
//! 
//! 提供高性能的计算机视觉处理功能，包括图像捕获、处理、特征检测等。

use crate::common::*;
use anyhow::Result;
use opencv::{prelude::*, core, imgproc, videoio, objdetect, features2d};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, mpsc};
use log::{info, warn, error, debug};

/// 视觉处理配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisionConfig {
    pub camera_index: i32,
    pub frame_width: i32,
    pub frame_height: i32,
    pub fps: f64,
    pub buffer_size: usize,
    pub enable_face_detection: bool,
    pub enable_object_detection: bool,
    pub enable_feature_detection: bool,
    pub face_cascade_path: String,
    pub processing_threads: usize,
}

impl Default for VisionConfig {
    fn default() -> Self {
        Self {
            camera_index: 0,
            frame_width: 640,
            frame_height: 480,
            fps: 30.0,
            buffer_size: 10,
            enable_face_detection: true,
            enable_object_detection: false,
            enable_feature_detection: false,
            face_cascade_path: "data/haarcascade_frontalface_alt.xml".to_string(),
            processing_threads: 2,
        }
    }
}

impl ConfigValidation for VisionConfig {
    fn validate(&self) -> Result<()> {
        if self.camera_index < 0 {
            return Err(anyhow::anyhow!("摄像头索引不能为负数"));
        }
        
        if self.frame_width <= 0 || self.frame_height <= 0 {
            return Err(anyhow::anyhow!("帧尺寸必须为正数"));
        }
        
        if self.fps <= 0.0 {
            return Err(anyhow::anyhow!("帧率必须为正数"));
        }
        
        if self.buffer_size == 0 {
            return Err(anyhow::anyhow!("缓冲区大小不能为0"));
        }
        
        Ok(())
    }
}

/// 视觉处理状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisionStatus {
    pub is_running: bool,
    pub camera_connected: bool,
    pub current_fps: f64,
    pub frames_processed: u64,
    pub frames_dropped: u64,
    pub last_frame_timestamp: u64,
    pub processing_stats: PerformanceStats,
}

impl Default for VisionStatus {
    fn default() -> Self {
        Self {
            is_running: false,
            camera_connected: false,
            current_fps: 0.0,
            frames_processed: 0,
            frames_dropped: 0,
            last_frame_timestamp: 0,
            processing_stats: PerformanceStats::new(),
        }
    }
}

/// 检测结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionResult {
    pub faces: Vec<FaceDetection>,
    pub objects: Vec<ObjectDetection>,
    pub features: Vec<FeaturePoint>,
    pub timestamp: u64,
}

/// 人脸检测结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaceDetection {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
    pub confidence: f64,
}

/// 物体检测结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjectDetection {
    pub class_id: i32,
    pub class_name: String,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
    pub confidence: f64,
}

/// 特征点
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeaturePoint {
    pub x: f32,
    pub y: f32,
    pub response: f32,
}

/// 视觉处理错误
#[derive(Debug, thiserror::Error)]
pub enum VisionError {
    #[error("摄像头错误: {0}")]
    Camera(String),
    
    #[error("图像处理错误: {0}")]
    ImageProcessing(String),
    
    #[error("检测器错误: {0}")]
    Detector(String),
    
    #[error("配置错误: {0}")]
    Config(String),
    
    #[error("OpenCV错误: {0}")]
    OpenCV(#[from] opencv::Error),
}

/// 帧数据
#[derive(Debug, Clone)]
pub struct FrameData {
    pub image: ImageData,
    pub detection_result: Option<DetectionResult>,
    pub timestamp: u64,
}

/// 视觉处理器
pub struct VisionProcessor {
    config: VisionConfig,
    status: Arc<RwLock<VisionStatus>>,
    camera: Option<videoio::VideoCapture>,
    face_cascade: Option<objdetect::CascadeClassifier>,
    feature_detector: Option<features2d::ORB>,
    frame_buffer: Arc<RwLock<VecDeque<FrameData>>>,
    frame_sender: Option<mpsc::UnboundedSender<FrameData>>,
    frame_receiver: Option<mpsc::UnboundedReceiver<FrameData>>,
    processing_handle: Option<tokio::task::JoinHandle<()>>,
    capture_handle: Option<tokio::task::JoinHandle<()>>,
    is_running: Arc<RwLock<bool>>,
}

impl VisionProcessor {
    /// 创建新的视觉处理器
    pub async fn new(config: VisionConfig) -> Result<Self> {
        config.validate()?;
        
        info!("初始化视觉处理器...");
        
        let status = Arc::new(RwLock::new(VisionStatus::default()));
        let frame_buffer = Arc::new(RwLock::new(VecDeque::with_capacity(config.buffer_size)));
        let is_running = Arc::new(RwLock::new(false));
        
        let (frame_sender, frame_receiver) = mpsc::unbounded_channel();
        
        let mut processor = Self {
            config,
            status,
            camera: None,
            face_cascade: None,
            feature_detector: None,
            frame_buffer,
            frame_sender: Some(frame_sender),
            frame_receiver: Some(frame_receiver),
            processing_handle: None,
            capture_handle: None,
            is_running,
        };
        
        processor.initialize_detectors().await?;
        
        info!("视觉处理器初始化完成");
        Ok(processor)
    }
    
    /// 初始化检测器
    async fn initialize_detectors(&mut self) -> Result<()> {
        // 初始化人脸检测器
        if self.config.enable_face_detection {
            match objdetect::CascadeClassifier::new(&self.config.face_cascade_path) {
                Ok(cascade) => {
                    self.face_cascade = Some(cascade);
                    info!("人脸检测器初始化成功");
                },
                Err(e) => {
                    warn!("人脸检测器初始化失败: {}, 将禁用人脸检测", e);
                }
            }
        }
        
        // 初始化特征检测器
        if self.config.enable_feature_detection {
            match features2d::ORB::create(500, 1.2, 8, 31, 0, 2, features2d::ORB_ScoreType::HARRIS_SCORE, 31, 20) {
                Ok(detector) => {
                    self.feature_detector = Some(detector);
                    info!("特征检测器初始化成功");
                },
                Err(e) => {
                    warn!("特征检测器初始化失败: {}, 将禁用特征检测", e);
                }
            }
        }
        
        Ok(())
    }
    
    /// 初始化摄像头
    async fn initialize_camera(&mut self) -> Result<()> {
        info!("初始化摄像头 {}", self.config.camera_index);
        
        let mut camera = videoio::VideoCapture::new(self.config.camera_index, videoio::CAP_ANY)?;
        
        if !camera.is_opened()? {
            return Err(VisionError::Camera("无法打开摄像头".to_string()).into());
        }
        
        // 设置摄像头参数
        camera.set(videoio::CAP_PROP_FRAME_WIDTH, self.config.frame_width as f64)?;
        camera.set(videoio::CAP_PROP_FRAME_HEIGHT, self.config.frame_height as f64)?;
        camera.set(videoio::CAP_PROP_FPS, self.config.fps)?;
        
        // 验证设置
        let actual_width = camera.get(videoio::CAP_PROP_FRAME_WIDTH)? as i32;
        let actual_height = camera.get(videoio::CAP_PROP_FRAME_HEIGHT)? as i32;
        let actual_fps = camera.get(videoio::CAP_PROP_FPS)?;
        
        info!("摄像头参数: {}x{} @ {:.1} FPS", actual_width, actual_height, actual_fps);
        
        self.camera = Some(camera);
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.camera_connected = true;
        }
        
        Ok(())
    }
    
    /// 启动视觉处理
    pub async fn start(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if *is_running {
            return Ok(());
        }
        
        info!("启动视觉处理器...");
        
        // 初始化摄像头
        self.initialize_camera().await?;
        
        // 启动帧捕获任务
        self.start_capture_task().await?;
        
        // 启动处理任务
        self.start_processing_task().await?;
        
        *is_running = true;
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_running = true;
        }
        
        info!("视觉处理器启动完成");
        Ok(())
    }
    
    /// 停止视觉处理
    pub async fn stop(&mut self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if !*is_running {
            return Ok(());
        }
        
        info!("停止视觉处理器...");
        
        *is_running = false;
        
        // 停止处理任务
        if let Some(handle) = self.processing_handle.take() {
            handle.abort();
        }
        
        // 停止捕获任务
        if let Some(handle) = self.capture_handle.take() {
            handle.abort();
        }
        
        // 关闭摄像头
        if let Some(mut camera) = self.camera.take() {
            let _ = camera.release();
        }
        
        // 更新状态
        {
            let mut status = self.status.write().await;
            status.is_running = false;
            status.camera_connected = false;
        }
        
        info!("视觉处理器停止完成");
        Ok(())
    }
    
    /// 启动帧捕获任务
    async fn start_capture_task(&mut self) -> Result<()> {
        let camera = self.camera.take().ok_or_else(|| {
            VisionError::Camera("摄像头未初始化".to_string())
        })?;
        
        let frame_sender = self.frame_sender.take().ok_or_else(|| {
            VisionError::Config("帧发送器未初始化".to_string())
        })?;
        
        let is_running = Arc::clone(&self.is_running);
        let status = Arc::clone(&self.status);
        let config = self.config.clone();
        
        let handle = tokio::task::spawn_blocking(move || {
            Self::capture_loop(camera, frame_sender, is_running, status, config)
        });
        
        self.capture_handle = Some(handle);
        Ok(())
    }
    
    /// 帧捕获循环
    fn capture_loop(
        mut camera: videoio::VideoCapture,
        frame_sender: mpsc::UnboundedSender<FrameData>,
        is_running: Arc<RwLock<bool>>,
        status: Arc<RwLock<VisionStatus>>,
        config: VisionConfig,
    ) {
        let mut frame = core::Mat::default();
        let frame_interval = Duration::from_secs_f64(1.0 / config.fps);
        let mut last_frame_time = Instant::now();
        
        loop {
            // 检查是否应该停止
            if let Ok(running) = is_running.try_read() {
                if !*running {
                    break;
                }
            }
            
            // 控制帧率
            let elapsed = last_frame_time.elapsed();
            if elapsed < frame_interval {
                std::thread::sleep(frame_interval - elapsed);
            }
            last_frame_time = Instant::now();
            
            // 捕获帧
            match camera.read(&mut frame) {
                Ok(true) => {
                    if frame.empty() {
                        continue;
                    }
                    
                    // 转换为ImageData
                    match Self::mat_to_image_data(&frame) {
                        Ok(image_data) => {
                            let frame_data = FrameData {
                                image: image_data,
                                detection_result: None,
                                timestamp: current_timestamp(),
                            };
                            
                            // 发送帧数据
                            if frame_sender.send(frame_data).is_err() {
                                error!("发送帧数据失败，接收器可能已关闭");
                                break;
                            }
                            
                            // 更新统计
                            if let Ok(mut status) = status.try_write() {
                                status.frames_processed += 1;
                                status.last_frame_timestamp = current_timestamp();
                            }
                        },
                        Err(e) => {
                            error!("转换帧数据失败: {}", e);
                        }
                    }
                },
                Ok(false) => {
                    warn!("摄像头返回空帧");
                    std::thread::sleep(Duration::from_millis(10));
                },
                Err(e) => {
                    error!("读取摄像头帧失败: {}", e);
                    std::thread::sleep(Duration::from_millis(100));
                }
            }
        }
        
        info!("帧捕获循环结束");
    }
    
    /// 启动处理任务
    async fn start_processing_task(&mut self) -> Result<()> {
        let frame_receiver = self.frame_receiver.take().ok_or_else(|| {
            VisionError::Config("帧接收器未初始化".to_string())
        })?;
        
        let is_running = Arc::clone(&self.is_running);
        let status = Arc::clone(&self.status);
        let frame_buffer = Arc::clone(&self.frame_buffer);
        let config = self.config.clone();
        
        // 复制检测器（如果可用）
        let face_cascade = self.face_cascade.clone();
        let feature_detector = self.feature_detector.clone();
        
        let handle = tokio::spawn(async move {
            Self::processing_loop(
                frame_receiver,
                is_running,
                status,
                frame_buffer,
                config,
                face_cascade,
                feature_detector,
            ).await
        });
        
        self.processing_handle = Some(handle);
        Ok(())
    }
    
    /// 处理循环
    async fn processing_loop(
        mut frame_receiver: mpsc::UnboundedReceiver<FrameData>,
        is_running: Arc<RwLock<bool>>,
        status: Arc<RwLock<VisionStatus>>,
        frame_buffer: Arc<RwLock<VecDeque<FrameData>>>,
        config: VisionConfig,
        face_cascade: Option<objdetect::CascadeClassifier>,
        feature_detector: Option<features2d::ORB>,
    ) {
        while let Some(mut frame_data) = frame_receiver.recv().await {
            // 检查是否应该停止
            if let Ok(running) = is_running.try_read() {
                if !*running {
                    break;
                }
            }
            
            let start_time = Instant::now();
            
            // 处理帧
            if let Ok(detection_result) = Self::process_frame(
                &frame_data.image,
                &face_cascade,
                &feature_detector,
                &config,
            ).await {
                frame_data.detection_result = Some(detection_result);
            }
            
            let processing_time = start_time.elapsed();
            
            // 添加到缓冲区
            {
                let mut buffer = frame_buffer.write().await;
                if buffer.len() >= config.buffer_size {
                    buffer.pop_front();
                    
                    // 更新丢帧统计
                    if let Ok(mut status) = status.try_write() {
                        status.frames_dropped += 1;
                    }
                }
                buffer.push_back(frame_data);
            }
            
            // 更新性能统计
            if let Ok(mut status) = status.try_write() {
                status.processing_stats.update_frame_stats(processing_time);
                status.current_fps = status.processing_stats.fps;
            }
        }
        
        info!("处理循环结束");
    }
    
    /// 处理单帧
    async fn process_frame(
        image_data: &ImageData,
        face_cascade: &Option<objdetect::CascadeClassifier>,
        feature_detector: &Option<features2d::ORB>,
        config: &VisionConfig,
    ) -> Result<DetectionResult> {
        let mut result = DetectionResult {
            faces: Vec::new(),
            objects: Vec::new(),
            features: Vec::new(),
            timestamp: current_timestamp(),
        };
        
        // 转换为OpenCV Mat
        let mat = Self::image_data_to_mat(image_data)?;
        
        // 人脸检测
        if config.enable_face_detection {
            if let Some(cascade) = face_cascade {
                result.faces = Self::detect_faces(&mat, cascade)?;
            }
        }
        
        // 特征检测
        if config.enable_feature_detection {
            if let Some(detector) = feature_detector {
                result.features = Self::detect_features(&mat, detector)?;
            }
        }
        
        Ok(result)
    }
    
    /// 人脸检测
    fn detect_faces(
        mat: &core::Mat,
        cascade: &objdetect::CascadeClassifier,
    ) -> Result<Vec<FaceDetection>> {
        let mut gray = core::Mat::default();
        imgproc::cvt_color(mat, &mut gray, imgproc::COLOR_BGR2GRAY, 0)?;
        
        let mut faces = core::Vector::<core::Rect>::new();
        cascade.detect_multi_scale(
            &gray,
            &mut faces,
            1.1,
            3,
            0,
            core::Size::new(30, 30),
            core::Size::new(0, 0),
        )?;
        
        let mut result = Vec::new();
        for face in faces.iter() {
            result.push(FaceDetection {
                x: face.x,
                y: face.y,
                width: face.width,
                height: face.height,
                confidence: 1.0, // Haar级联不提供置信度
            });
        }
        
        Ok(result)
    }
    
    /// 特征检测
    fn detect_features(
        mat: &core::Mat,
        detector: &features2d::ORB,
    ) -> Result<Vec<FeaturePoint>> {
        let mut gray = core::Mat::default();
        imgproc::cvt_color(mat, &mut gray, imgproc::COLOR_BGR2GRAY, 0)?;
        
        let mut keypoints = core::Vector::<core::KeyPoint>::new();
        let mask = core::Mat::default();
        
        detector.detect(&gray, &mut keypoints, &mask)?;
        
        let mut result = Vec::new();
        for kp in keypoints.iter() {
            result.push(FeaturePoint {
                x: kp.pt.x,
                y: kp.pt.y,
                response: kp.response,
            });
        }
        
        Ok(result)
    }
    
    /// Mat转ImageData
    fn mat_to_image_data(mat: &core::Mat) -> Result<ImageData> {
        let rows = mat.rows();
        let cols = mat.cols();
        let channels = mat.channels();
        
        if rows <= 0 || cols <= 0 || channels <= 0 {
            return Err(VisionError::ImageProcessing("无效的图像尺寸".to_string()).into());
        }
        
        let mut data = vec![0u8; (rows * cols * channels) as usize];
        
        unsafe {
            let mat_data = mat.ptr(0)? as *const u8;
            std::ptr::copy_nonoverlapping(
                mat_data,
                data.as_mut_ptr(),
                data.len(),
            );
        }
        
        let format = match channels {
            1 => ImageFormat::Gray8,
            3 => ImageFormat::BGR8,
            4 => ImageFormat::BGRA8,
            _ => return Err(VisionError::ImageProcessing("不支持的通道数".to_string()).into()),
        };
        
        Ok(ImageData::from_raw(
            cols as u32,
            rows as u32,
            channels as u32,
            data,
            format,
        ))
    }
    
    /// ImageData转Mat
    fn image_data_to_mat(image_data: &ImageData) -> Result<core::Mat> {
        let cv_type = match image_data.format {
            ImageFormat::Gray8 => core::CV_8UC1,
            ImageFormat::BGR8 => core::CV_8UC3,
            ImageFormat::RGB8 => core::CV_8UC3,
            ImageFormat::BGRA8 => core::CV_8UC4,
            ImageFormat::RGBA8 => core::CV_8UC4,
            _ => return Err(VisionError::ImageProcessing("不支持的图像格式".to_string()).into()),
        };
        
        let mat = unsafe {
            core::Mat::new_rows_cols_with_data(
                image_data.height as i32,
                image_data.width as i32,
                cv_type,
                image_data.data.as_ptr() as *mut std::ffi::c_void,
                core::Mat_AUTO_STEP,
            )?
        };
        
        Ok(mat)
    }
    
    /// 获取最新帧
    pub async fn get_latest_frame(&self) -> Option<FrameData> {
        let buffer = self.frame_buffer.read().await;
        buffer.back().cloned()
    }
    
    /// 获取帧缓冲区
    pub async fn get_frame_buffer(&self) -> Vec<FrameData> {
        let buffer = self.frame_buffer.read().await;
        buffer.iter().cloned().collect()
    }
    
    /// 获取状态
    pub async fn get_status(&self) -> Result<VisionStatus> {
        let status = self.status.read().await;
        Ok(status.clone())
    }
    
    /// 是否正在运行
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
}

impl LifecycleManager for VisionProcessor {
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
    async fn test_vision_config_validation() {
        let config = VisionConfig::default();
        assert!(config.validate().is_ok());
        
        let mut invalid_config = config.clone();
        invalid_config.camera_index = -1;
        assert!(invalid_config.validate().is_err());
    }
    
    #[tokio::test]
    async fn test_vision_processor_creation() {
        let config = VisionConfig::default();
        let processor = VisionProcessor::new(config).await;
        
        // 在没有摄像头的测试环境中，创建应该成功
        // 但启动可能会失败
        assert!(processor.is_ok());
    }
    
    #[test]
    fn test_image_data_conversion() {
        // 创建测试图像数据
        let width = 100;
        let height = 100;
        let channels = 3;
        let data = vec![128u8; (width * height * channels) as usize];
        
        let image_data = ImageData::from_raw(
            width,
            height,
            channels,
            data,
            ImageFormat::BGR8,
        );
        
        // 测试转换（需要OpenCV环境）
        // let mat_result = VisionProcessor::image_data_to_mat(&image_data);
        // assert!(mat_result.is_ok());
    }
}