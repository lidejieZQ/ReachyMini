#!/usr/bin/env python3
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
import uvicorn

from core.config import get_config
from service_manager import get_service_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        title="Reachy Mini Control System",
        description="基于Allspark2-Orin NX平台的Reachy Mini机器人控制系统",
        version="1.0.0",
        lifespan=lifespan
    )
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "Reachy Mini系统运行正常"}
    
    return app

if __name__ == "__main__":
    logger.info("="*50)
    logger.info("🚀 使用简化方式启动Reachy Mini")
    logger.info("="*50)
    
    app = create_app()
    
    logger.info(f"启动服务器: http://{config.api_host}:{config.api_port}")
    
    # 使用uvicorn.run直接启动
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level="info",
        access_log=True
    )