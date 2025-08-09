#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini 数据库管理模块

提供数据库连接、会话管理和基础操作功能，包括：
- 数据库引擎创建和配置
- 会话管理
- 连接池管理
- 数据库迁移
- 健康检查
"""

import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional, Dict, Any
from urllib.parse import urlparse

from sqlalchemy import (
    create_engine, event, pool, text, inspect
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from alembic import command, context
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from .config import get_settings
from .models import Base, create_all_tables, drop_all_tables

# 配置日志
logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: Optional[str] = None):
        """初始化数据库管理器"""
        self.settings = get_settings()
        self.database_url = database_url or self.settings.database.database_url
        self.engine: Optional[Engine] = None
        self.async_engine = None
        self.session_factory: Optional[sessionmaker] = None
        self.async_session_factory = None
        self._is_initialized = False
    
    def initialize(self) -> None:
        """初始化数据库连接"""
        if self._is_initialized:
            logger.warning("Database manager already initialized")
            return
        
        try:
            # 创建同步引擎
            self.engine = self._create_engine()
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # 创建异步引擎（如果支持）
            if self._supports_async():
                async_url = self._get_async_url()
                self.async_engine = create_async_engine(
                    async_url,
                    echo=self.settings.database.DB_ECHO,
                    pool_size=self.settings.database.DB_POOL_SIZE,
                    max_overflow=self.settings.database.DB_MAX_OVERFLOW,
                    pool_timeout=self.settings.database.DB_POOL_TIMEOUT,
                    pool_pre_ping=True,
                )
                self.async_session_factory = async_sessionmaker(
                    bind=self.async_engine,
                    class_=AsyncSession,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False
                )
            
            # 设置事件监听器
            self._setup_event_listeners()
            
            # 测试连接
            self._test_connection()
            
            self._is_initialized = True
            logger.info(f"Database manager initialized with URL: {self._mask_url(self.database_url)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    def _create_engine(self) -> Engine:
        """创建数据库引擎"""
        # 解析数据库URL
        parsed_url = urlparse(self.database_url)
        
        # 根据数据库类型配置引擎参数
        engine_kwargs = {
            "echo": self.settings.database.DB_ECHO,
            "echo_pool": self.settings.database.DB_ECHO_POOL,
            "pool_pre_ping": True,  # 启用连接预检查
        }
        
        # SQLite特殊配置
        if parsed_url.scheme.startswith('sqlite'):
            engine_kwargs.update({
                "poolclass": NullPool,  # SQLite不需要连接池
                "connect_args": {
                    "check_same_thread": False,  # 允许多线程访问
                    "timeout": 20,  # 设置超时时间
                }
            })
        else:
            # PostgreSQL/MySQL配置
            engine_kwargs.update({
                "poolclass": QueuePool,
                "pool_size": self.settings.database.DB_POOL_SIZE,
                "max_overflow": self.settings.database.DB_MAX_OVERFLOW,
                "pool_timeout": self.settings.database.DB_POOL_TIMEOUT,
                "pool_recycle": 3600,  # 1小时后回收连接
            })
        
        return create_engine(self.database_url, **engine_kwargs)
    
    def _supports_async(self) -> bool:
        """检查是否支持异步操作"""
        parsed_url = urlparse(self.database_url)
        # SQLite和PostgreSQL支持异步
        return parsed_url.scheme in ['sqlite', 'postgresql', 'postgresql+asyncpg']
    
    def _get_async_url(self) -> str:
        """获取异步数据库URL"""
        parsed_url = urlparse(self.database_url)
        
        if parsed_url.scheme == 'sqlite':
            return self.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
        elif parsed_url.scheme == 'postgresql':
            return self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
        
        return self.database_url
    
    def _setup_event_listeners(self) -> None:
        """设置数据库事件监听器"""
        if not self.engine:
            return
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """为SQLite设置PRAGMA"""
            if 'sqlite' in self.database_url:
                cursor = dbapi_connection.cursor()
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys=ON")
                # 设置WAL模式以提高并发性能
                cursor.execute("PRAGMA journal_mode=WAL")
                # 设置同步模式
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出时的处理"""
            logger.debug("Database connection checked out")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接检入时的处理"""
            logger.debug("Database connection checked in")
        
        @event.listens_for(self.engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """连接失效时的处理"""
            logger.warning(f"Database connection invalidated: {exception}")
    
    def _test_connection(self) -> None:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    def _mask_url(self, url: str) -> str:
        """遮蔽数据库URL中的敏感信息"""
        parsed = urlparse(url)
        if parsed.password:
            masked_url = url.replace(parsed.password, "***")
            return masked_url
        return url
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话（同步）"""
        if not self._is_initialized:
            raise RuntimeError("Database manager not initialized")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（异步）"""
        if not self._is_initialized or not self.async_session_factory:
            raise RuntimeError("Async database manager not initialized")
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()
    
    def create_tables(self) -> None:
        """创建所有表"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        try:
            create_all_tables(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """删除所有表"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        try:
            drop_all_tables(self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def get_table_info(self) -> Dict[str, Any]:
        """获取表信息"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        inspector = inspect(self.engine)
        tables_info = {}
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            tables_info[table_name] = {
                "columns": len(columns),
                "indexes": len(indexes),
                "foreign_keys": len(foreign_keys),
                "column_details": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "primary_key": col.get("primary_key", False)
                    }
                    for col in columns
                ]
            }
        
        return tables_info
    
    def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        health_info = {
            "status": "unknown",
            "database_url": self._mask_url(self.database_url),
            "initialized": self._is_initialized,
            "engine_info": None,
            "connection_test": False,
            "tables_count": 0,
            "error": None
        }
        
        try:
            if not self._is_initialized:
                health_info["status"] = "not_initialized"
                return health_info
            
            # 引擎信息
            if self.engine:
                pool = self.engine.pool
                health_info["engine_info"] = {
                    "pool_size": getattr(pool, 'size', lambda: 'N/A')(),
                    "checked_in": getattr(pool, 'checkedin', lambda: 'N/A')(),
                    "checked_out": getattr(pool, 'checkedout', lambda: 'N/A')(),
                    "overflow": getattr(pool, 'overflow', lambda: 'N/A')(),
                }
            
            # 连接测试
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                health_info["connection_test"] = True
            
            # 表数量
            inspector = inspect(self.engine)
            health_info["tables_count"] = len(inspector.get_table_names())
            
            health_info["status"] = "healthy"
            
        except Exception as e:
            health_info["status"] = "unhealthy"
            health_info["error"] = str(e)
            logger.error(f"Database health check failed: {e}")
        
        return health_info
    
    def close(self) -> None:
        """关闭数据库连接"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("Database engine disposed")
            
            if self.async_engine:
                # 异步引擎需要在异步上下文中关闭
                logger.info("Async database engine marked for disposal")
            
            self._is_initialized = False
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    async def close_async(self) -> None:
        """异步关闭数据库连接"""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
                logger.info("Async database engine disposed")
        except Exception as e:
            logger.error(f"Error closing async database connections: {e}")


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, database_manager: DatabaseManager, alembic_cfg_path: str = "alembic.ini"):
        """初始化迁移管理器"""
        self.db_manager = database_manager
        self.alembic_cfg_path = alembic_cfg_path
        self.alembic_cfg = None
    
    def initialize(self) -> None:
        """初始化Alembic配置"""
        try:
            self.alembic_cfg = AlembicConfig(self.alembic_cfg_path)
            # 设置数据库URL
            self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_manager.database_url)
            logger.info("Migration manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize migration manager: {e}")
            raise
    
    def create_migration(self, message: str) -> None:
        """创建新的迁移文件"""
        if not self.alembic_cfg:
            raise RuntimeError("Migration manager not initialized")
        
        try:
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            logger.info(f"Migration created: {message}")
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise
    
    def upgrade(self, revision: str = "head") -> None:
        """执行数据库升级"""
        if not self.alembic_cfg:
            raise RuntimeError("Migration manager not initialized")
        
        try:
            # 检查当前版本，如果已经是最新版本则跳过
            current_rev = self.get_current_revision()
            if current_rev == revision or (revision == "head" and current_rev):
                logger.info(f"Database already at revision: {current_rev}, skipping upgrade")
                return
            
            command.upgrade(self.alembic_cfg, revision)
            logger.info(f"Database upgraded to revision: {revision}")
        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            raise
    
    def downgrade(self, revision: str) -> None:
        """执行数据库降级"""
        if not self.alembic_cfg:
            raise RuntimeError("Migration manager not initialized")
        
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Database downgraded to revision: {revision}")
        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """获取当前数据库版本"""
        try:
            with self.db_manager.get_session() as session:
                context = MigrationContext.configure(session.connection())
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def get_migration_history(self) -> list:
        """获取迁移历史"""
        if not self.alembic_cfg:
            raise RuntimeError("Migration manager not initialized")
        
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []
            
            for revision in script_dir.walk_revisions():
                revisions.append({
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "message": revision.doc,
                    "create_date": getattr(revision, 'create_date', None)
                })
            
            return revisions
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None
_migration_manager: Optional[MigrationManager] = None


def get_database_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def get_migration_manager() -> MigrationManager:
    """获取全局迁移管理器实例"""
    global _migration_manager
    if _migration_manager is None:
        db_manager = get_database_manager()
        _migration_manager = MigrationManager(db_manager)
        _migration_manager.initialize()
    return _migration_manager


# 便捷函数
def get_db_session():
    """获取数据库会话的便捷函数"""
    return get_database_manager().get_session()


def get_async_db_session():
    """获取异步数据库会话的便捷函数"""
    return get_database_manager().get_async_session()


if __name__ == "__main__":
    # 测试数据库管理器
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        db_manager.initialize()
        
        # 健康检查
        health = db_manager.health_check()
        print("Database Health Check:")
        for key, value in health.items():
            print(f"  {key}: {value}")
        
        # 获取表信息
        tables_info = db_manager.get_table_info()
        print(f"\nTables: {len(tables_info)}")
        for table_name, info in tables_info.items():
            print(f"  {table_name}: {info['columns']} columns")
        
        # 测试会话
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1 as test"))
            print(f"\nSession test result: {result.fetchone()}")
        
        print("\n✅ Database manager test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Database manager test failed: {e}")
        sys.exit(1)
    
    finally:
        if 'db_manager' in locals():
            db_manager.close()