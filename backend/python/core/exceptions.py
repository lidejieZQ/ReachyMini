#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini 异常处理模块

定义应用程序的自定义异常类和全局异常处理器，包括：
- 基础异常类
- 业务逻辑异常
- API异常
- 数据库异常
- 硬件异常
- 全局异常处理器
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from enum import Enum

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

# 配置日志
logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """错误代码枚举"""
    # 通用错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    
    # 数据库错误
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_CONSTRAINT_ERROR = "DATABASE_CONSTRAINT_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"
    
    # 机器人硬件错误
    ROBOT_CONNECTION_ERROR = "ROBOT_CONNECTION_ERROR"
    ROBOT_COMMUNICATION_ERROR = "ROBOT_COMMUNICATION_ERROR"
    ROBOT_HARDWARE_ERROR = "ROBOT_HARDWARE_ERROR"
    ROBOT_SAFETY_ERROR = "ROBOT_SAFETY_ERROR"
    ROBOT_CALIBRATION_ERROR = "ROBOT_CALIBRATION_ERROR"
    
    # AI服务错误
    AI_MODEL_ERROR = "AI_MODEL_ERROR"
    AI_INFERENCE_ERROR = "AI_INFERENCE_ERROR"
    AI_MODEL_NOT_FOUND = "AI_MODEL_NOT_FOUND"
    AI_PROCESSING_ERROR = "AI_PROCESSING_ERROR"
    
    # 视频流错误
    STREAM_CONNECTION_ERROR = "STREAM_CONNECTION_ERROR"
    STREAM_ENCODING_ERROR = "STREAM_ENCODING_ERROR"
    STREAM_DEVICE_ERROR = "STREAM_DEVICE_ERROR"
    STREAM_BUFFER_ERROR = "STREAM_BUFFER_ERROR"
    
    # 任务管理错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_EXECUTION_ERROR = "TASK_EXECUTION_ERROR"
    TASK_TIMEOUT_ERROR = "TASK_TIMEOUT_ERROR"
    TASK_CANCELLED_ERROR = "TASK_CANCELLED_ERROR"
    
    # 配置错误
    CONFIG_ERROR = "CONFIG_ERROR"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"
    
    # 文件操作错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PERMISSION_ERROR = "FILE_PERMISSION_ERROR"
    FILE_SIZE_ERROR = "FILE_SIZE_ERROR"
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"


class BaseReachyException(Exception):
    """Reachy Mini 基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details
        }
        
        if self.cause:
            result["cause"] = str(self.cause)
        
        return result
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code='{self.error_code.value}', message='{self.message}')"


# API相关异常
class APIException(BaseReachyException):
    """API异常基类"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(message, error_code, details)
        self.status_code = status_code
        self.headers = headers or {}


class ValidationException(APIException):
    """验证异常"""
    
    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None):
        details = {"field_errors": field_errors} if field_errors else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details
        )


class AuthenticationException(APIException):
    """认证异常"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(APIException):
    """授权异常"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.AUTHORIZATION_ERROR
        )


class NotFoundException(APIException):
    """资源未找到异常"""
    
    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND_ERROR,
            details={"resource": resource, "identifier": identifier}
        )


class ConflictException(APIException):
    """资源冲突异常"""
    
    def __init__(self, message: str, resource: str = ""):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT_ERROR,
            details={"resource": resource} if resource else {}
        )


