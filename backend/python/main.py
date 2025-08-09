#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini Robot Control System - Main Application
基于Allspark2-Orin NX平台的Reachy Mini机器人控制系统主应用

这是 Reachy Mini 机器人系统的主要 FastAPI 应用程序，提供：
- REST API 接口
- WebSocket 实时通信
- AI 服务集成
- 视频流处理
- 机器人控制接口
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
import uvicorn

# 导入核心模块
from core.config import get_config, validate_config
from core.database import get_database_manager
from core.exceptions import register_exception_handlers, BaseReachyException
from service_manager import get_service_manager, setup_signal_handlers
from rust_bindings import is_rust_available, get_rust_system_info

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/reachy_mini.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 全局配置
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("🚀 启动 Reachy Mini 控制系统...")
    
    try:
        # 获取服务管理器并初始化
        service_manager = get_service_manager()
        await service_manager.initialize()
        
        logger.info("🎉 Reachy Mini 控制系统启动成功！")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 系统启动失败: {e}")
        raise
    finally:
        logger.info("🛑 正在关闭 Reachy Mini 控制系统...")
        
        try:
            # 清理服务管理器
            service_manager = get_service_manager()
            await service_manager.cleanup()
            
            logger.info("👋 Reachy Mini 控制系统已关闭")
            
        except Exception as e:
            logger.error(f"❌ 系统关闭时出错: {e}")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Reachy Mini Control API",
        description="Reachy Mini机器人控制系统API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if config.DEBUG else None,
        redoc_url="/redoc" if config.DEBUG else None,
    )
    
    # 设置中间件
    setup_middleware(app)
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    # 先设置静态文件（但不包括通配符路由）
    setup_static_files_basic(app)
    
    # 设置API路由
    setup_routes(app)
    
    # 最后设置SPA路由（通配符）
    setup_spa_route(app)
    
    return app


def setup_middleware(app: FastAPI):
    """设置FastAPI中间件
    
    配置应用程序的中间件栈，包括：
    - CORS: 处理跨域请求，允许前端访问API
    - GZip: 压缩响应数据，减少网络传输量
    
    Args:
        app: FastAPI应用实例
    """
    # CORS中间件 - 处理跨域资源共享
    # 允许前端应用从不同端口访问后端API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中应该限制具体域名
        allow_credentials=True,  # 允许携带认证信息
        allow_methods=["*"],     # 允许所有HTTP方法
        allow_headers=["*"],     # 允许所有请求头
    )
    
    # Gzip压缩中间件 - 自动压缩响应数据
    # 当响应大小超过1000字节时启用压缩
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    logger.info("✅ 中间件设置完成")


