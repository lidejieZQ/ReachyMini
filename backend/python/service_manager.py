#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务管理器

负责管理Python后端的所有服务组件，包括FastAPI应用、数据库连接、
Rust绑定、WebSocket连接、任务调度等。
"""

import asyncio
import logging
import signal
import threading
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from core.config import get_config
from core.database import get_database_manager, get_migration_manager
from core.exceptions import register_exception_handlers
from rust_bindings import (
    get_rust_bindings_manager, cleanup_rust_bindings,
    VisionConfig, RealtimeConfig, HardwareConfig, AIConfig,
    is_rust_available
)

logger = logging.getLogger(__name__)


class ServiceManager:
    """服务管理器 - 统一管理所有系统服务组件
    
    负责协调和管理Reachy Mini系统的所有核心组件，包括：
    - 数据库连接管理
    - Rust模块绑定
    - FastAPI Web服务器
    - WebSocket实时通信
    - 后台任务调度器
    
    提供统一的生命周期管理，确保所有组件的正确启动、运行和关闭。
    """
    
    def __init__(self):
        """初始化服务管理器
        
        设置基本配置和状态跟踪变量
        """
        self.config = get_config()  # 获取全局配置
        self.app: Optional[FastAPI] = None  # FastAPI应用实例
        self.server: Optional[uvicorn.Server] = None  # Web服务器实例
        self.server_task: Optional[asyncio.Task] = None  # 服务器异步任务
        
        # 组件运行状态跟踪
        self._running = False  # 整体运行状态
        self._shutdown_event = asyncio.Event()  # 关闭事件信号
        self._components_status = {
            "database": False,      # 数据库连接状态
            "rust_bindings": False, # Rust模块绑定状态
            "api_server": False,    # API服务器状态
            "websocket": False,     # WebSocket服务状态
            "scheduler": False,     # 任务调度器状态
        }
        
        # 线程安全锁
        self._lock = threading.Lock()
        
        logger.info("服务管理器初始化完成")
    
    async def initialize(self) -> None:
        """初始化所有服务组件
        
        按照依赖关系顺序初始化各个组件：
        1. 数据库连接 - 基础数据存储
        2. Rust模块绑定 - 高性能计算模块
        3. FastAPI应用 - Web API服务
        4. WebSocket服务 - 实时通信
        5. 任务调度器 - 后台任务管理
        
        如果任何组件初始化失败，会自动清理已初始化的组件
        
        Raises:
            Exception: 当任何组件初始化失败时抛出异常
        """
        logger.info("开始初始化服务组件...")
        
        try:
            # 初始化数据库 - 必须首先建立数据连接
            await self._initialize_database()
            
            # 初始化Rust绑定 - 加载高性能计算模块
            await self._initialize_rust_bindings()
            
            # 初始化FastAPI应用 - 设置Web服务
            await self._initialize_api_server()
            
            # 初始化WebSocket - 建立实时通信能力
            await self._initialize_websocket()
            
            # 初始化任务调度器 - 启动后台任务管理
            await self._initialize_scheduler()
            
            logger.info("所有服务组件初始化完成")
            
        except Exception as e:
            logger.error(f"服务组件初始化失败: {e}")
            # 发生错误时自动清理已初始化的组件
            await self.cleanup()
            raise
    
    async def _initialize_database(self) -> None:
        """初始化数据库连接
        
        建立与数据库的连接并验证连接状态。
        数据库用于存储系统配置、用户数据、日志等信息。
        执行必要的数据库迁移以确保数据结构是最新的。
        
        Raises:
            RuntimeError: 当数据库连接失败时抛出异常
        """
        try:
            logger.info("初始化数据库...")
            
            # 获取数据库管理器实例
            db_manager = get_database_manager()
            
            # 执行数据库健康检查
            # 验证连接是否正常，数据库是否可访问
            health_status = db_manager.health_check()
            if health_status["status"] != "healthy":
                raise RuntimeError(f"数据库连接失败: {health_status.get('error', '未知错误')}")
            
            # 运行数据库迁移（在线程池中运行同步操作）
            # 确保数据库结构是最新版本
            migration_manager = get_migration_manager()
            await asyncio.to_thread(migration_manager.initialize)
            await asyncio.to_thread(migration_manager.upgrade)
            
            # 更新组件状态
            self._components_status["database"] = True
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _initialize_rust_bindings(self) -> None:
        """初始化Rust绑定"""
        try:
            logger.info("初始化Rust绑定...")
            
            if not is_rust_available():
                logger.warning("Rust模块不可用，跳过Rust绑定初始化")
                return
            
            # 获取Rust绑定管理器
            rust_manager = get_rust_bindings_manager()
            
            # 验证配置
            rust_config = {
                "vision": self.config.vision.__dict__,
                "realtime": self.config.realtime.__dict__,
                "hardware": self.config.hardware.__dict__,
                "ai": self.config.ai.__dict__,
            }
            
            if not rust_manager.validate_config(rust_config):
                raise RuntimeError("Rust配置验证失败")
            
            # 创建系统实例（但不启动）
            # 映射配置字段名称（从大写转换为小写）
            vision_dict = {
                'camera_index': self.config.vision.CAMERA_INDEX,
                'frame_width': self.config.vision.FRAME_WIDTH,
                'frame_height': self.config.vision.FRAME_HEIGHT,
                'fps': self.config.vision.FPS,
                'buffer_size': self.config.vision.BUFFER_SIZE,
                'enable_face_detection': self.config.vision.ENABLE_FACE_DETECTION,
                'enable_object_detection': self.config.vision.ENABLE_OBJECT_DETECTION,
                'enable_feature_detection': self.config.vision.ENABLE_FEATURE_DETECTION,
                'face_cascade_path': self.config.vision.FACE_CASCADE_PATH,
                'processing_threads': self.config.vision.PROCESSING_THREADS,
            }
            
            realtime_dict = {
                'control_frequency': self.config.realtime.CONTROL_FREQUENCY,
                'max_joint_velocity': self.config.realtime.MAX_JOINT_VELOCITY,
                'max_joint_acceleration': self.config.realtime.MAX_JOINT_ACCELERATION,
                'position_tolerance': self.config.realtime.POSITION_TOLERANCE,
                'velocity_tolerance': self.config.realtime.VELOCITY_TOLERANCE,
                'enable_safety_limits': self.config.realtime.ENABLE_SAFETY_LIMITS,
                'emergency_stop_enabled': self.config.realtime.EMERGENCY_STOP_ENABLED,
                'sensor_update_rate': self.config.realtime.SENSOR_UPDATE_RATE,
                'command_timeout_ms': self.config.realtime.COMMAND_TIMEOUT_MS,
                'pid_gains': self.config.realtime.PID_GAINS,
                'joint_limits': self.config.realtime.JOINT_LIMITS,
            }
            
            hardware_dict = {
                'serial_port': self.config.hardware.SERIAL_PORT,
                'serial_baudrate': self.config.hardware.SERIAL_BAUDRATE,
                'serial_timeout': self.config.hardware.SERIAL_TIMEOUT,
                'i2c_bus': 1,  # 默认I2C总线
                'i2c_address': 0x48,  # 默认I2C地址
                'gpio_pins': {"led_status": 18, "button_emergency": 19, "relay_power": 20},  # 默认GPIO配置
                'sensor_update_rate': self.config.hardware.SENSOR_POLLING_RATE,
                'enable_watchdog': True,  # 默认启用看门狗
                'watchdog_timeout': 5.0,  # 默认看门狗超时
            }
            
            ai_dict = {
                'model_path': self.config.ai.AI_MODEL_PATH,
                'device': self.config.ai.AI_DEVICE,
                'batch_size': self.config.ai.AI_BATCH_SIZE,
                'max_workers': self.config.ai.AI_MAX_WORKERS,
                'enable_face_detection': True,  # 默认启用
                'enable_object_detection': True,  # 默认启用
                'enable_pose_estimation': False,  # 默认禁用
                'enable_scene_analysis': False,  # 默认禁用
                'face_detection_threshold': self.config.ai.FACE_DETECTION_CONFIDENCE,
                'object_detection_threshold': self.config.ai.OBJECT_DETECTION_CONFIDENCE,
                'pose_estimation_threshold': self.config.ai.POSE_ESTIMATION_CONFIDENCE,
            }
            
            vision_config = VisionConfig(**vision_dict)
            realtime_config = RealtimeConfig(**realtime_dict)
            hardware_config = HardwareConfig(**hardware_dict)
            ai_config = AIConfig(**ai_dict)
            
            rust_system = rust_manager.create_system(
                vision_config, realtime_config, hardware_config, ai_config
            )
            
            self._components_status["rust_bindings"] = True
            logger.info("Rust绑定初始化完成")
            
        except Exception as e:
            logger.error(f"Rust绑定初始化失败: {e}")
            raise
    
    async def _initialize_api_server(self) -> None:
        """初始化API服务器"""
        try:
            logger.info("初始化API服务器...")
            
            # 创建FastAPI应用
            @asynccontextmanager
            async def lifespan(app: FastAPI):
                # 启动时的操作
                logger.info("FastAPI应用启动")
                yield
                # 关闭时的操作
                logger.info("FastAPI应用关闭")
                await self._shutdown_event.set()
            
            self.app = FastAPI(
                title="Reachy Mini API",
                description="Reachy Mini机器人控制API",
                version="1.0.0",
                lifespan=lifespan
            )
            
            # 添加中间件
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)
            
            # 注册异常处理器
            register_exception_handlers(self.app)
            
            # 挂载静态文件
            static_dir = Path("static")
            if static_dir.exists():
                self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
            
            # 注册路由
            await self._register_routes()
            
            self._components_status["api_server"] = True
            logger.info("API服务器初始化完成")
            
        except Exception as e:
            logger.error(f"API服务器初始化失败: {e}")
            raise
    
    async def _register_routes(self) -> None:
        """注册API路由"""
        try:
            # 导入并注册路由模块
            # 这里需要根据实际的路由模块进行调整
            
            # 健康检查路由
            @self.app.get("/health")
            async def health_check():
                return {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "components": self._components_status
                }
            
            # 系统信息路由
            @self.app.get("/system/info")
            async def system_info():
                info = {
                    "service_manager": {
                        "running": self._running,
                        "components": self._components_status
                    },
                    "config": {
                        "api_host": self.config.api_host,
                        "api_port": self.config.api_port,
                        "debug": self.config.debug,
                    }
                }
                
                # 添加Rust系统信息
                if is_rust_available():
                    rust_manager = get_rust_bindings_manager()
                    info["rust"] = rust_manager.get_system_info()
                
                return info
            
            # 系统状态路由
            @self.app.get("/system/status")
            async def system_status():
                return {
                    "running": self._running,
                    "components": self._components_status,
                    "uptime": time.time() - getattr(self, '_start_time', time.time())
                }
            
            logger.info("API路由注册完成")
            
        except Exception as e:
            logger.error(f"API路由注册失败: {e}")
            raise
    
    async def _initialize_websocket(self) -> None:
        """初始化WebSocket"""
        try:
            logger.info("初始化WebSocket...")
            
            # WebSocket连接管理器
            from fastapi import WebSocket, WebSocketDisconnect
            
            class ConnectionManager:
                def __init__(self):
                    self.active_connections: List[WebSocket] = []
                
                async def connect(self, websocket: WebSocket):
                    await websocket.accept()
                    self.active_connections.append(websocket)
                    logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
                
                def disconnect(self, websocket: WebSocket):
                    if websocket in self.active_connections:
                        self.active_connections.remove(websocket)
                    logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")
                
                async def send_personal_message(self, message: str, websocket: WebSocket):
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        logger.error(f"发送WebSocket消息失败: {e}")
                        self.disconnect(websocket)
                
                async def broadcast(self, message: str):
                    disconnected = []
                    for connection in self.active_connections:
                        try:
                            await connection.send_text(message)
                        except Exception as e:
                            logger.error(f"广播WebSocket消息失败: {e}")
                            disconnected.append(connection)
                    
                    # 清理断开的连接
                    for connection in disconnected:
                        self.disconnect(connection)
            
            self.websocket_manager = ConnectionManager()
            
            # WebSocket路由
            @self.app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                await self.websocket_manager.connect(websocket)
                try:
                    while True:
                        data = await websocket.receive_text()
                        # 处理接收到的消息
                        await self.websocket_manager.send_personal_message(
                            f"Echo: {data}", websocket
                        )
                except WebSocketDisconnect:
                    self.websocket_manager.disconnect(websocket)
            
            self._components_status["websocket"] = True
            logger.info("WebSocket初始化完成")
            
        except Exception as e:
            logger.error(f"WebSocket初始化失败: {e}")
            raise
    
    async def _initialize_scheduler(self) -> None:
        """初始化任务调度器"""
        try:
            logger.info("初始化任务调度器...")
            
            # 这里可以添加定期任务，如系统监控、数据清理等
            async def periodic_health_check():
                while self._running:
                    try:
                        # 检查各组件健康状态
                        db_manager = get_database_manager()
                        health_status = db_manager.health_check()
                        db_healthy = health_status["status"] == "healthy"
                        self._components_status["database"] = db_healthy
                        
                        if not db_healthy:
                            logger.warning(f"数据库健康检查失败: {health_status.get('error', '未知错误')}")
                        
                        # 等待下次检查
                        await asyncio.sleep(30)  # 每30秒检查一次
                        
                    except Exception as e:
                        logger.error(f"健康检查失败: {e}")
                        await asyncio.sleep(30)
            
            # 启动健康检查任务
            asyncio.create_task(periodic_health_check())
            
            self._components_status["scheduler"] = True
            logger.info("任务调度器初始化完成")
            
        except Exception as e:
            logger.error(f"任务调度器初始化失败: {e}")
            raise
    
    async def start(self) -> None:
        """启动所有服务"""
        with self._lock:
            if self._running:
                logger.warning("服务已在运行中")
                return
        
        try:
            logger.info("启动服务管理器...")
            self._start_time = time.time()
            
            # 初始化所有组件
            await self.initialize()
            
            # 启动API服务器
            config = uvicorn.Config(
                app=self.app,
                host=self.config.api_host,
                port=self.config.api_port,
                log_level="info" if self.config.debug else "warning",
                access_log=self.config.debug
            )
            
            self.server = uvicorn.Server(config)
            
            # 在后台启动服务器
            self.server_task = asyncio.create_task(self.server.serve())
            
            self._running = True
            logger.info(f"服务管理器启动成功，API服务器运行在 http://{self.config.api_host}:{self.config.api_port}")
            
        except Exception as e:
            logger.error(f"服务管理器启动失败: {e}")
            await self.cleanup()
            raise
    
    async def stop(self) -> None:
        """停止所有服务"""
        with self._lock:
            if not self._running:
                logger.warning("服务未在运行中")
                return
        
        logger.info("停止服务管理器...")
        
        try:
            # 设置关闭事件
            self._shutdown_event.set()
            
            # 停止API服务器
            if self.server:
                self.server.should_exit = True
                if self.server_task:
                    try:
                        await asyncio.wait_for(self.server_task, timeout=10.0)
                    except asyncio.TimeoutError:
                        logger.warning("API服务器停止超时")
                        self.server_task.cancel()
            
            # 清理资源
            await self.cleanup()
            
            self._running = False
            logger.info("服务管理器停止完成")
            
        except Exception as e:
            logger.error(f"服务管理器停止失败: {e}")
            raise
    
    async def cleanup(self) -> None:
        """清理所有资源"""
        logger.info("清理服务资源...")
        
        try:
            # 清理Rust绑定
            if self._components_status.get("rust_bindings"):
                cleanup_rust_bindings()
                self._components_status["rust_bindings"] = False
            
            # 清理数据库连接
            if self._components_status.get("database"):
                db_manager = get_database_manager()
                await db_manager.close_all_sessions()
                self._components_status["database"] = False
            
            # 重置组件状态
            for key in self._components_status:
                self._components_status[key] = False
            
            logger.info("服务资源清理完成")
            
        except Exception as e:
            logger.error(f"服务资源清理失败: {e}")
    
    async def restart(self) -> None:
        """重启服务"""
        logger.info("重启服务管理器...")
        await self.stop()
        await asyncio.sleep(1)  # 等待清理完成
        await self.start()
    
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "running": self._running,
            "components": self._components_status.copy(),
            "uptime": time.time() - getattr(self, '_start_time', time.time()) if self._running else 0,
            "config": {
                "api_host": self.config.api_host,
                "api_port": self.config.api_port,
                "debug": self.config.debug,
            }
        }


# 全局服务管理器实例
_service_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """获取全局服务管理器实例"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager


async def start_services() -> None:
    """启动所有服务"""
    manager = get_service_manager()
    await manager.start()


async def stop_services() -> None:
    """停止所有服务"""
    global _service_manager
    if _service_manager is not None:
        await _service_manager.stop()
        _service_manager = None


def setup_signal_handlers() -> None:
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"接收到信号 {signum}，准备关闭服务...")
        asyncio.create_task(stop_services())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置信号处理器
    setup_signal_handlers()
    
    try:
        # 启动服务
        await start_services()
        
        # 等待关闭信号
        manager = get_service_manager()
        while manager.is_running():
            await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，关闭服务...")
    except Exception as e:
        logger.error(f"服务运行异常: {e}")
    finally:
        await stop_services()


if __name__ == "__main__":
    asyncio.run(main())