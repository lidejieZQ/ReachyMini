#!/usr/bin/env python3
"""
WebSocket连接管理器
管理WebSocket连接和消息分发
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储不同类型的连接
        self.connections: Dict[str, Set[WebSocket]] = {
            "control": set(),
            "stream": set(),
            "monitor": set()
        }
        
        # 连接元数据
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
        # 心跳任务
        self.heartbeat_task: asyncio.Task = None
        self.heartbeat_interval = 30  # 秒
        
        # 启动心跳
        self._start_heartbeat()
    
    async def connect(self, websocket: WebSocket, connection_type: str = "control"):
        """建立WebSocket连接"""
        try:
            await websocket.accept()
            
            # 添加到连接池
            if connection_type not in self.connections:
                self.connections[connection_type] = set()
            
            self.connections[connection_type].add(websocket)
            
            # 记录连接信息
            self.connection_info[websocket] = {
                "type": connection_type,
                "connected_at": datetime.now(),
                "last_ping": datetime.now(),
                "client_info": websocket.client
            }
            
            logger.info(f"WebSocket连接建立: {connection_type}, 客户端: {websocket.client}")
            
            # 发送连接确认
            await self.send_to_websocket(websocket, {
                "type": "connection_established",
                "connection_type": connection_type,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            raise
    
    async def disconnect(self, websocket: WebSocket, connection_type: str = None):
        """断开WebSocket连接"""
        client_id = None
        
        try:
            # 查找对应的连接
            for cid, connection in self.connections.items():
                if connection.websocket == websocket:
                    client_id = cid
                    break
            
            if client_id:
                await self._remove_connection(client_id)
                logger.info(f"WebSocket连接已断开: {client_id}")
            else:
                logger.warning("尝试断开未找到的WebSocket连接")
                
        except Exception as e:
            logger.error(f"断开WebSocket连接时出错: {e}")
    
    async def _remove_connection(self, client_id: str):
        """移除连接"""
        if client_id in self.connections:
            connection = self.connections[client_id]
            
            # 从类型分组中移除
            self.connections_by_type[connection.connection_type].discard(client_id)
            
            # 标记为非活跃
            connection.is_active = False
            
            # 移除连接
            del self.connections[client_id]
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """向指定客户端发送消息"""
        if client_id not in self.connections:
            logger.warning(f"尝试向不存在的客户端发送消息: {client_id}")
            return False
        
        connection = self.connections[client_id]
        
        try:
            # 确保消息包含时间戳
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            await connection.websocket.send_text(json.dumps(message))
            return True
            
        except WebSocketDisconnect:
            logger.info(f"客户端已断开连接: {client_id}")
            await self._remove_connection(client_id)
            return False
        except Exception as e:
            logger.error(f"向客户端 {client_id} 发送消息失败: {e}")
            await self._remove_connection(client_id)
            return False
    
    async def send_to_type(self, connection_type: str, message: Dict[str, Any]) -> int:
        """向指定类型的所有客户端发送消息"""
        if connection_type not in self.connections_by_type:
            logger.warning(f"连接类型不存在: {connection_type}")
            return 0
        
        client_ids = list(self.connections_by_type[connection_type])
        success_count = 0
        
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast(self, message: Dict[str, Any], exclude_client: Optional[str] = None) -> int:
        """向所有客户端广播消息"""
        client_ids = list(self.connections.keys())
        success_count = 0
        
        for client_id in client_ids:
            if client_id != exclude_client:
                if await self.send_to_client(client_id, message):
                    success_count += 1
        
        return success_count
    
    async def handle_control_message(self, data: Dict[str, Any], websocket: WebSocket):
        """处理控制消息"""
        try:
            message_type = data.get("type")
            
            if message_type == "ping":
                # 处理心跳
                await self.send_to_websocket(websocket, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
                # 更新最后ping时间
                if websocket in self.connection_info:
                    self.connection_info[websocket]["last_ping"] = datetime.now()
            
            elif message_type == "robot_control":
                # 处理机器人控制命令
                await self._handle_robot_control(data, websocket)
            
            elif message_type == "get_status":
                # 获取系统状态
                await self._handle_status_request(websocket)
            
            else:
                logger.warning(f"未知的消息类型: {message_type}")
                await self.send_to_websocket(websocket, {
                    "type": "error",
                    "message": f"未知的消息类型: {message_type}"
                })
        
        except Exception as e:
            logger.error(f"处理控制消息时出错: {e}")
            await self.send_to_websocket(websocket, {
                "type": "error",
                "message": str(e)
            })
    
    async def _handle_robot_control(self, data: Dict[str, Any], websocket: WebSocket):
        """处理机器人控制命令"""
        try:
            # 这里需要与机器人服务交互
            # 暂时返回确认消息
            await self.send_to_websocket(websocket, {
                "type": "robot_control_ack",
                "command": data.get("command"),
                "status": "received",
                "timestamp": datetime.now().isoformat()
            })
            
            # 广播状态更新给所有监控连接
            await self.broadcast_to_type("monitor", {
                "type": "robot_status_update",
                "command": data.get("command"),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"处理机器人控制命令时出错: {e}")
            raise
    
    async def _handle_status_request(self, websocket: WebSocket):
        """处理状态请求"""
        try:
            status = {
                "type": "system_status",
                "connections": {
                    conn_type: len(conn_set) 
                    for conn_type, conn_set in self.connections.items()
                },
                "timestamp": datetime.now().isoformat(),
                "uptime": "unknown",  # 可以添加系统运行时间
                "robot_connected": False,  # 需要从机器人服务获取
                "ai_ready": False,  # 需要从AI服务获取
                "stream_active": False  # 需要从流服务获取
            }
            
            await self.send_to_websocket(websocket, status)
            
        except Exception as e:
            logger.error(f"处理状态请求时出错: {e}")
            raise
    
    def _start_heartbeat_task(self):
        """启动心跳检测任务"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测循环出错: {e}")
    
    async def _check_heartbeats(self):
        """检查心跳超时"""
        now = datetime.now()
        timeout_threshold = now - timedelta(seconds=self.heartbeat_timeout)
        
        timeout_clients = []
        
        for client_id, connection in self.connections.items():
            if connection.last_heartbeat < timeout_threshold:
                timeout_clients.append(client_id)
        
        # 移除超时的连接
        for client_id in timeout_clients:
            logger.warning(f"客户端心跳超时，断开连接: {client_id}")
            try:
                connection = self.connections[client_id]
                await connection.websocket.close(code=1001, reason="Heartbeat timeout")
            except:
                pass
            await self._remove_connection(client_id)
    
    async def cleanup(self):
        """清理资源"""
        logger.info("开始清理WebSocket管理器资源")
        
        # 取消心跳任务
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有连接
        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            try:
                connection = self.connections[client_id]
                await connection.websocket.close(code=1001, reason="Server shutdown")
            except:
                pass
            await self._remove_connection(client_id)
        
        logger.info("WebSocket管理器资源清理完成")
    
    def get_connection_count(self, connection_type: str = None) -> int:
        """获取连接数量"""
        if connection_type:
            return len(self.connections.get(connection_type, set()))
        else:
            return sum(len(conn_set) for conn_set in self.connections.values())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        stats = {
            "total_connections": len(self.connections),
            "connections_by_type": {
                conn_type: len(client_ids)
                for conn_type, client_ids in self.connections_by_type.items()
            },
            "active_connections": sum(1 for conn in self.connections.values() if conn.is_active),
            "oldest_connection": None,
            "newest_connection": None
        }
        
        if self.connections:
            connections_by_time = sorted(
                self.connections.values(),
                key=lambda x: x.connected_at
            )
            stats["oldest_connection"] = {
                "client_id": connections_by_time[0].client_id,
                "connected_at": connections_by_time[0].connected_at.isoformat(),
                "duration": str(datetime.now() - connections_by_time[0].connected_at)
            }
            stats["newest_connection"] = {
                "client_id": connections_by_time[-1].client_id,
                "connected_at": connections_by_time[-1].connected_at.isoformat(),
                "duration": str(datetime.now() - connections_by_time[-1].connected_at)
            }
        
        return stats
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"已注册消息处理器: {message_type}")
    
    def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if client_id not in self.connections:
            return None
        
        connection = self.connections[client_id]
        return {
            "client_id": client_id,
            "connection_type": connection.connection_type,
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "is_active": connection.is_active,
            "metadata": connection.metadata
        }


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


# 便捷函数
async def get_websocket_manager() -> WebSocketManager:
    """获取WebSocket管理器实例"""
    return websocket_manager


async def broadcast_message(message: Dict[str, Any], exclude_client: Optional[str] = None) -> int:
    """广播消息的便捷函数"""
    return await websocket_manager.broadcast(message, exclude_client)


async def send_to_connection_type(connection_type: str, message: Dict[str, Any]) -> int:
    """向指定类型连接发送消息的便捷函数"""
    return await websocket_manager.send_to_type(connection_type, message)


def register_message_handler(message_type: str, handler: Callable):
    """注册消息处理器的便捷函数"""
    websocket_manager.register_message_handler(message_type, handler)