#!/usr/bin/env python3
"""
机器人控制API路由
提供机器人控制的REST API接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.robot_service import robot_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/robot", tags=["robot"])


# 请求模型
class HeadMoveRequest(BaseModel):
    """头部运动请求"""
    pan: float = Field(..., ge=-90, le=90, description="水平角度（度）")
    tilt: float = Field(..., ge=-45, le=45, description="垂直角度（度）")
    speed: float = Field(10.0, gt=0, le=30, description="运动速度（度/秒）")


class BodyMoveRequest(BaseModel):
    """身体运动请求"""
    x: float = Field(..., ge=-0.5, le=0.5, description="X轴位置（米）")
    y: float = Field(..., ge=-0.5, le=0.5, description="Y轴位置（米）")
    z: float = Field(..., ge=0.0, le=0.3, description="Z轴位置（米）")
    speed: float = Field(0.05, gt=0, le=0.1, description="运动速度（米/秒）")


class LEDColorRequest(BaseModel):
    """LED颜色设置请求"""
    color: str = Field(..., regex=r'^#[0-9A-Fa-f]{6}$|^(red|green|blue|yellow|purple|cyan|white|off)$', 
                      description="颜色值（十六进制或预定义颜色名）")


class RobotCommandRequest(BaseModel):
    """通用机器人命令请求"""
    command: str = Field(..., description="命令类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="命令参数")


# 响应模型
class RobotStatusResponse(BaseModel):
    """机器人状态响应"""
    connected: bool
    head_position: Dict[str, float]
    body_position: Dict[str, float]
    battery_level: float
    temperature: float
    error_messages: List[str]
    last_update: str


class CommandResponse(BaseModel):
    """命令执行响应"""
    success: bool
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None


@router.get("/status", response_model=RobotStatusResponse)
async def get_robot_status():
    """获取机器人状态"""
    try:
        robot_state = await robot_service.get_robot_state()
        
        return RobotStatusResponse(
            connected=robot_state.connected,
            head_position=robot_state.head_position,
            body_position=robot_state.body_position,
            battery_level=robot_state.battery_level,
            temperature=robot_state.temperature,
            error_messages=robot_state.error_messages,
            last_update=robot_state.last_update.isoformat()
        )
        
    except Exception as e:
        logger.error(f"获取机器人状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect", response_model=CommandResponse)
async def connect_robot():
    """连接机器人"""
    try:
        success = await robot_service.connect()
        
        return CommandResponse(
            success=success,
            message="机器人连接成功" if success else "机器人连接失败",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"连接机器人失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect", response_model=CommandResponse)
async def disconnect_robot():
    """断开机器人连接"""
    try:
        await robot_service.disconnect()
        
        return CommandResponse(
            success=True,
            message="机器人连接已断开",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"断开机器人连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/head/move", response_model=CommandResponse)
async def move_head(request: HeadMoveRequest):
    """控制头部运动"""
    try:
        success = await robot_service.move_head(
            pan=request.pan,
            tilt=request.tilt,
            speed=request.speed
        )
        
        return CommandResponse(
            success=success,
            message=f"头部运动命令{'成功' if success else '失败'}",
            timestamp=datetime.now().isoformat(),
            data={
                "pan": request.pan,
                "tilt": request.tilt,
                "speed": request.speed
            }
        )
        
    except Exception as e:
        logger.error(f"头部运动控制失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/body/move", response_model=CommandResponse)
async def move_body(request: BodyMoveRequest):
    """控制身体运动"""
    try:
        success = await robot_service.move_body(
            x=request.x,
            y=request.y,
            z=request.z,
            speed=request.speed
        )
        
        return CommandResponse(
            success=success,
            message=f"身体运动命令{'成功' if success else '失败'}",
            timestamp=datetime.now().isoformat(),
            data={
                "x": request.x,
                "y": request.y,
                "z": request.z,
                "speed": request.speed
            }
        )
        
    except Exception as e:
        logger.error(f"身体运动控制失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=CommandResponse)
async def stop_all_movement():
    """停止所有运动"""
    try:
        success = await robot_service.stop_all_movement()
        
        return CommandResponse(
            success=success,
            message=f"停止运动命令{'成功' if success else '失败'}",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"停止运动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/led/color", response_model=CommandResponse)
async def set_led_color(request: LEDColorRequest):
    """设置LED颜色"""
    try:
        success = await robot_service.set_led_color(request.color)
        
        return CommandResponse(
            success=success,
            message=f"LED颜色设置{'成功' if success else '失败'}",
            timestamp=datetime.now().isoformat(),
            data={"color": request.color}
        )
        
    except Exception as e:
        logger.error(f"设置LED颜色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibrate", response_model=CommandResponse)
async def calibrate_robot(background_tasks: BackgroundTasks):
    """校准机器人"""
    try:
        # 校准是一个耗时操作，放到后台任务中执行
        background_tasks.add_task(robot_service.calibrate)
        
        return CommandResponse(
            success=True,
            message="机器人校准已开始，请等待完成",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"启动机器人校准失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command", response_model=CommandResponse)
async def execute_robot_command(request: RobotCommandRequest):
    """执行通用机器人命令"""
    try:
        command = request.command.lower()
        parameters = request.parameters
        
        if command == "move_head":
            success = await robot_service.move_head(
                pan=parameters.get("pan", 0),
                tilt=parameters.get("tilt", 0),
                speed=parameters.get("speed", 10)
            )
        elif command == "move_body":
            success = await robot_service.move_body(
                x=parameters.get("x", 0),
                y=parameters.get("y", 0),
                z=parameters.get("z", 0),
                speed=parameters.get("speed", 0.05)
            )
        elif command == "stop":
            success = await robot_service.stop_all_movement()
        elif command == "set_led":
            success = await robot_service.set_led_color(parameters.get("color", "white"))
        elif command == "calibrate":
            success = await robot_service.calibrate()
        else:
            raise HTTPException(status_code=400, detail=f"未知命令: {command}")
        
        return CommandResponse(
            success=success,
            message=f"命令 {command} {'执行成功' if success else '执行失败'}",
            timestamp=datetime.now().isoformat(),
            data={"command": command, "parameters": parameters}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行机器人命令失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limits")
async def get_robot_limits():
    """获取机器人运动限制"""
    try:
        limits = {
            "head": {
                "pan": {"min": -90, "max": 90, "unit": "degrees"},
                "tilt": {"min": -45, "max": 45, "unit": "degrees"},
                "max_speed": {"value": 30, "unit": "degrees/second"}
            },
            "body": {
                "x": {"min": -0.5, "max": 0.5, "unit": "meters"},
                "y": {"min": -0.5, "max": 0.5, "unit": "meters"},
                "z": {"min": 0.0, "max": 0.3, "unit": "meters"},
                "max_speed": {"value": 0.1, "unit": "meters/second"}
            },
            "led_colors": [
                "red", "green", "blue", "yellow", "purple", "cyan", "white", "off"
            ]
        }
        
        return JSONResponse(content=limits)
        
    except Exception as e:
        logger.error(f"获取机器人限制失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def robot_health_check():
    """机器人健康检查"""
    try:
        robot_state = await robot_service.get_robot_state()
        
        health_status = {
            "status": "healthy" if robot_state.connected else "disconnected",
            "connected": robot_state.connected,
            "battery_level": robot_state.battery_level,
            "temperature": robot_state.temperature,
            "error_count": len(robot_state.error_messages),
            "last_update": robot_state.last_update.isoformat(),
            "checks": {
                "connection": robot_state.connected,
                "battery_ok": robot_state.battery_level > 20,
                "temperature_ok": robot_state.temperature < 40,
                "no_errors": len(robot_state.error_messages) == 0
            }
        }
        
        # 根据健康状态设置HTTP状态码
        status_code = 200 if all(health_status["checks"].values()) else 503
        
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"机器人健康检查失败: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )