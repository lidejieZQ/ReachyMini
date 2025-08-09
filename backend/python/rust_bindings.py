#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rust绑定模块

提供Python与Rust后端模块的接口，包括视觉处理、实时控制、硬件管理和AI推理功能。
"""

import json
import logging
import threading
import time
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import reachy_mini_rust
    RUST_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Rust模块不可用: {e}")
    RUST_AVAILABLE = False
    reachy_mini_rust = None

logger = logging.getLogger(__name__)


@dataclass
class VisionConfig:
    """视觉处理配置"""
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps: float = 30.0
    buffer_size: int = 10
    enable_face_detection: bool = True
    enable_object_detection: bool = False
    enable_feature_detection: bool = False
    face_cascade_path: str = "data/haarcascade_frontalface_alt.xml"
    processing_threads: int = 2


@dataclass
class RealtimeConfig:
    """实时控制配置"""
    control_frequency: float = 100.0
    max_joint_velocity: float = 2.0
    max_joint_acceleration: float = 5.0
    position_tolerance: float = 0.01
    velocity_tolerance: float = 0.1
    enable_safety_limits: bool = True
    emergency_stop_enabled: bool = True
    sensor_update_rate: float = 200.0
    command_timeout_ms: int = 1000
    pid_gains: Dict[str, Dict[str, float]] = None
    joint_limits: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        if self.pid_gains is None:
            self.pid_gains = {
                "head_pan": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "head_tilt": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "left_shoulder_pitch": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "left_shoulder_roll": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "left_elbow_pitch": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "right_shoulder_pitch": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "right_shoulder_roll": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
                "right_elbow_pitch": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "max_integral": 10.0, "max_output": 100.0},
            }
        
        if self.joint_limits is None:
            self.joint_limits = {
                "head_pan": {"min_position": -90.0, "max_position": 90.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "head_tilt": {"min_position": -45.0, "max_position": 45.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "left_shoulder_pitch": {"min_position": -180.0, "max_position": 180.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "left_shoulder_roll": {"min_position": -90.0, "max_position": 90.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "left_elbow_pitch": {"min_position": 0.0, "max_position": 150.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "right_shoulder_pitch": {"min_position": -180.0, "max_position": 180.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "right_shoulder_roll": {"min_position": -90.0, "max_position": 90.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
                "right_elbow_pitch": {"min_position": 0.0, "max_position": 150.0, "max_velocity": 90.0, "max_acceleration": 180.0, "max_torque": 10.0},
            }


@dataclass
class HardwareConfig:
    """硬件配置"""
    serial_port: str = "/dev/ttyUSB0"
    serial_baudrate: int = 115200
    serial_timeout: float = 1.0
    i2c_bus: int = 1
    i2c_address: int = 0x48
    gpio_pins: Dict[str, int] = None
    sensor_update_rate: float = 100.0
    enable_watchdog: bool = True
    watchdog_timeout: float = 5.0

    def __post_init__(self):
        if self.gpio_pins is None:
            self.gpio_pins = {
                "led_status": 18,
                "button_emergency": 19,
                "relay_power": 20,
            }


@dataclass
class AIConfig:
    """AI配置"""
    model_path: str = "models/"
    device: str = "cpu"
    batch_size: int = 1
    max_workers: int = 2
    enable_face_detection: bool = True
    enable_object_detection: bool = True
    enable_pose_estimation: bool = False
    enable_scene_analysis: bool = False
    face_detection_threshold: float = 0.5
    object_detection_threshold: float = 0.5
    pose_estimation_threshold: float = 0.3


class RustVisionProcessor:
    """Rust视觉处理器包装类"""
    
    def __init__(self, config: VisionConfig):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust模块不可用")
        
        self.config = config
        config_json = json.dumps(asdict(config))
        self._processor = reachy_mini_rust.PyVisionProcessor(config_json)
        self._running = False
        
        logger.info("Rust视觉处理器初始化完成")
    
    def start(self) -> None:
        """启动视觉处理"""
        try:
            self._processor.start()
            self._running = True
            logger.info("视觉处理器启动成功")
        except Exception as e:
            logger.error(f"启动视觉处理器失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止视觉处理"""
        try:
            self._processor.stop()
            self._running = False
            logger.info("视觉处理器停止成功")
        except Exception as e:
            logger.error(f"停止视觉处理器失败: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        try:
            status_json = self._processor.get_status()
            return json.loads(status_json)
        except Exception as e:
            logger.error(f"获取视觉处理器状态失败: {e}")
            return {}
    
    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        """获取最新帧"""
        try:
            frame_json = self._processor.get_latest_frame()
            if frame_json:
                return json.loads(frame_json)
            return None
        except Exception as e:
            logger.error(f"获取最新帧失败: {e}")
            return None
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        try:
            return self._processor.is_running()
        except Exception as e:
            logger.error(f"检查运行状态失败: {e}")
            return False


class RustRealtimeController:
    """Rust实时控制器包装类"""
    
    def __init__(self, config: RealtimeConfig):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust模块不可用")
        
        self.config = config
        config_json = json.dumps(asdict(config))
        self._controller = reachy_mini_rust.PyRealtimeController(config_json)
        self._running = False
        
        logger.info("Rust实时控制器初始化完成")
    
    def start(self) -> None:
        """启动实时控制"""
        try:
            self._controller.start()
            self._running = True
            logger.info("实时控制器启动成功")
        except Exception as e:
            logger.error(f"启动实时控制器失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止实时控制"""
        try:
            self._controller.stop()
            self._running = False
            logger.info("实时控制器停止成功")
        except Exception as e:
            logger.error(f"停止实时控制器失败: {e}")
            raise
    
    def send_joint_command(self, joint_name: str, command: Dict[str, Any]) -> None:
        """发送关节命令"""
        try:
            command_json = json.dumps(command)
            self._controller.send_joint_command(joint_name, command_json)
        except Exception as e:
            logger.error(f"发送关节命令失败: {e}")
            raise
    
    def get_joint_state(self, joint_name: str) -> Optional[Dict[str, Any]]:
        """获取关节状态"""
        try:
            state_json = self._controller.get_joint_state(joint_name)
            if state_json:
                return json.loads(state_json)
            return None
        except Exception as e:
            logger.error(f"获取关节状态失败: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        try:
            status_json = self._controller.get_status()
            return json.loads(status_json)
        except Exception as e:
            logger.error(f"获取实时控制器状态失败: {e}")
            return {}
    
    def emergency_stop(self) -> None:
        """紧急停止"""
        try:
            self._controller.emergency_stop()
            logger.warning("执行紧急停止")
        except Exception as e:
            logger.error(f"紧急停止失败: {e}")
            raise


class RustHardwareManager:
    """Rust硬件管理器包装类"""
    
    def __init__(self, config: HardwareConfig):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust模块不可用")
        
        self.config = config
        config_json = json.dumps(asdict(config))
        self._manager = reachy_mini_rust.PyHardwareManager(config_json)
        self._running = False
        
        logger.info("Rust硬件管理器初始化完成")
    
    def start(self) -> None:
        """启动硬件管理"""
        try:
            self._manager.start()
            self._running = True
            logger.info("硬件管理器启动成功")
        except Exception as e:
            logger.error(f"启动硬件管理器失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止硬件管理"""
        try:
            self._manager.stop()
            self._running = False
            logger.info("硬件管理器停止成功")
        except Exception as e:
            logger.error(f"停止硬件管理器失败: {e}")
            raise
    
    def get_sensor_data(self, sensor_name: str) -> Optional[Dict[str, Any]]:
        """获取传感器数据"""
        try:
            data_json = self._manager.get_sensor_data(sensor_name)
            if data_json:
                return json.loads(data_json)
            return None
        except Exception as e:
            logger.error(f"获取传感器数据失败: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        try:
            status_json = self._manager.get_status()
            return json.loads(status_json)
        except Exception as e:
            logger.error(f"获取硬件管理器状态失败: {e}")
            return {}


class RustAIEngine:
    """Rust AI引擎包装类"""
    
    def __init__(self, config: AIConfig):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust模块不可用")
        
        self.config = config
        config_json = json.dumps(asdict(config))
        self._engine = reachy_mini_rust.PyAIEngine(config_json)
        self._running = False
        
        logger.info("Rust AI引擎初始化完成")
    
    def start(self) -> None:
        """启动AI引擎"""
        try:
            self._engine.start()
            self._running = True
            logger.info("AI引擎启动成功")
        except Exception as e:
            logger.error(f"启动AI引擎失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止AI引擎"""
        try:
            self._engine.stop()
            self._running = False
            logger.info("AI引擎停止成功")
        except Exception as e:
            logger.error(f"停止AI引擎失败: {e}")
            raise
    
    def inference(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """执行推理"""
        try:
            request_json = json.dumps(request)
            response_json = self._engine.inference(request_json)
            return json.loads(response_json)
        except Exception as e:
            logger.error(f"AI推理失败: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        try:
            status_json = self._engine.get_status()
            return json.loads(status_json)
        except Exception as e:
            logger.error(f"获取AI引擎状态失败: {e}")
            return {}


class RustReachyMiniSystem:
    """Rust完整系统包装类"""
    
    def __init__(self, 
                 vision_config: VisionConfig,
                 realtime_config: RealtimeConfig,
                 hardware_config: HardwareConfig,
                 ai_config: AIConfig):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust模块不可用")
        
        self.vision_config = vision_config
        self.realtime_config = realtime_config
        self.hardware_config = hardware_config
        self.ai_config = ai_config
        
        config = {
            "vision": asdict(vision_config),
            "realtime": asdict(realtime_config),
            "hardware": asdict(hardware_config),
            "ai": asdict(ai_config),
        }
        
        config_json = json.dumps(config)
        self._system = reachy_mini_rust.PyReachyMiniSystem("reachy_mini", "1.0.0")
        self._running = False
        
        logger.info("Rust完整系统初始化完成")
    
    def start(self) -> None:
        """启动系统"""
        try:
            self._system.start()
            self._running = True
            logger.info("Reachy Mini系统启动成功")
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止系统"""
        try:
            self._system.stop()
            self._running = False
            logger.info("Reachy Mini系统停止成功")
        except Exception as e:
            logger.error(f"停止系统失败: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status_json = self._system.get_status()
            return json.loads(status_json)
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {}
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        try:
            return self._system.is_running()
        except Exception as e:
            logger.error(f"检查运行状态失败: {e}")
            return False


class RustBindingsManager:
    """Rust绑定管理器"""
    
    def __init__(self):
        self._vision_processor: Optional[RustVisionProcessor] = None
        self._realtime_controller: Optional[RustRealtimeController] = None
        self._hardware_manager: Optional[RustHardwareManager] = None
        self._ai_engine: Optional[RustAIEngine] = None
        self._system: Optional[RustReachyMiniSystem] = None
        self._lock = threading.Lock()
        
        # 初始化Rust日志系统
        if RUST_AVAILABLE:
            try:
                reachy_mini_rust.init_logging()
                logger.info("Rust日志系统初始化完成")
            except Exception as e:
                logger.warning(f"Rust日志系统初始化失败: {e}")
    
    def create_vision_processor(self, config: VisionConfig) -> RustVisionProcessor:
        """创建视觉处理器"""
        with self._lock:
            if self._vision_processor is not None:
                logger.warning("视觉处理器已存在，将停止现有实例")
                self._vision_processor.stop()
            
            self._vision_processor = RustVisionProcessor(config)
            return self._vision_processor
    
    def create_realtime_controller(self, config: RealtimeConfig) -> RustRealtimeController:
        """创建实时控制器"""
        with self._lock:
            if self._realtime_controller is not None:
                logger.warning("实时控制器已存在，将停止现有实例")
                self._realtime_controller.stop()
            
            self._realtime_controller = RustRealtimeController(config)
            return self._realtime_controller
    
    def create_hardware_manager(self, config: HardwareConfig) -> RustHardwareManager:
        """创建硬件管理器"""
        with self._lock:
            if self._hardware_manager is not None:
                logger.warning("硬件管理器已存在，将停止现有实例")
                self._hardware_manager.stop()
            
            self._hardware_manager = RustHardwareManager(config)
            return self._hardware_manager
    
    def create_ai_engine(self, config: AIConfig) -> RustAIEngine:
        """创建AI引擎"""
        with self._lock:
            if self._ai_engine is not None:
                logger.warning("AI引擎已存在，将停止现有实例")
                self._ai_engine.stop()
            
            self._ai_engine = RustAIEngine(config)
            return self._ai_engine
    
    def create_system(self, 
                     vision_config: VisionConfig,
                     realtime_config: RealtimeConfig,
                     hardware_config: HardwareConfig,
                     ai_config: AIConfig) -> RustReachyMiniSystem:
        """创建完整系统"""
        with self._lock:
            if self._system is not None:
                logger.warning("系统已存在，将停止现有实例")
                self._system.stop()
            
            self._system = RustReachyMiniSystem(
                vision_config, realtime_config, hardware_config, ai_config
            )
            return self._system
    
    def cleanup(self) -> None:
        """清理所有资源"""
        with self._lock:
            if self._system:
                try:
                    self._system.stop()
                except Exception as e:
                    logger.error(f"停止系统失败: {e}")
                self._system = None
            
            if self._vision_processor:
                try:
                    self._vision_processor.stop()
                except Exception as e:
                    logger.error(f"停止视觉处理器失败: {e}")
                self._vision_processor = None
            
            if self._realtime_controller:
                try:
                    self._realtime_controller.stop()
                except Exception as e:
                    logger.error(f"停止实时控制器失败: {e}")
                self._realtime_controller = None
            
            if self._hardware_manager:
                try:
                    self._hardware_manager.stop()
                except Exception as e:
                    logger.error(f"停止硬件管理器失败: {e}")
                self._hardware_manager = None
            
            if self._ai_engine:
                try:
                    self._ai_engine.stop()
                except Exception as e:
                    logger.error(f"停止AI引擎失败: {e}")
                self._ai_engine = None
            
            logger.info("Rust绑定资源清理完成")
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        if not RUST_AVAILABLE:
            return {
                "rust_available": False,
                "error": "Rust模块不可用"
            }
        
        try:
            info_json = reachy_mini_rust.get_system_info()
            info = json.loads(info_json)
            info["rust_available"] = True
            return info
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {
                "rust_available": True,
                "error": str(e)
            }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        if not RUST_AVAILABLE:
            logger.warning("Rust模块不可用，跳过配置验证")
            return True
        
        try:
            config_json = json.dumps(config)
            return reachy_mini_rust.validate_config(config_json)
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False


# 全局实例
_rust_bindings_manager = None


def get_rust_bindings_manager() -> RustBindingsManager:
    """获取全局Rust绑定管理器实例"""
    global _rust_bindings_manager
    if _rust_bindings_manager is None:
        _rust_bindings_manager = RustBindingsManager()
    return _rust_bindings_manager


def cleanup_rust_bindings() -> None:
    """清理Rust绑定资源"""
    global _rust_bindings_manager
    if _rust_bindings_manager is not None:
        _rust_bindings_manager.cleanup()
        _rust_bindings_manager = None


# 便捷函数
def is_rust_available() -> bool:
    """检查Rust模块是否可用"""
    return RUST_AVAILABLE


def get_rust_system_info() -> Dict[str, Any]:
    """获取Rust系统信息"""
    manager = get_rust_bindings_manager()
    return manager.get_system_info()


def validate_rust_config(config: Dict[str, Any]) -> bool:
    """验证Rust配置"""
    manager = get_rust_bindings_manager()
    return manager.validate_config(config)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print(f"Rust模块可用: {is_rust_available()}")
    
    if is_rust_available():
        print("系统信息:")
        info = get_rust_system_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # 测试配置验证
        test_config = {
            "vision": asdict(VisionConfig()),
            "realtime": asdict(RealtimeConfig()),
            "hardware": asdict(HardwareConfig()),
            "ai": asdict(AIConfig()),
        }
        
        print(f"配置验证: {validate_rust_config(test_config)}")
        
        # 清理资源
        cleanup_rust_bindings()
    else:
        print("Rust模块不可用，请检查安装")