class RateLimitException(APIException):
    """限流异常"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_ERROR,
            headers=headers
        )


# 数据库相关异常
class DatabaseException(BaseReachyException):
    """数据库异常基类"""
    pass


class DatabaseConnectionException(DatabaseException):
    """数据库连接异常"""
    
    def __init__(self, message: str = "Database connection failed", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
            cause=cause
        )


class DatabaseQueryException(DatabaseException):
    """数据库查询异常"""
    
    def __init__(self, message: str, query: str = "", cause: Optional[Exception] = None):
        details = {"query": query} if query else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_QUERY_ERROR,
            details=details,
            cause=cause
        )


class DatabaseConstraintException(DatabaseException):
    """数据库约束异常"""
    
    def __init__(self, message: str, constraint: str = "", cause: Optional[Exception] = None):
        details = {"constraint": constraint} if constraint else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_CONSTRAINT_ERROR,
            details=details,
            cause=cause
        )


# 机器人硬件相关异常
class RobotException(BaseReachyException):
    """机器人异常基类"""
    pass


class RobotConnectionException(RobotException):
    """机器人连接异常"""
    
    def __init__(self, message: str = "Robot connection failed", device: str = ""):
        details = {"device": device} if device else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.ROBOT_CONNECTION_ERROR,
            details=details
        )


class RobotCommunicationException(RobotException):
    """机器人通信异常"""
    
    def __init__(self, message: str, command: str = "", response: str = ""):
        details = {}
        if command:
            details["command"] = command
        if response:
            details["response"] = response
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ROBOT_COMMUNICATION_ERROR,
            details=details
        )


class RobotHardwareException(RobotException):
    """机器人硬件异常"""
    
    def __init__(self, message: str, component: str = "", error_data: Optional[Dict] = None):
        details = {"component": component} if component else {}
        if error_data:
            details.update(error_data)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ROBOT_HARDWARE_ERROR,
            details=details
        )


class RobotSafetyException(RobotException):
    """机器人安全异常"""
    
    def __init__(self, message: str, safety_check: str = "", current_values: Optional[Dict] = None):
        details = {"safety_check": safety_check} if safety_check else {}
        if current_values:
            details["current_values"] = current_values
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ROBOT_SAFETY_ERROR,
            details=details
        )


# AI服务相关异常
class AIException(BaseReachyException):
    """AI服务异常基类"""
    pass


class AIModelException(AIException):
    """AI模型异常"""
    
    def __init__(self, message: str, model_name: str = "", model_path: str = ""):
        details = {}
        if model_name:
            details["model_name"] = model_name
        if model_path:
            details["model_path"] = model_path
        
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_MODEL_ERROR,
            details=details
        )


class AIInferenceException(AIException):
    """AI推理异常"""
    
    def __init__(self, message: str, input_shape: Optional[tuple] = None, model_name: str = ""):
        details = {}
        if input_shape:
            details["input_shape"] = input_shape
        if model_name:
            details["model_name"] = model_name
        
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_INFERENCE_ERROR,
            details=details
        )


# 视频流相关异常
class StreamException(BaseReachyException):
    """视频流异常基类"""
    pass


class StreamConnectionException(StreamException):
    """视频流连接异常"""
    
    def __init__(self, message: str, device_id: Union[int, str] = ""):
        details = {"device_id": str(device_id)} if device_id != "" else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.STREAM_CONNECTION_ERROR,
            details=details
        )


class StreamEncodingException(StreamException):
    """视频流编码异常"""
    
    def __init__(self, message: str, codec: str = "", resolution: str = ""):
        details = {}
        if codec:
            details["codec"] = codec
        if resolution:
            details["resolution"] = resolution
        
        super().__init__(
            message=message,
            error_code=ErrorCode.STREAM_ENCODING_ERROR,
            details=details
        )


# 任务管理相关异常
class TaskException(BaseReachyException):
    """任务异常基类"""
    pass


class TaskNotFoundException(TaskException):
    """任务未找到异常"""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            error_code=ErrorCode.TASK_NOT_FOUND,
            details={"task_id": task_id}
        )


class TaskExecutionException(TaskException):
    """任务执行异常"""
    
    def __init__(self, message: str, task_id: str = "", step: str = ""):
        details = {}
        if task_id:
            details["task_id"] = task_id
        if step:
            details["step"] = step
        
        super().__init__(
            message=message,
            error_code=ErrorCode.TASK_EXECUTION_ERROR,
            details=details
        )


class TaskTimeoutException(TaskException):
    """任务超时异常"""
    
    def __init__(self, message: str, task_id: str = "", timeout_seconds: Optional[int] = None):
        details = {}
        if task_id:
            details["task_id"] = task_id
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code=ErrorCode.TASK_TIMEOUT_ERROR,
            details=details
        )


# 配置相关异常
class ConfigException(BaseReachyException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str = "", config_value: Any = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = str(config_value)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_ERROR,
            details=details
        )


# 文件操作相关异常
class FileException(BaseReachyException):
    """文件操作异常基类"""
    pass


class FileNotFoundException(FileException):
    """文件未找到异常"""
    
    def __init__(self, file_path: str):
        super().__init__(
            message=f"File not found: {file_path}",
            error_code=ErrorCode.FILE_NOT_FOUND,
            details={"file_path": file_path}
        )


class FilePermissionException(FileException):
    """文件权限异常"""
    
    def __init__(self, message: str, file_path: str = "", operation: str = ""):
        details = {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_PERMISSION_ERROR,
            details=details
        )


# 全局异常处理器
class GlobalExceptionHandler:
    """全局异常处理器"""
    
    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> JSONResponse:
        """创建错误响应"""
        content = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": logger.handlers[0].formatter.formatTime(logging.LogRecord(
                    name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
                )) if logger.handlers else None
            }
        }
        
        if details:
            content["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers
        )
    
    @staticmethod
    async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
        """API异常处理器"""
        logger.error(f"API Exception: {exc}", exc_info=True)
        
        return GlobalExceptionHandler.create_error_response(
            error_code=exc.error_code.value,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            headers=exc.headers
        )
    
    @staticmethod
    async def base_reachy_exception_handler(request: Request, exc: BaseReachyException) -> JSONResponse:
        """基础Reachy异常处理器"""
        logger.error(f"Reachy Exception: {exc}", exc_info=True)
        
        return GlobalExceptionHandler.create_error_response(
            error_code=exc.error_code.value,
            message=exc.message,
            status_code=500,
            details=exc.details
        )
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """HTTP异常处理器"""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        
        return GlobalExceptionHandler.create_error_response(
            error_code="HTTP_ERROR",
            message=exc.detail,
            status_code=exc.status_code
        )
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """验证异常处理器"""
        logger.warning(f"Validation Exception: {exc}")
        
        # 提取字段错误信息
        field_errors = {}
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error["loc"])
            field_errors[field_name] = error["msg"]
        
        return GlobalExceptionHandler.create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Validation failed",
            status_code=422,
            details={"field_errors": field_errors}
        )
    
    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """通用异常处理器"""
        logger.error(f"Unhandled Exception: {exc}", exc_info=True)
        
        # 在开发环境中包含详细的错误信息
        details = None
        try:
            from .config import get_settings
            settings = get_settings()
            if settings.DEBUG:
                details = {
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc()
                }
        except Exception:
            pass
        
        return GlobalExceptionHandler.create_error_response(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR.value,
            message="Internal server error",
            status_code=500,
            details=details
        )


# 异常处理器注册函数
def register_exception_handlers(app):
    """注册异常处理器到FastAPI应用"""
    app.add_exception_handler(APIException, GlobalExceptionHandler.api_exception_handler)
    app.add_exception_handler(BaseReachyException, GlobalExceptionHandler.base_reachy_exception_handler)
    app.add_exception_handler(HTTPException, GlobalExceptionHandler.http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, GlobalExceptionHandler.http_exception_handler)
    app.add_exception_handler(RequestValidationError, GlobalExceptionHandler.validation_exception_handler)
    app.add_exception_handler(Exception, GlobalExceptionHandler.general_exception_handler)
    
    logger.info("Exception handlers registered")


if __name__ == "__main__":
    # 测试异常类
    print("Testing Reachy Mini Exception Classes:")
    print("=" * 50)
    
    # 测试基础异常
    try:
        raise BaseReachyException(
            "Test base exception",
            ErrorCode.UNKNOWN_ERROR,
            {"test_key": "test_value"}
        )
    except BaseReachyException as e:
        print(f"Base Exception: {e}")
        print(f"Dict: {e.to_dict()}")
    
    # 测试API异常
    try:
        raise ValidationException(
            "Test validation error",
            {"field1": "Required field", "field2": "Invalid format"}
        )
    except APIException as e:
        print(f"\nAPI Exception: {e}")
        print(f"Status Code: {e.status_code}")
        print(f"Dict: {e.to_dict()}")
    
    # 测试机器人异常
    try:
        raise RobotSafetyException(
            "Joint position out of range",
            "joint_position_check",
            {"joint_0": 3.5, "limit": 3.14}
        )
    except RobotException as e:
        print(f"\nRobot Exception: {e}")
        print(f"Dict: {e.to_dict()}")
    
    print("\n✅ Exception classes test completed")