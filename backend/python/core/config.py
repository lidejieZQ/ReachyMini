#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini 配置管理模块

提供应用程序的配置管理功能，包括：
- 环境变量配置
- 数据库配置
- Redis配置
- AI服务配置
- 视频流配置
- 机器人控制配置
- 安全配置
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    
    # SQLite配置
    SQLITE_URL: str = Field(
        default="sqlite:///./reachy_mini.db",
        description="SQLite数据库URL"
    )
    
    # PostgreSQL配置（可选）
    POSTGRES_HOST: Optional[str] = Field(default=None, description="PostgreSQL主机")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL端口")
    POSTGRES_USER: Optional[str] = Field(default=None, description="PostgreSQL用户名")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="PostgreSQL密码")
    POSTGRES_DB: Optional[str] = Field(default=None, description="PostgreSQL数据库名")
    
    # 连接池配置
    DB_POOL_SIZE: int = Field(default=10, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=20, description="数据库连接池最大溢出")
    DB_POOL_TIMEOUT: int = Field(default=30, description="数据库连接超时时间")
    
    # 其他配置
    DB_ECHO: bool = Field(default=False, description="是否打印SQL语句")
    DB_ECHO_POOL: bool = Field(default=False, description="是否打印连接池信息")
    
    @property
    def database_url(self) -> str:
        """获取数据库URL"""
        if all([self.POSTGRES_HOST, self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self.SQLITE_URL
    
    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    """Redis配置"""
    
    REDIS_HOST: str = Field(default="localhost", description="Redis主机")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis密码")
    REDIS_DB: int = Field(default=0, description="Redis数据库索引")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, description="Redis最大连接数")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, description="Redis套接字超时")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, description="Redis连接超时")
    REDIS_RETRY_ON_TIMEOUT: bool = Field(default=True, description="超时时是否重试")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30, description="健康检查间隔")
    
    @property
    def redis_url(self) -> str:
        """获取Redis URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")


class AISettings(BaseSettings):
    """AI服务配置"""
    
    # 模型配置
    AI_MODEL_PATH: str = Field(default="./models", description="AI模型路径")
    AI_DEVICE: str = Field(default="cpu", description="AI推理设备 (cpu, cuda, mps)")
    AI_BATCH_SIZE: int = Field(default=1, description="AI推理批次大小")
    AI_MAX_WORKERS: int = Field(default=4, description="AI工作线程数")
    
    # 对象检测配置
    OBJECT_DETECTION_MODEL: str = Field(
        default="yolov8n.pt",
        description="对象检测模型文件"
    )
    OBJECT_DETECTION_CONFIDENCE: float = Field(
        default=0.5,
        description="对象检测置信度阈值"
    )
    OBJECT_DETECTION_IOU: float = Field(
        default=0.45,
        description="对象检测IoU阈值"
    )
    
    # 人脸检测配置
    FACE_DETECTION_MODEL: str = Field(
        default="retinaface",
        description="人脸检测模型"
    )
    FACE_DETECTION_CONFIDENCE: float = Field(
        default=0.8,
        description="人脸检测置信度阈值"
    )
    
    # 姿态估计配置
    POSE_ESTIMATION_MODEL: str = Field(
        default="yolov8n-pose.pt",
        description="姿态估计模型文件"
    )
    POSE_ESTIMATION_CONFIDENCE: float = Field(
        default=0.3,
        description="姿态估计置信度阈值"
    )
    
    # 场景分析配置
    SCENE_ANALYSIS_MODEL: str = Field(
        default="resnet50",
        description="场景分析模型"
    )
    
    # 缓存配置
    AI_CACHE_SIZE: int = Field(default=100, description="AI结果缓存大小")
    AI_CACHE_TTL: int = Field(default=300, description="AI结果缓存TTL（秒）")
    
    @validator('AI_DEVICE')
    def validate_device(cls, v):
        allowed_devices = ['cpu', 'cuda', 'mps', 'auto']
        if v not in allowed_devices:
            raise ValueError(f'AI_DEVICE must be one of {allowed_devices}')
        return v
    
    model_config = SettingsConfigDict(env_prefix="AI_")


class StreamSettings(BaseSettings):
    """视频流配置"""
    
    # 摄像头配置
    CAMERA_INDEX: int = Field(default=0, description="摄像头索引")
    CAMERA_WIDTH: int = Field(default=640, description="摄像头宽度")
    CAMERA_HEIGHT: int = Field(default=480, description="摄像头高度")
    CAMERA_FPS: int = Field(default=30, description="摄像头帧率")
    CAMERA_BUFFER_SIZE: int = Field(default=1, description="摄像头缓冲区大小")
    
    # 编码配置
    VIDEO_CODEC: str = Field(default="h264", description="视频编码格式")
    VIDEO_BITRATE: int = Field(default=1000000, description="视频比特率")
    VIDEO_QUALITY: int = Field(default=23, description="视频质量 (0-51)")
    VIDEO_PRESET: str = Field(default="medium", description="编码预设")
    
    # 流配置
    STREAM_BUFFER_SIZE: int = Field(default=10, description="流缓冲区大小")
    STREAM_MAX_CLIENTS: int = Field(default=10, description="最大客户端数")
    STREAM_TIMEOUT: int = Field(default=30, description="流超时时间")
    
    # WebRTC配置
    WEBRTC_STUN_SERVER: str = Field(
        default="stun:stun.l.google.com:19302",
        description="STUN服务器"
    )
    WEBRTC_TURN_SERVER: Optional[str] = Field(default=None, description="TURN服务器")
    WEBRTC_TURN_USERNAME: Optional[str] = Field(default=None, description="TURN用户名")
    WEBRTC_TURN_PASSWORD: Optional[str] = Field(default=None, description="TURN密码")
    
    @validator('VIDEO_QUALITY')
    def validate_video_quality(cls, v):
        if not 0 <= v <= 51:
            raise ValueError('VIDEO_QUALITY must be between 0 and 51')
        return v
    
    model_config = SettingsConfigDict(env_prefix="STREAM_")


class RobotSettings(BaseSettings):
    """机器人控制配置"""
    
    # 串口配置
    SERIAL_PORT: str = Field(default="/dev/ttyUSB0", description="串口设备")
    SERIAL_BAUDRATE: int = Field(default=115200, description="串口波特率")
    SERIAL_TIMEOUT: float = Field(default=1.0, description="串口超时时间")
    
    # 控制配置
    CONTROL_FREQUENCY: float = Field(default=50.0, description="控制频率 (Hz)")
    MAX_JOINT_VELOCITY: float = Field(default=2.0, description="最大关节速度 (rad/s)")
    MAX_JOINT_ACCELERATION: float = Field(default=5.0, description="最大关节加速度 (rad/s²)")
    
    # 安全配置
    ENABLE_SAFETY_LIMITS: bool = Field(default=True, description="启用安全限制")
    EMERGENCY_STOP_TIMEOUT: float = Field(default=0.1, description="紧急停止超时时间")
    WATCHDOG_TIMEOUT: float = Field(default=1.0, description="看门狗超时时间")
    
    # 关节限制
    JOINT_LIMITS: Dict[str, Dict[str, float]] = Field(
        default={
            "joint_0": {"min": -3.14, "max": 3.14},
            "joint_1": {"min": -1.57, "max": 1.57},
            "joint_2": {"min": -3.14, "max": 3.14},
            "joint_3": {"min": -1.57, "max": 1.57},
            "joint_4": {"min": -3.14, "max": 3.14},
            "joint_5": {"min": -1.57, "max": 1.57},
        },
        description="关节限制"
    )
    
    # PID参数
    PID_GAINS: Dict[str, Dict[str, float]] = Field(
        default={
            "joint_0": {"kp": 10.0, "ki": 0.1, "kd": 0.5},
            "joint_1": {"kp": 8.0, "ki": 0.1, "kd": 0.4},
            "joint_2": {"kp": 6.0, "ki": 0.1, "kd": 0.3},
            "joint_3": {"kp": 4.0, "ki": 0.1, "kd": 0.2},
            "joint_4": {"kp": 3.0, "ki": 0.1, "kd": 0.15},
            "joint_5": {"kp": 2.0, "ki": 0.1, "kd": 0.1},
        },
        description="PID控制参数"
    )
    
    model_config = SettingsConfigDict(env_prefix="ROBOT_")


class SecuritySettings(BaseSettings):
    """安全配置"""
    
    # JWT配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="JWT密钥"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="访问令牌过期时间")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="刷新令牌过期天数")
    
    # API密钥
    API_KEYS: List[str] = Field(default=[], description="API密钥列表")
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="允许的源"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法"
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=["*"],
        description="允许的HTTP头"
    )
    
    # 限流配置
    ENABLE_RATE_LIMITING: bool = Field(default=True, description="启用限流")
    RATE_LIMIT_CALLS: int = Field(default=100, description="限流调用次数")
    RATE_LIMIT_PERIOD: int = Field(default=60, description="限流时间窗口")
    
    # SSL配置
    SSL_CERT_FILE: Optional[str] = Field(default=None, description="SSL证书文件")
    SSL_KEY_FILE: Optional[str] = Field(default=None, description="SSL私钥文件")
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class VisionSettings(BaseSettings):
    """视觉配置"""
    
    CAMERA_INDEX: int = Field(default=0, description="摄像头索引")
    FRAME_WIDTH: int = Field(default=640, description="帧宽度")
    FRAME_HEIGHT: int = Field(default=480, description="帧高度")
    FPS: float = Field(default=30.0, description="帧率")
    BUFFER_SIZE: int = Field(default=5, description="缓冲区大小")
    ENABLE_FACE_DETECTION: bool = Field(default=True, description="启用人脸检测")
    ENABLE_OBJECT_DETECTION: bool = Field(default=True, description="启用物体检测")
    ENABLE_FEATURE_DETECTION: bool = Field(default=False, description="启用特征检测")
    FACE_CASCADE_PATH: str = Field(default="haarcascade_frontalface_default.xml", description="人脸级联分类器路径")
    PROCESSING_THREADS: int = Field(default=2, description="处理线程数")
    
    model_config = SettingsConfigDict(env_prefix="VISION_")


class RealtimeSettings(BaseSettings):
    """实时控制配置"""
    
    CONTROL_FREQUENCY: float = Field(default=100.0, description="控制频率")
    MAX_JOINT_VELOCITY: float = Field(default=2.0, description="最大关节速度")
    MAX_JOINT_ACCELERATION: float = Field(default=5.0, description="最大关节加速度")
    POSITION_TOLERANCE: float = Field(default=0.01, description="位置容差")
    VELOCITY_TOLERANCE: float = Field(default=0.1, description="速度容差")
    ENABLE_SAFETY_LIMITS: bool = Field(default=True, description="启用安全限制")
    EMERGENCY_STOP_ENABLED: bool = Field(default=True, description="启用紧急停止")
    SENSOR_UPDATE_RATE: float = Field(default=200.0, description="传感器更新率")
    COMMAND_TIMEOUT_MS: int = Field(default=1000, description="命令超时时间(毫秒)")
    PID_GAINS: Dict[str, Dict[str, float]] = Field(
        default={
            "joint_0": {"kp": 10.0, "ki": 0.1, "kd": 0.5},
            "joint_1": {"kp": 8.0, "ki": 0.1, "kd": 0.4},
            "joint_2": {"kp": 6.0, "ki": 0.1, "kd": 0.3},
        },
        description="PID增益参数"
    )
    JOINT_LIMITS: Dict[str, Dict[str, float]] = Field(
        default={
            "joint_0": {"min": -3.14, "max": 3.14},
            "joint_1": {"min": -1.57, "max": 1.57},
            "joint_2": {"min": -3.14, "max": 3.14},
        },
        description="关节限制"
    )
    
    model_config = SettingsConfigDict(env_prefix="REALTIME_")


class HardwareSettings(BaseSettings):
    """硬件配置"""
    
    SERIAL_PORT: str = Field(default="/dev/ttyUSB0", description="串口端口")
    SERIAL_BAUDRATE: int = Field(default=115200, description="串口波特率")
    SERIAL_TIMEOUT: float = Field(default=1.0, description="串口超时")
    ENABLE_HARDWARE: bool = Field(default=False, description="启用硬件")
    HARDWARE_TYPE: str = Field(default="simulation", description="硬件类型")
    DEVICE_ID: str = Field(default="reachy_mini_001", description="设备ID")
    CALIBRATION_FILE: str = Field(default="calibration.json", description="校准文件")
    SENSOR_POLLING_RATE: float = Field(default=100.0, description="传感器轮询率")
    ACTUATOR_UPDATE_RATE: float = Field(default=50.0, description="执行器更新率")
    
    model_config = SettingsConfigDict(env_prefix="HARDWARE_")


class LoggingSettings(BaseSettings):
    """日志配置"""
    
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    LOG_FILE: Optional[str] = Field(default=None, description="日志文件路径")
    LOG_MAX_SIZE: int = Field(default=10485760, description="日志文件最大大小 (10MB)")
    LOG_BACKUP_COUNT: int = Field(default=5, description="日志文件备份数量")
    LOG_JSON: bool = Field(default=False, description="使用JSON格式日志")
    
    # 特定模块日志级别
    LOG_LEVELS: Dict[str, str] = Field(
        default={
            "uvicorn": "INFO",
            "fastapi": "INFO",
            "sqlalchemy": "WARNING",
            "redis": "WARNING",
        },
        description="特定模块日志级别"
    )
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'LOG_LEVEL must be one of {allowed_levels}')
        return v.upper()
    
    model_config = SettingsConfigDict(env_prefix="LOG_")


class Settings(BaseSettings):
    """主配置类"""
    
    # 基本配置
    APP_NAME: str = Field(default="Reachy Mini Control System", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="调试模式")
    TESTING: bool = Field(default=False, description="测试模式")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    WORKERS: int = Field(default=1, description="工作进程数")
    AUTO_RELOAD: bool = Field(default=False, description="自动重载")
    
    # 功能开关
    ENABLE_DOCS: bool = Field(default=True, description="启用API文档")
    ENABLE_METRICS: bool = Field(default=True, description="启用指标监控")
    ENABLE_REQUEST_LOGGING: bool = Field(default=True, description="启用请求日志")
    ENABLE_ACCESS_LOG: bool = Field(default=True, description="启用访问日志")
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    ai: AISettings = AISettings()
    stream: StreamSettings = StreamSettings()
    robot: RobotSettings = RobotSettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    vision: VisionSettings = VisionSettings()
    realtime: RealtimeSettings = RealtimeSettings()
    hardware: HardwareSettings = HardwareSettings()
    
    # 环境配置
    ENVIRONMENT: str = Field(default="development", description="运行环境")
    
    # 数据目录
    DATA_DIR: str = Field(default="./data", description="数据目录")
    LOGS_DIR: str = Field(default="./logs", description="日志目录")
    MODELS_DIR: str = Field(default="./models", description="模型目录")
    TEMP_DIR: str = Field(default="./temp", description="临时目录")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.DATA_DIR,
            self.LOGS_DIR,
            self.MODELS_DIR,
            self.TEMP_DIR,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'testing', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'ENVIRONMENT must be one of {allowed_envs}')
        return v
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT == "testing" or self.TESTING
    
    @property
    def api_host(self) -> str:
        """API主机地址"""
        return self.HOST
    
    @property
    def api_port(self) -> int:
        """API端口"""
        return self.PORT
    
    @property
    def debug(self) -> bool:
        """调试模式"""
        return self.DEBUG
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()


# 兼容性别名
get_config = get_settings


# 全局配置实例
settings = get_settings()


# 配置验证函数
def validate_config() -> bool:
    """验证配置是否正确"""
    try:
        config = get_settings()
        
        # 验证必要的目录
        required_dirs = [config.DATA_DIR, config.LOGS_DIR]
        for directory in required_dirs:
            if not Path(directory).exists():
                raise ValueError(f"Required directory does not exist: {directory}")
        
        # 验证端口范围
        if not 1 <= config.PORT <= 65535:
            raise ValueError(f"Invalid port number: {config.PORT}")
        
        # 验证Redis配置
        if not 1 <= config.redis.REDIS_PORT <= 65535:
            raise ValueError(f"Invalid Redis port: {config.redis.REDIS_PORT}")
        
        # 验证AI设备配置
        if config.ai.AI_DEVICE not in ['cpu', 'cuda', 'mps', 'auto']:
            raise ValueError(f"Invalid AI device: {config.ai.AI_DEVICE}")
        
        return True
        
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # 配置测试
    if validate_config():
        print("✅ Configuration is valid")
        config = get_settings()
        print(f"App: {config.APP_NAME} v{config.APP_VERSION}")
        print(f"Environment: {config.ENVIRONMENT}")
        print(f"Debug: {config.DEBUG}")
        print(f"Host: {config.HOST}:{config.PORT}")
        print(f"Database: {config.database.database_url}")
        print(f"Redis: {config.redis.redis_url}")
    else:
        print("❌ Configuration validation failed")
        exit(1)