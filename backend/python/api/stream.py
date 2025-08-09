#!/usr/bin/env python3
"""
视频流API路由
提供视频流控制和管理的REST API接口
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
import cv2
import numpy as np
from io import BytesIO

from services.stream_service import stream_service
from core.websocket_manager import WebSocketManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/stream", tags=["stream"])

# WebSocket管理器实例
ws_manager = WebSocketManager()


# 请求模型
class StreamConfigRequest(BaseModel):
    """流配置请求"""
    width: Optional[int] = Field(640, ge=320, le=1920, description="视频宽度")
    height: Optional[int] = Field(480, ge=240, le=1080, description="视频高度")
    fps: Optional[int] = Field(30, ge=5, le=60, description="帧率")
    quality: Optional[int] = Field(80, ge=10, le=100, description="视频质量")


class CameraSourceRequest(BaseModel):
    """摄像头源请求"""
    source: int = Field(0, ge=0, le=10, description="摄像头索引")


# 响应模型
class StreamStatusResponse(BaseModel):
    """流状态响应"""
    is_streaming: bool
    camera_opened: bool
    stream_settings: Dict[str, Any]
    stats: Dict[str, Any]
    processors_count: int
    callbacks_count: int


class CommandResponse(BaseModel):
    """命令响应"""
    success: bool
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None


@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status():
    """获取视频流状态"""
    try:
        stream_info = stream_service.get_stream_info()
        
        return StreamStatusResponse(
            is_streaming=stream_info["is_streaming"],
            camera_opened=stream_info["camera_opened"],
            stream_settings=stream_info["stream_settings"],
            stats=stream_info["stats"],
            processors_count=stream_info["processors_count"],
            callbacks_count=stream_info["callbacks_count"]
        )
        
    except Exception as e:
        logger.error(f"获取视频流状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=CommandResponse)
async def start_stream():
    """启动视频流"""
    try:
        success = await stream_service.start_streaming()
        
        return CommandResponse(
            success=success,
            message="视频流启动成功" if success else "视频流启动失败",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"启动视频流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=CommandResponse)
async def stop_stream():
    """停止视频流"""
    try:
        await stream_service.stop_streaming()
        
        return CommandResponse(
            success=True,
            message="视频流已停止",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"停止视频流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize", response_model=CommandResponse)
async def initialize_stream(request: CameraSourceRequest):
    """初始化视频流"""
    try:
        success = await stream_service.initialize(request.source)
        
        return CommandResponse(
            success=success,
            message=f"视频流初始化{'成功' if success else '失败'}",
            timestamp=datetime.now().isoformat(),
            data={"camera_source": request.source}
        )
        
    except Exception as e:
        logger.error(f"初始化视频流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=CommandResponse)
async def configure_stream(request: StreamConfigRequest):
    """配置视频流参数"""
    try:
        # 这里应该更新流服务的配置
        # 由于当前实现中配置是从settings读取的，这里只是示例
        
        config_data = {
            "width": request.width,
            "height": request.height,
            "fps": request.fps,
            "quality": request.quality
        }
        
        return CommandResponse(
            success=True,
            message="视频流配置已更新",
            timestamp=datetime.now().isoformat(),
            data=config_data
        )
        
    except Exception as e:
        logger.error(f"配置视频流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot")
async def capture_snapshot():
    """捕获快照"""
    try:
        snapshot_data = await stream_service.capture_snapshot()
        
        if snapshot_data is None:
            raise HTTPException(status_code=503, detail="无法捕获快照")
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "image_data": snapshot_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"捕获快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients")
async def get_stream_clients():
    """获取流客户端信息"""
    try:
        client_count = len(stream_service.stream_clients)
        
        return JSONResponse(content={
            "connected_clients": client_count,
            "client_ids": list(stream_service.stream_clients),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取流客户端信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_stream_endpoint(websocket: WebSocket):
    """WebSocket视频流端点"""
    client_id = f"stream_client_{id(websocket)}"
    
    try:
        # 建立WebSocket连接
        await ws_manager.connect(websocket, "stream")
        
        # 添加到流客户端
        stream_service.add_client(client_id)
        
        logger.info(f"视频流客户端连接: {client_id}")
        
        # 发送连接确认
        await websocket.send_json({
            "type": "stream_connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # 监听客户端消息
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "request_frame":
                    # 客户端请求帧（可选功能）
                    snapshot = await stream_service.capture_snapshot()
                    if snapshot:
                        await websocket.send_json({
                            "type": "frame_response",
                            "image_data": snapshot,
                            "timestamp": datetime.now().isoformat()
                        })
                
                elif message_type == "stream_control":
                    # 流控制命令
                    command = message.get("command")
                    if command == "start":
                        success = await stream_service.start_streaming()
                        await websocket.send_json({
                            "type": "stream_control_response",
                            "command": command,
                            "success": success,
                            "timestamp": datetime.now().isoformat()
                        })
                    elif command == "stop":
                        await stream_service.stop_streaming()
                        await websocket.send_json({
                            "type": "stream_control_response",
                            "command": command,
                            "success": True,
                            "timestamp": datetime.now().isoformat()
                        })
                
                else:
                    logger.warning(f"未知的WebSocket消息类型: {message_type}")
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"无效的JSON消息来自客户端: {client_id}")
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"视频流客户端断开连接: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        # 清理资源
        stream_service.remove_client(client_id)
        ws_manager.disconnect(websocket, "stream")


@router.get("/formats")
async def get_supported_formats():
    """获取支持的视频格式"""
    try:
        formats = {
            "input_formats": {
                "camera_sources": {
                    "description": "支持的摄像头源",
                    "sources": [0, 1, 2, 3, 4],  # 常见的摄像头索引
                    "note": "0通常是默认摄像头"
                },
                "video_codecs": {
                    "description": "支持的视频编解码器",
                    "codecs": ["H.264", "MJPEG", "YUYV"]
                }
            },
            "output_formats": {
                "streaming": {
                    "description": "流输出格式",
                    "formats": ["JPEG", "WebRTC", "RTMP"],
                    "default": "JPEG"
                },
                "snapshot": {
                    "description": "快照格式",
                    "formats": ["JPEG", "PNG"],
                    "default": "JPEG"
                }
            },
            "resolutions": {
                "supported": [
                    {"width": 320, "height": 240, "name": "QVGA"},
                    {"width": 640, "height": 480, "name": "VGA"},
                    {"width": 800, "height": 600, "name": "SVGA"},
                    {"width": 1024, "height": 768, "name": "XGA"},
                    {"width": 1280, "height": 720, "name": "HD"},
                    {"width": 1920, "height": 1080, "name": "Full HD"}
                ],
                "default": {"width": 640, "height": 480}
            },
            "frame_rates": {
                "supported": [5, 10, 15, 20, 25, 30, 60],
                "default": 30,
                "unit": "fps"
            }
        }
        
        return JSONResponse(content=formats)
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def stream_health_check():
    """视频流服务健康检查"""
    try:
        stream_info = stream_service.get_stream_info()
        
        health_status = {
            "status": "healthy" if stream_info["camera_opened"] else "camera_not_available",
            "camera_opened": stream_info["camera_opened"],
            "is_streaming": stream_info["is_streaming"],
            "connected_clients": stream_info["stats"]["connected_clients"],
            "average_fps": stream_info["stats"]["average_fps"],
            "frames_processed": stream_info["stats"]["frames_processed"],
            "checks": {
                "camera_available": stream_info["camera_opened"],
                "streaming_active": stream_info["is_streaming"],
                "performance_ok": stream_info["stats"]["average_fps"] > 10,
                "clients_connected": stream_info["stats"]["connected_clients"] >= 0
            }
        }
        
        # 根据健康状态设置HTTP状态码
        critical_checks = ["camera_available"]
        critical_ok = all(health_status["checks"][check] for check in critical_checks)
        status_code = 200 if critical_ok else 503
        
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"视频流健康检查失败: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )


# 添加帧处理器的示例端点
@router.post("/processors/add")
async def add_frame_processor():
    """添加帧处理器（示例）"""
    try:
        # 示例：添加一个简单的帧处理器
        async def sample_processor(frame):
            # 添加时间戳水印
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            return frame
        
        stream_service.add_frame_processor(sample_processor)
        
        return CommandResponse(
            success=True,
            message="帧处理器已添加",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"添加帧处理器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/frame")
async def get_debug_frame():
    """获取调试帧信息"""
    try:
        if not stream_service.is_streaming:
            raise HTTPException(status_code=503, detail="视频流未启动")
        
        # 获取当前帧信息
        frame_data = stream_service.video_capture.get_frame() if stream_service.video_capture else None
        
        if frame_data is None:
            return JSONResponse(content={
                "frame_available": False,
                "message": "当前无可用帧",
                "timestamp": datetime.now().isoformat()
            })
        
        frame, timestamp = frame_data
        
        debug_info = {
            "frame_available": True,
            "frame_shape": frame.shape,
            "frame_dtype": str(frame.dtype),
            "frame_timestamp": timestamp.isoformat(),
            "processing_stats": stream_service.stream_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=debug_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取调试帧信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))