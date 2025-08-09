#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini 数据库模型

定义应用程序的数据库模型，包括：
- 用户管理
- 机器人状态
- 任务管理
- 传感器数据
- 系统日志
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# 创建基础模型类
Base = declarative_base()


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    """UUID混入类"""
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


# 枚举类定义
class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型"""
    MOTION = "motion"
    VISION = "vision"
    INTERACTION = "interaction"
    MAINTENANCE = "maintenance"
    CALIBRATION = "calibration"


class RobotStatus(str, Enum):
    """机器人状态"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    EMERGENCY_STOP = "emergency_stop"


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# 用户管理模型
class User(Base, UUIDMixin, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # 用户偏好设置
    preferences = Column(JSON, nullable=True)
    
    # 关系
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    @validates('role')
    def validate_role(self, key, role):
        if role not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role: {role}")
        return role
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class UserSession(Base, UUIDMixin, TimestampMixin):
    """用户会话模型"""
    __tablename__ = "user_sessions"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # 关系
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(user_id='{self.user_id}', expires_at='{self.expires_at}')>"


# 机器人状态模型
class RobotState(Base, UUIDMixin, TimestampMixin):
    """机器人状态模型"""
    __tablename__ = "robot_states"
    
    status = Column(String(20), nullable=False, default=RobotStatus.IDLE)
    battery_level = Column(Float, nullable=True)  # 电池电量 (0-100)
    temperature = Column(Float, nullable=True)  # 温度 (摄氏度)
    cpu_usage = Column(Float, nullable=True)  # CPU使用率 (0-100)
    memory_usage = Column(Float, nullable=True)  # 内存使用率 (0-100)
    
    # 关节状态
    joint_positions = Column(JSON, nullable=True)  # 关节位置
    joint_velocities = Column(JSON, nullable=True)  # 关节速度
    joint_efforts = Column(JSON, nullable=True)  # 关节力矩
    joint_temperatures = Column(JSON, nullable=True)  # 关节温度
    
    # 传感器数据
    imu_data = Column(JSON, nullable=True)  # IMU数据
    force_torque_data = Column(JSON, nullable=True)  # 力/扭矩传感器数据
    
    # 错误信息
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 运行时间统计
    uptime_seconds = Column(Integer, default=0, nullable=False)
    
    @validates('status')
    def validate_status(self, key, status):
        if status not in [s.value for s in RobotStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status
    
    def __repr__(self):
        return f"<RobotState(status='{self.status}', battery='{self.battery_level}%')>"


# 任务管理模型
class Task(Base, UUIDMixin, TimestampMixin):
    """任务模型"""
    __tablename__ = "tasks"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Integer, default=0, nullable=False)  # 优先级，数字越大优先级越高
    
    # 任务参数
    parameters = Column(JSON, nullable=True)
    
    # 执行信息
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Float, default=0.0, nullable=False)  # 进度 (0-100)
    
    # 结果和错误信息
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 用户关联
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # 关系
    user = relationship("User", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    
    # 约束
    __table_args__ = (
        CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range'),
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_user_created', 'user_id', 'created_at'),
    )
    
    @validates('task_type')
    def validate_task_type(self, key, task_type):
        if task_type not in [t.value for t in TaskType]:
            raise ValueError(f"Invalid task type: {task_type}")
        return task_type
    
    @validates('status')
    def validate_status(self, key, status):
        if status not in [s.value for s in TaskStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status
    
    def __repr__(self):
        return f"<Task(name='{self.name}', status='{self.status}', progress={self.progress}%)>"


class TaskLog(Base, UUIDMixin, TimestampMixin):
    """任务日志模型"""
    __tablename__ = "task_logs"
    
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    level = Column(String(10), nullable=False, default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # 关系
    task = relationship("Task", back_populates="logs")
    
    # 索引
    __table_args__ = (
        Index('idx_task_log_task_created', 'task_id', 'created_at'),
        Index('idx_task_log_level', 'level'),
    )
    
    @validates('level')
    def validate_level(self, key, level):
        if level not in [l.value for l in LogLevel]:
            raise ValueError(f"Invalid log level: {level}")
        return level
    
    def __repr__(self):
        return f"<TaskLog(task_id='{self.task_id}', level='{self.level}')>"


# 传感器数据模型
class SensorData(Base, UUIDMixin, TimestampMixin):
    """传感器数据模型"""
    __tablename__ = "sensor_data"
    
    sensor_type = Column(String(50), nullable=False)  # 传感器类型
    sensor_id = Column(String(50), nullable=False)  # 传感器ID
    
    # 数据
    data = Column(JSON, nullable=False)  # 传感器数据
    quality = Column(Float, nullable=True)  # 数据质量 (0-1)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_sensor_type_id_created', 'sensor_type', 'sensor_id', 'created_at'),
        Index('idx_sensor_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SensorData(type='{self.sensor_type}', id='{self.sensor_id}')>"


# 系统日志模型
class SystemLog(Base, UUIDMixin, TimestampMixin):
    """系统日志模型"""
    __tablename__ = "system_logs"
    
    level = Column(String(10), nullable=False)
    logger_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    
    # 上下文信息
    module = Column(String(100), nullable=True)
    function = Column(String(100), nullable=True)
    line_number = Column(Integer, nullable=True)
    
    # 额外数据
    extra_data = Column(JSON, nullable=True)
    
    # 用户关联（可选）
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_system_log_level_created', 'level', 'created_at'),
        Index('idx_system_log_logger_created', 'logger_name', 'created_at'),
        Index('idx_system_log_user_created', 'user_id', 'created_at'),
    )
    
    @validates('level')
    def validate_level(self, key, level):
        if level not in [l.value for l in LogLevel]:
            raise ValueError(f"Invalid log level: {level}")
        return level
    
    def __repr__(self):
        return f"<SystemLog(level='{self.level}', logger='{self.logger_name}')>"


# 配置存储模型
class Configuration(Base, UUIDMixin, TimestampMixin):
    """配置存储模型"""
    __tablename__ = "configurations"
    
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # 是否为系统配置
    
    # 版本控制
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Configuration(key='{self.key}', version={self.version})>"


# 文件存储模型
class FileStorage(Base, UUIDMixin, TimestampMixin):
    """文件存储模型"""
    __tablename__ = "file_storage"
    
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # 文件哈希（用于去重）
    file_hash = Column(String(64), nullable=True, index=True)
    
    # 关联信息
    related_type = Column(String(50), nullable=True)  # 关联的对象类型
    related_id = Column(String(36), nullable=True)  # 关联的对象ID
    
    # 用户关联
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_file_hash', 'file_hash'),
        Index('idx_file_related', 'related_type', 'related_id'),
        Index('idx_file_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<FileStorage(filename='{self.filename}', size={self.file_size})>"


# 性能监控模型
class PerformanceMetric(Base, UUIDMixin, TimestampMixin):
    """性能指标模型"""
    __tablename__ = "performance_metrics"
    
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)
    
    # 标签（用于分组和过滤）
    tags = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_metric_name_created', 'metric_name', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PerformanceMetric(name='{self.metric_name}', value={self.metric_value})>"


# 数据库工具函数
def create_all_tables(engine):
    """创建所有表"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine):
    """删除所有表"""
    Base.metadata.drop_all(bind=engine)


def get_table_names():
    """获取所有表名"""
    return list(Base.metadata.tables.keys())


if __name__ == "__main__":
    # 打印所有表信息
    print("Reachy Mini Database Models:")
    print("=" * 40)
    
    for table_name in get_table_names():
        table = Base.metadata.tables[table_name]
        print(f"\nTable: {table_name}")
        print(f"Columns: {len(table.columns)}")
        for column in table.columns:
            print(f"  - {column.name}: {column.type}")
    
    print(f"\nTotal tables: {len(Base.metadata.tables)}")