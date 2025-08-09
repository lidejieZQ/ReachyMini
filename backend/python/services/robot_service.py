#!/usr/bin/env python3
"""
机器人控制服务
负责与Reachy Mini机器人的通信和控制
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass

from core.config import get_config
from utils.logger import setup_logger

# 获取配置
config = get_config()

logger = setup_logger(__name__)


@dataclass
class RobotState:
    """机器人状态数据类"""
    connected: bool = False
    head_position: Dict[str, float] = None
    body_position: Dict[str, float] = None
    battery_level: float = 0.0
    temperature: float = 0.0
    error_messages: List[str] = None
    last_update: datetime = None
    
    def __post_init__(self):
        if self.head_position is None:
            self.head_position = {"pan": 0.0, "tilt": 0.0}
        if self.body_position is None:
            self.body_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        if self.error_messages is None:
            self.error_messages = []
        if self.last_update is None:
            self.last_update = datetime.now()


class RobotService:
    """机器人控制服务"""
    
    def __init__(self):
        self.robot_state = RobotState()
        self.is_connected = False
        self.reachy_sdk = None
        self.connection_lock = asyncio.Lock()
        
        # 运动限制
        self.head_limits = {
            "pan": (-90, 90),    # 度
            "tilt": (-45, 45)    # 度
        }
        
        self.body_limits = {
            "x": (-0.5, 0.5),   # 米
            "y": (-0.5, 0.5),   # 米
            "z": (0.0, 0.3)     # 米
        }
        
        # 运动速度限制
        self.max_speed = {
            "head": 30,  # 度/秒
            "body": 0.1  # 米/秒
        }
        
        # 状态更新任务
        self.status_update_task = None
        self.status_update_interval = 0.1  # 100ms
        
    async def initialize(self) -> bool:
        """初始化机器人服务"""
        try:
            logger.info("正在初始化机器人服务...")
            
            # 在实际环境中，这里会初始化Reachy SDK
            # from reachy_sdk import ReachySDK
            # self.reachy_sdk = ReachySDK(host=settings.REACHY_HOST)
            
            # 模拟连接
            await self._simulate_connection()
            
            # 启动状态更新任务
            self.status_update_task = asyncio.create_task(self._status_update_loop())
            
            logger.info("机器人服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"机器人服务初始化失败: {e}")
            return False
    
    async def _simulate_connection(self):
        """模拟机器人连接（用于开发测试）"""
        try:
            # 模拟连接延迟
            await asyncio.sleep(1)
            
            self.is_connected = True
            self.robot_state.connected = True
            self.robot_state.battery_level = 85.0
            self.robot_state.temperature = 35.2
            
            logger.info("机器人连接模拟成功")
            
        except Exception as e:
            logger.error(f"机器人连接模拟失败: {e}")
            raise
    
    async def connect(self) -> bool:
        """连接到机器人"""
        async with self.connection_lock:
            try:
                if self.is_connected:
                    logger.info("机器人已经连接")
                    return True
                
                logger.info(f"正在连接到机器人: {settings.REACHY_HOST}:{settings.REACHY_PORT}")
                
                # 实际连接代码
                # if self.reachy_sdk:
                #     await self.reachy_sdk.connect()
                #     self.is_connected = True
                #     self.robot_state.connected = True
                
                # 模拟连接
                await self._simulate_connection()
                
                logger.info("机器人连接成功")
                return True
                
            except Exception as e:
                logger.error(f"机器人连接失败: {e}")
                self.is_connected = False
                self.robot_state.connected = False
                return False
    
    async def disconnect(self):
        """断开机器人连接"""
        async with self.connection_lock:
            try:
                if not self.is_connected:
                    return
                
                logger.info("正在断开机器人连接...")
                
                # 实际断开代码
                # if self.reachy_sdk:
                #     await self.reachy_sdk.disconnect()
                
                self.is_connected = False
                self.robot_state.connected = False
                
                logger.info("机器人连接已断开")
                
            except Exception as e:
                logger.error(f"断开机器人连接时出错: {e}")
    
    async def move_head(self, pan: float, tilt: float, speed: float = 10.0) -> bool:
        """控制头部运动"""
        try:
            if not self.is_connected:
                raise Exception("机器人未连接")
            
            # 检查运动限制
            pan = self._clamp_value(pan, *self.head_limits["pan"])
            tilt = self._clamp_value(tilt, *self.head_limits["tilt"])
            speed = min(speed, self.max_speed["head"])
            
            logger.info(f"头部运动: pan={pan:.2f}°, tilt={tilt:.2f}°, speed={speed:.2f}°/s")
            
            # 实际控制代码
            # if self.reachy_sdk:
            #     await self.reachy_sdk.head.look_at(pan, tilt, speed)
            
            # 模拟运动
            await self._simulate_head_movement(pan, tilt, speed)
            
            return True
            
        except Exception as e:
            logger.error(f"头部运动控制失败: {e}")
            return False
    
    async def move_body(self, x: float, y: float, z: float, speed: float = 0.05) -> bool:
        """控制身体运动"""
        try:
            if not self.is_connected:
                raise Exception("机器人未连接")
            
            # 检查运动限制
            x = self._clamp_value(x, *self.body_limits["x"])
            y = self._clamp_value(y, *self.body_limits["y"])
            z = self._clamp_value(z, *self.body_limits["z"])
            speed = min(speed, self.max_speed["body"])
            
            logger.info(f"身体运动: x={x:.3f}m, y={y:.3f}m, z={z:.3f}m, speed={speed:.3f}m/s")
            
            # 实际控制代码
            # if self.reachy_sdk:
            #     await self.reachy_sdk.body.move_to(x, y, z, speed)
            
            # 模拟运动
            await self._simulate_body_movement(x, y, z, speed)
            
            return True
            
        except Exception as e:
            logger.error(f"身体运动控制失败: {e}")
            return False
    
    async def stop_all_movement(self) -> bool:
        """停止所有运动"""
        try:
            if not self.is_connected:
                raise Exception("机器人未连接")
            
            logger.info("停止所有运动")
            
            # 实际停止代码
            # if self.reachy_sdk:
            #     await self.reachy_sdk.stop_all()
            
            # 模拟停止
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"停止运动失败: {e}")
            return False
    
    async def get_robot_state(self) -> RobotState:
        """获取机器人状态"""
        return self.robot_state
    
    async def set_led_color(self, color: str) -> bool:
        """设置LED颜色"""
        try:
            if not self.is_connected:
                raise Exception("机器人未连接")
            
            logger.info(f"设置LED颜色: {color}")
            
            # 实际LED控制代码
            # if self.reachy_sdk:
            #     await self.reachy_sdk.led.set_color(color)
            
            # 模拟设置
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"设置LED颜色失败: {e}")
            return False
    
    async def calibrate(self) -> bool:
        """校准机器人"""
        try:
            if not self.is_connected:
                raise Exception("机器人未连接")
            
            logger.info("开始机器人校准...")
            
            # 实际校准代码
            # if self.reachy_sdk:
            #     await self.reachy_sdk.calibrate()
            
            # 模拟校准
            await asyncio.sleep(3)
            
            # 重置位置
            self.robot_state.head_position = {"pan": 0.0, "tilt": 0.0}
            self.robot_state.body_position = {"x": 0.0, "y": 0.0, "z": 0.0}
            
            logger.info("机器人校准完成")
            return True
            
        except Exception as e:
            logger.error(f"机器人校准失败: {e}")
            return False
    
    def _clamp_value(self, value: float, min_val: float, max_val: float) -> float:
        """限制数值范围"""
        return max(min_val, min(max_val, value))
    
    async def _simulate_head_movement(self, pan: float, tilt: float, speed: float):
        """模拟头部运动"""
        # 计算运动时间
        current_pan = self.robot_state.head_position["pan"]
        current_tilt = self.robot_state.head_position["tilt"]
        
        pan_diff = abs(pan - current_pan)
        tilt_diff = abs(tilt - current_tilt)
        max_diff = max(pan_diff, tilt_diff)
        
        movement_time = max_diff / speed if speed > 0 else 0.1
        
        # 模拟渐进运动
        steps = max(1, int(movement_time / 0.05))  # 50ms步长
        
        for i in range(steps + 1):
            progress = i / steps
            current_pan_sim = current_pan + (pan - current_pan) * progress
            current_tilt_sim = current_tilt + (tilt - current_tilt) * progress
            
            self.robot_state.head_position["pan"] = current_pan_sim
            self.robot_state.head_position["tilt"] = current_tilt_sim
            self.robot_state.last_update = datetime.now()
            
            if i < steps:
                await asyncio.sleep(0.05)
    
    async def _simulate_body_movement(self, x: float, y: float, z: float, speed: float):
        """模拟身体运动"""
        # 计算运动时间
        current_x = self.robot_state.body_position["x"]
        current_y = self.robot_state.body_position["y"]
        current_z = self.robot_state.body_position["z"]
        
        distance = np.sqrt((x - current_x)**2 + (y - current_y)**2 + (z - current_z)**2)
        movement_time = distance / speed if speed > 0 else 0.1
        
        # 模拟渐进运动
        steps = max(1, int(movement_time / 0.05))  # 50ms步长
        
        for i in range(steps + 1):
            progress = i / steps
            current_x_sim = current_x + (x - current_x) * progress
            current_y_sim = current_y + (y - current_y) * progress
            current_z_sim = current_z + (z - current_z) * progress
            
            self.robot_state.body_position["x"] = current_x_sim
            self.robot_state.body_position["y"] = current_y_sim
            self.robot_state.body_position["z"] = current_z_sim
            self.robot_state.last_update = datetime.now()
            
            if i < steps:
                await asyncio.sleep(0.05)
    
    async def _status_update_loop(self):
        """状态更新循环"""
        while True:
            try:
                if self.is_connected:
                    # 模拟状态更新
                    self.robot_state.last_update = datetime.now()
                    
                    # 模拟电池电量缓慢下降
                    if self.robot_state.battery_level > 0:
                        self.robot_state.battery_level -= 0.001
                    
                    # 模拟温度波动
                    self.robot_state.temperature += np.random.normal(0, 0.1)
                    self.robot_state.temperature = self._clamp_value(
                        self.robot_state.temperature, 30.0, 45.0
                    )
                
                await asyncio.sleep(self.status_update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"状态更新循环出错: {e}")
                await asyncio.sleep(1)
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 取消状态更新任务
            if self.status_update_task and not self.status_update_task.done():
                self.status_update_task.cancel()
                try:
                    await self.status_update_task
                except asyncio.CancelledError:
                    pass
            
            # 断开机器人连接
            await self.disconnect()
            
            logger.info("机器人服务清理完成")
            
        except Exception as e:
            logger.error(f"机器人服务清理时出错: {e}")


# 全局机器人服务实例
robot_service = RobotService()