#!/usr/bin/env python3
"""
日志工具模块
提供统一的日志配置和管理
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 获取原始格式化结果
        log_message = super().format(record)
        
        # 添加颜色
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            log_message = f"{color}{log_message}{self.RESET}"
        
        return log_message


class CustomLogger:
    """自定义日志管理器"""
    
    def __init__(self):
        self.loggers = {}
        self.log_dir = Path(settings.LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保日志目录存在
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """确保日志目录存在"""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建子目录
            (self.log_dir / "app").mkdir(exist_ok=True)
            (self.log_dir / "error").mkdir(exist_ok=True)
            (self.log_dir / "access").mkdir(exist_ok=True)
            (self.log_dir / "debug").mkdir(exist_ok=True)
            
        except Exception as e:
            print(f"创建日志目录失败: {e}")
    
    def get_logger(self, name: str, level: Optional[str] = None) -> logging.Logger:
        """获取或创建日志器"""
        if name in self.loggers:
            return self.loggers[name]
        
        # 创建新的日志器
        logger = logging.getLogger(name)
        
        # 设置日志级别
        log_level = getattr(logging, (level or settings.LOG_LEVEL).upper())
        logger.setLevel(log_level)
        
        # 避免重复添加处理器
        if not logger.handlers:
            self._setup_handlers(logger, name)
        
        # 防止日志传播到根日志器
        logger.propagate = False
        
        self.loggers[name] = logger
        return logger
    
    def _setup_handlers(self, logger: logging.Logger, name: str):
        """设置日志处理器"""
        # 控制台处理器
        if settings.LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            
            # 使用彩色格式化器
            console_formatter = ColoredFormatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 文件处理器
        if settings.LOG_TO_FILE:
            # 应用日志文件
            app_log_file = self.log_dir / "app" / f"{name}.log"
            app_handler = logging.handlers.RotatingFileHandler(
                app_log_file,
                maxBytes=settings.LOG_MAX_SIZE,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            app_handler.setLevel(logging.INFO)
            
            # 错误日志文件
            error_log_file = self.log_dir / "error" / f"{name}_error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=settings.LOG_MAX_SIZE,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            
            # 调试日志文件（仅在DEBUG模式下）
            if settings.LOG_LEVEL.upper() == 'DEBUG':
                debug_log_file = self.log_dir / "debug" / f"{name}_debug.log"
                debug_handler = logging.handlers.RotatingFileHandler(
                    debug_log_file,
                    maxBytes=settings.LOG_MAX_SIZE,
                    backupCount=settings.LOG_BACKUP_COUNT,
                    encoding='utf-8'
                )
                debug_handler.setLevel(logging.DEBUG)
                
                debug_formatter = logging.Formatter(
                    fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                debug_handler.setFormatter(debug_formatter)
                logger.addHandler(debug_handler)
            
            # 文件格式化器
            file_formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            app_handler.setFormatter(file_formatter)
            error_handler.setFormatter(file_formatter)
            
            logger.addHandler(app_handler)
            logger.addHandler(error_handler)
    
    def setup_access_logger(self) -> logging.Logger:
        """设置访问日志器"""
        access_logger = logging.getLogger("access")
        access_logger.setLevel(logging.INFO)
        
        if not access_logger.handlers:
            # 访问日志文件
            access_log_file = self.log_dir / "access" / "access.log"
            access_handler = logging.handlers.TimedRotatingFileHandler(
                access_log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            
            # 访问日志格式
            access_formatter = logging.Formatter(
                fmt='%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            access_handler.setFormatter(access_formatter)
            access_logger.addHandler(access_handler)
        
        access_logger.propagate = False
        return access_logger
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            for log_subdir in self.log_dir.iterdir():
                if log_subdir.is_dir():
                    for log_file in log_subdir.glob("*.log*"):
                        if log_file.stat().st_mtime < cutoff_time:
                            log_file.unlink()
                            print(f"删除旧日志文件: {log_file}")
            
        except Exception as e:
            print(f"清理旧日志文件失败: {e}")
    
    def get_log_stats(self) -> dict:
        """获取日志统计信息"""
        try:
            stats = {
                "log_directory": str(self.log_dir),
                "active_loggers": len(self.loggers),
                "logger_names": list(self.loggers.keys()),
                "log_files": {},
                "total_size": 0
            }
            
            # 统计各类日志文件
            for log_subdir in self.log_dir.iterdir():
                if log_subdir.is_dir():
                    subdir_files = []
                    subdir_size = 0
                    
                    for log_file in log_subdir.glob("*.log*"):
                        file_size = log_file.stat().st_size
                        subdir_files.append({
                            "name": log_file.name,
                            "size": file_size,
                            "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                        })
                        subdir_size += file_size
                    
                    stats["log_files"][log_subdir.name] = {
                        "files": subdir_files,
                        "count": len(subdir_files),
                        "total_size": subdir_size
                    }
                    stats["total_size"] += subdir_size
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}


# 全局日志管理器实例
_logger_manager = CustomLogger()


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """设置并获取日志器"""
    return _logger_manager.get_logger(name, level)


def get_access_logger() -> logging.Logger:
    """获取访问日志器"""
    return _logger_manager.setup_access_logger()


def cleanup_logs(days: int = 30):
    """清理旧日志"""
    _logger_manager.cleanup_old_logs(days)


def get_log_statistics() -> dict:
    """获取日志统计信息"""
    return _logger_manager.get_log_stats()


# 设置根日志器的默认配置
def configure_root_logger():
    """配置根日志器"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # 只显示警告及以上级别
    
    # 移除默认处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加简单的控制台处理器
    if settings.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


# 在模块加载时配置根日志器
configure_root_logger()


# 日志装饰器
def log_function_call(logger_name: str = None):
    """函数调用日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = setup_logger(logger_name or func.__module__)
            
            # 记录函数调用
            logger.debug(f"调用函数: {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"函数 {func.__name__} 执行成功")
                return result
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行失败: {e}")
                raise
        
        return wrapper
    return decorator


# 异步日志装饰器
def log_async_function_call(logger_name: str = None):
    """异步函数调用日志装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = setup_logger(logger_name or func.__module__)
            
            # 记录函数调用
            logger.debug(f"调用异步函数: {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"异步函数 {func.__name__} 执行成功")
                return result
            except Exception as e:
                logger.error(f"异步函数 {func.__name__} 执行失败: {e}")
                raise
        
        return wrapper
    return decorator