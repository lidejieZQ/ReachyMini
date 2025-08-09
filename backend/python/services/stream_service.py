#!/usr/bin/env python3
"""
视频流服务
负责摄像头数据采集、视频流处理和WebRTC传输
"""

import asyncio
import json
import logging
import cv2
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import base64
import io
from PIL import Image
import threading
from queue import Queue, Empty

from core.config import get_config
from utils.logger import setup_logger

# 获取配置
config = get_config()

logger = setup_logger(__name__)


class VideoCapture:
    """视频捕获类"""
    
    def __init__(self, source: int = 0):
        self.source = source
        self.cap = None
        self.is_opened = False
        self.frame_queue = Queue(maxsize=10)
        self.capture_thread = None
        self.stop_event = threading.Event()
        
        # 视频参数
        self.width = getattr(config, 'stream_width', 640)
        self.height = getattr(config, 'stream_height', 480)
        self.fps = getattr(config, 'stream_fps', 30)
        
    def open(self) -> bool:
        """打开摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                logger.error(f"无法打开摄像头: {self.source}")
                return False
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 获取实际参数
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"摄像头已打开: {actual_width}x{actual_height}@{actual_fps}fps")
            
            self.is_opened = True
            return True
            
        except Exception as e:
            logger.error(f"打开摄像头失败: {e}")
            return False
    
    def start_capture(self):
        """开始捕获视频"""
        if not self.is_opened:
            return False
        
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        logger.info("视频捕获已启动")
        return True
    
    def _capture_loop(self):
        """视频捕获循环"""
        while not self.stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("无法读取视频帧")
                    continue
                
                # 添加时间戳
                timestamp = datetime.now()
                
                # 如果队列满了，移除旧帧
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                
                # 添加新帧
                self.frame_queue.put((frame, timestamp))
                
            except Exception as e:
                logger.error(f"视频捕获循环出错: {e}")
                break
    
    def get_frame(self) -> Optional[tuple]:
        """获取最新帧"""
        try:
            return self.frame_queue.get_nowait()
        except Empty:
            return None
    
    def stop_capture(self):
        """停止捕获"""
        self.stop_event.set()
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1)
        
        logger.info("视频捕获已停止")
    
    def close(self):
        """关闭摄像头"""
        self.stop_capture()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.is_opened = False
        logger.info("摄像头已关闭")


class StreamService:
    """视频流服务"""
    
    def __init__(self):
        self.video_capture = None
        self.is_streaming = False
        self.stream_clients = set()
        self.frame_processors = []
        
        # 流统计
        self.stream_stats = {
            "frames_captured": 0,
            "frames_processed": 0,
            "frames_sent": 0,
            "average_fps": 0.0,
            "last_frame_time": None,
            "connected_clients": 0
        }
        
        # 流处理任务
        self.stream_task = None
        self.stats_task = None
        
        # 帧处理回调
        self.frame_callbacks = []
        
    async def initialize(self, camera_source: int = 0) -> bool:
        """初始化视频流服务"""
        try:
            logger.info(f"正在初始化视频流服务，摄像头源: {camera_source}")
            
            # 创建视频捕获对象
            self.video_capture = VideoCapture(camera_source)
            
            # 尝试打开摄像头
            if not self.video_capture.open():
                # 如果指定摄像头失败，尝试默认摄像头
                if camera_source != 0:
                    logger.warning(f"摄像头 {camera_source} 打开失败，尝试默认摄像头")
                    self.video_capture = VideoCapture(0)
                    if not self.video_capture.open():
                        raise Exception("无法打开任何摄像头")
                else:
                    raise Exception("无法打开默认摄像头")
            
            logger.info("视频流服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"视频流服务初始化失败: {e}")
            return False
    
    async def start_streaming(self) -> bool:
        """开始视频流"""
        try:
            if self.is_streaming:
                logger.info("视频流已经在运行")
                return True
            
            if not self.video_capture or not self.video_capture.is_opened:
                raise Exception("摄像头未初始化或未打开")
            
            # 开始视频捕获
            if not self.video_capture.start_capture():
                raise Exception("无法启动视频捕获")
            
            # 启动流处理任务
            self.stream_task = asyncio.create_task(self._stream_loop())
            self.stats_task = asyncio.create_task(self._stats_loop())
            
            self.is_streaming = True
            logger.info("视频流已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动视频流失败: {e}")
            return False
    
    async def stop_streaming(self):
        """停止视频流"""
        try:
            if not self.is_streaming:
                return
            
            logger.info("正在停止视频流...")
            
            self.is_streaming = False
            
            # 取消任务
            if self.stream_task and not self.stream_task.done():
                self.stream_task.cancel()
                try:
                    await self.stream_task
                except asyncio.CancelledError:
                    pass
            
            if self.stats_task and not self.stats_task.done():
                self.stats_task.cancel()
                try:
                    await self.stats_task
                except asyncio.CancelledError:
                    pass
            
            # 停止视频捕获
            if self.video_capture:
                self.video_capture.stop_capture()
            
            logger.info("视频流已停止")
            
        except Exception as e:
            logger.error(f"停止视频流时出错: {e}")
    
    async def _stream_loop(self):
        """视频流处理循环"""
        frame_interval = 1.0 / settings.STREAM_FPS
        
        while self.is_streaming:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # 获取最新帧
                frame_data = self.video_capture.get_frame()
                if frame_data is None:
                    await asyncio.sleep(0.01)
                    continue
                
                frame, timestamp = frame_data
                self.stream_stats["frames_captured"] += 1
                
                # 处理帧
                processed_frame = await self._process_frame(frame)
                self.stream_stats["frames_processed"] += 1
                
                # 发送给客户端
                if self.stream_clients:
                    await self._send_frame_to_clients(processed_frame, timestamp)
                    self.stream_stats["frames_sent"] += 1
                
                # 调用帧回调
                for callback in self.frame_callbacks:
                    try:
                        await callback(processed_frame, timestamp)
                    except Exception as e:
                        logger.error(f"帧回调执行失败: {e}")
                
                # 控制帧率
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                self.stream_stats["last_frame_time"] = timestamp
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"视频流处理循环出错: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """处理视频帧"""
        try:
            processed_frame = frame.copy()
            
            # 应用帧处理器
            for processor in self.frame_processors:
                processed_frame = await processor(processed_frame)
            
            return processed_frame
            
        except Exception as e:
            logger.error(f"帧处理失败: {e}")
            return frame
    
    async def _send_frame_to_clients(self, frame: np.ndarray, timestamp: datetime):
        """发送帧给所有客户端"""
        try:
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, settings.STREAM_QUALITY])
            
            # 转换为base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # 创建消息
            message = {
                "type": "video_frame",
                "data": f"data:image/jpeg;base64,{frame_base64}",
                "timestamp": timestamp.isoformat(),
                "frame_info": {
                    "width": frame.shape[1],
                    "height": frame.shape[0],
                    "channels": frame.shape[2] if len(frame.shape) > 2 else 1
                }
            }
            
            # 发送给所有客户端（这里需要与WebSocket管理器集成）
            # 暂时记录日志
            if len(self.stream_clients) > 0:
                logger.debug(f"发送帧给 {len(self.stream_clients)} 个客户端")
            
        except Exception as e:
            logger.error(f"发送帧给客户端失败: {e}")
    
    async def _stats_loop(self):
        """统计信息更新循环"""
        last_frame_count = 0
        last_time = asyncio.get_event_loop().time()
        
        while self.is_streaming:
            try:
                await asyncio.sleep(1.0)  # 每秒更新一次
                
                current_time = asyncio.get_event_loop().time()
                current_frame_count = self.stream_stats["frames_processed"]
                
                # 计算FPS
                time_diff = current_time - last_time
                frame_diff = current_frame_count - last_frame_count
                
                if time_diff > 0:
                    fps = frame_diff / time_diff
                    self.stream_stats["average_fps"] = fps
                
                last_time = current_time
                last_frame_count = current_frame_count
                
                # 更新客户端数量
                self.stream_stats["connected_clients"] = len(self.stream_clients)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"统计信息更新失败: {e}")
    
    def add_client(self, client_id: str):
        """添加流客户端"""
        self.stream_clients.add(client_id)
        logger.info(f"添加流客户端: {client_id}，当前客户端数: {len(self.stream_clients)}")
    
    def remove_client(self, client_id: str):
        """移除流客户端"""
        self.stream_clients.discard(client_id)
        logger.info(f"移除流客户端: {client_id}，当前客户端数: {len(self.stream_clients)}")
    
    def add_frame_processor(self, processor: Callable):
        """添加帧处理器"""
        self.frame_processors.append(processor)
        logger.info(f"添加帧处理器，当前处理器数: {len(self.frame_processors)}")
    
    def remove_frame_processor(self, processor: Callable):
        """移除帧处理器"""
        if processor in self.frame_processors:
            self.frame_processors.remove(processor)
            logger.info(f"移除帧处理器，当前处理器数: {len(self.frame_processors)}")
    
    def add_frame_callback(self, callback: Callable):
        """添加帧回调"""
        self.frame_callbacks.append(callback)
        logger.info(f"添加帧回调，当前回调数: {len(self.frame_callbacks)}")
    
    def remove_frame_callback(self, callback: Callable):
        """移除帧回调"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
            logger.info(f"移除帧回调，当前回调数: {len(self.frame_callbacks)}")
    
    async def capture_snapshot(self) -> Optional[str]:
        """捕获快照"""
        try:
            if not self.video_capture:
                raise Exception("摄像头未初始化")
            
            frame_data = self.video_capture.get_frame()
            if frame_data is None:
                raise Exception("无法获取视频帧")
            
            frame, timestamp = frame_data
            
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # 转换为base64
            snapshot_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.info("快照捕获成功")
            return f"data:image/jpeg;base64,{snapshot_base64}"
            
        except Exception as e:
            logger.error(f"捕获快照失败: {e}")
            return None
    
    def get_stream_info(self) -> Dict[str, Any]:
        """获取流信息"""
        return {
            "is_streaming": self.is_streaming,
            "camera_opened": self.video_capture.is_opened if self.video_capture else False,
            "stream_settings": {
                "width": settings.STREAM_WIDTH,
                "height": settings.STREAM_HEIGHT,
                "fps": settings.STREAM_FPS,
                "quality": settings.STREAM_QUALITY
            },
            "stats": self.stream_stats.copy(),
            "processors_count": len(self.frame_processors),
            "callbacks_count": len(self.frame_callbacks)
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("正在清理视频流服务资源...")
            
            # 停止流
            await self.stop_streaming()
            
            # 关闭摄像头
            if self.video_capture:
                self.video_capture.close()
                self.video_capture = None
            
            # 清空客户端和处理器
            self.stream_clients.clear()
            self.frame_processors.clear()
            self.frame_callbacks.clear()
            
            logger.info("视频流服务资源清理完成")
            
        except Exception as e:
            logger.error(f"视频流服务清理时出错: {e}")


# 全局视频流服务实例
stream_service = StreamService()