def setup_routes(app: FastAPI):
    """设置API路由
    
    定义所有的API端点，包括：
    - 系统信息和状态查询
    - 健康检查接口
    - WebSocket通信端点
    
    Args:
        app: FastAPI应用实例
    """
    
    @app.get("/api/root")
    async def root():
        """API根路径 - 提供系统基本信息
        
        Returns:
            dict: 包含系统名称、版本、状态等基本信息
        """
        return {
            "message": "Reachy Mini Control System",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs" if config.debug else "disabled",
            "health": "/health"
        }
    
    @app.get("/api/health")
    async def health_check():
        """健康检查API - 返回系统健康状态
        
        检查所有系统组件的运行状态，包括：
        - 服务管理器状态
        - 各个组件的健康状态
        - 系统配置信息
        - 运行时间统计
        
        Returns:
            dict: 系统健康状态信息
        """
        service_manager = get_service_manager()
        status = service_manager.get_status()
        
        return {
            "status": "healthy" if status["running"] else "unhealthy",
            "timestamp": status.get("uptime", 0),
            "components": status["components"],
            "config": status["config"]
        }
    
    @app.get("/system/info")
    async def system_info():
        """系统信息API - 返回详细的系统配置和环境信息
        
        收集并返回系统的详细信息，包括：
        - 服务管理器状态
        - 系统配置参数
        - Python运行环境信息
        - Rust模块可用性和信息
        
        Returns:
            dict: 完整的系统信息
        """
        service_manager = get_service_manager()
        info = {
            "service_manager": service_manager.get_status(),
            "config": {
                "api_host": config.api_host,
                "api_port": config.api_port,
                "debug": config.debug,
                "database_url": config.database.database_url.split("@")[-1] if "@" in config.database.database_url else "local",
            },
            "python": {
                "version": sys.version,
                "platform": sys.platform,
            }
        }
        
        # 添加Rust系统信息
        # 检查Rust模块是否可用并获取相关信息
        if is_rust_available():
            try:
                info["rust"] = get_rust_system_info()
            except Exception as e:
                info["rust"] = {"error": str(e)}
        else:
            info["rust"] = {"available": False}
        
        return info
    
    @app.get("/system/status")
    async def system_status():
        """系统状态API - 返回当前系统运行状态
        
        获取系统的实时运行状态，包括：
        - 各个服务组件的运行状态
        - 系统资源使用情况
        - 错误和警告信息
        
        Returns:
            dict: 系统运行状态信息
        """
        service_manager = get_service_manager()
        return service_manager.get_status()
    
    # WebSocket路由
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """通用WebSocket端点"""
        await websocket.accept()
        logger.info("WebSocket连接建立")
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                logger.info(f"收到WebSocket消息: {data}")
                
                # 回显消息
                await websocket.send_text(f"Echo: {data}")
                
        except WebSocketDisconnect:
            logger.info("WebSocket连接断开")
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
            await websocket.close()
    
    @app.websocket("/ws/control")
    async def websocket_control_endpoint(websocket: WebSocket):
        """机器人控制WebSocket端点"""
        await websocket.accept()
        logger.info("控制WebSocket连接建立")
        
        try:
            while True:
                data = await websocket.receive_text()
                logger.info(f"收到控制命令: {data}")
                
                # 这里可以添加实际的机器人控制逻辑
                response = {
                    "type": "control_response",
                    "data": f"已处理控制命令: {data}",
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                await websocket.send_json(response)
                
        except WebSocketDisconnect:
            logger.info("控制WebSocket连接断开")
        except Exception as e:
            logger.error(f"控制WebSocket错误: {e}")
            await websocket.close()
    
    @app.websocket("/ws/stream")
    async def websocket_stream_endpoint(websocket: WebSocket):
        """视频流WebSocket端点"""
        await websocket.accept()
        logger.info("流媒体WebSocket连接建立")
        
        try:
            while True:
                data = await websocket.receive_text()
                logger.info(f"收到流媒体请求: {data}")
                
                # 这里可以添加实际的视频流处理逻辑
                response = {
                    "type": "stream_response",
                    "data": f"流媒体响应: {data}",
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                await websocket.send_json(response)
                
        except WebSocketDisconnect:
            logger.info("流媒体WebSocket连接断开")
        except Exception as e:
            logger.error(f"流媒体WebSocket错误: {e}")
            await websocket.close()
    
    logger.info("✅ 路由设置完成")


def setup_static_files_basic(app: FastAPI):
    """设置基本静态文件服务（不包括通配符路由）"""
    # 设置前端静态文件服务
    frontend_dist = Path("../../frontend/dist")
    if frontend_dist.exists():
        # 挂载静态资源
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
        
        # 为根路径提供index.html
        @app.get("/", response_class=FileResponse)
        async def serve_frontend():
            return frontend_dist / "index.html"
        
        logger.info(f"✅ 前端静态文件服务设置完成: {frontend_dist}")
    else:
        logger.warning(f"⚠️ 前端构建目录不存在: {frontend_dist}")
    
    # 传统静态文件目录
    static_dir = Path("static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"✅ 静态文件服务设置完成: {static_dir}")
    else:
        logger.warning(f"⚠️ 静态文件目录不存在: {static_dir}")


def setup_spa_route(app: FastAPI):
    """设置SPA路由（通配符路由，必须最后设置）"""
    frontend_dist = Path("../../frontend/dist")
    if frontend_dist.exists():
        # 为所有未匹配的路径提供index.html (SPA路由支持)
        @app.get("/{full_path:path}", response_class=FileResponse)
        async def serve_spa(full_path: str):
            # 检查是否是静态文件
            file_path = frontend_dist / full_path
            if file_path.exists() and file_path.is_file():
                return file_path
            
            # 否则返回index.html用于SPA路由
            return frontend_dist / "index.html"
        
        logger.info(f"✅ SPA路由设置完成")


# 创建应用实例
app = create_app()


def setup_environment():
    """设置运行环境"""
    # 创建必要的目录
    directories = ['logs', 'data', 'models', 'static', 'uploads', 'temp']
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")
    
    # 设置环境变量
    os.environ.setdefault('PYTHONPATH', str(Path(__file__).parent))
    os.environ.setdefault('REACHY_MINI_ENV', 'development')
    
    logger.info("✅ 运行环境设置完成")


def check_dependencies() -> bool:
    """检查依赖项"""
    logger.info("检查依赖项...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'alembic',
        'pydantic',
        'asyncpg',  # PostgreSQL异步驱动
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("✅ 依赖项检查通过")
    return True


def validate_system_config() -> bool:
    """验证系统配置"""
    logger.info("验证系统配置...")
    
    try:
        # 验证配置
        if not validate_config():
            logger.error("❌ 配置验证失败")
            return False
        
        # 检查关键配置项
        if not config.database.database_url:
            logger.error("❌ 数据库URL未配置")
            return False
        
        if not (1024 <= config.api_port <= 65535):
            logger.error(f"❌ API端口配置无效: {config.api_port}")
            return False
        
        logger.info("✅ 系统配置验证通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置验证失败: {e}")
        return False


async def startup_checks() -> bool:
    """启动前检查"""
    logger.info("执行启动前检查...")
    
    # 检查依赖项
    if not check_dependencies():
        return False
    
    # 验证配置
    if not validate_system_config():
        return False
    
    # 检查Rust模块
    try:
        if is_rust_available():
            logger.info("✅ Rust模块可用")
            rust_info = get_rust_system_info()
            logger.info(f"Rust系统信息: {rust_info}")
        else:
            logger.warning("⚠️ Rust模块不可用，某些功能可能受限")
    except Exception as e:
        logger.warning(f"⚠️ Rust模块检查失败: {e}")
    
    logger.info("✅ 启动前检查完成")
    return True


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，准备关闭服务...")
    # 这里可以添加优雅关闭逻辑
    sys.exit(0)


async def main_async():
    """异步主函数"""
    logger.info("="*50)
    logger.info("🚀 Reachy Mini Python后端启动")
    logger.info("="*50)
    
    try:
        # 设置运行环境
        setup_environment()
        
        # 执行启动前检查
        if not await startup_checks():
            logger.error("❌ 启动前检查失败，退出程序")
            sys.exit(1)
        
        # 设置信号处理器
        setup_signal_handlers()
        
        # 启动服务器
        server_config = uvicorn.Config(
            app=app,
            host=config.api_host,
            port=config.api_port,
            log_level="info" if config.debug else "warning",
            access_log=config.debug,
            reload=config.debug,
        )
        
        server = uvicorn.Server(server_config)
        
        # 打印启动信息
        logger.info("="*50)
        logger.info("🎉 服务启动成功！")
        logger.info(f"📡 API服务器: http://{config.api_host}:{config.api_port}")
        logger.info(f"🔌 WebSocket: ws://{config.api_host}:{config.api_port}/ws")
        logger.info(f"❤️ 健康检查: http://{config.api_host}:{config.api_port}/health")
        logger.info(f"ℹ️ 系统信息: http://{config.api_host}:{config.api_port}/system/info")
        if config.debug:
            logger.info(f"📚 API文档: http://{config.api_host}:{config.api_port}/docs")
        logger.info(f"🐛 调试模式: {'开启' if config.debug else '关闭'}")
        logger.info("="*50)
        
        # 启动服务器
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("接收到键盘中断信号")
    except BaseReachyException as e:
        logger.error(f"❌ Reachy异常: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 未处理的异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("👋 Reachy Mini Python后端已退出")


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ["--help", "-h"]:
            print("Reachy Mini Python后端")
            print("")
            print("用法:")
            print("  python main.py          # 启动服务器")
            print("  python main.py --help   # 显示帮助信息")
            print("  python main.py --version # 显示版本信息")
            print("")
            print("环境变量:")
            print("  REACHY_MINI_ENV         # 运行环境 (development/production)")
            print("  REACHY_MINI_CONFIG      # 配置文件路径")
            print("  REACHY_MINI_LOG_LEVEL   # 日志级别 (DEBUG/INFO/WARNING/ERROR)")
            sys.exit(0)
        
        elif command in ["--version", "-v"]:
            print("Reachy Mini Python后端 v1.0.0")
            sys.exit(0)
        
        else:
            print(f"❌ 未知命令: {command}")
            print("使用 --help 查看帮助信息")
            sys.exit(1)
    
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动异步主函数
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()