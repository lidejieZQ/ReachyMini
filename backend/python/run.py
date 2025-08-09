#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reachy Mini 快速启动脚本
用于快速启动和测试 Reachy Mini 系统
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from main import main_async, setup_environment, check_dependencies, validate_system_config
from core.config import get_config
from service_manager import get_service_manager
from rust_bindings import is_rust_available, get_rust_system_info

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    Reachy Mini Robot                         ║
    ║                   Control System v1.0                       ║
    ║                                                              ║
    ║    基于 Allspark2-Orin NX 平台的智能机器人控制系统          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_system_info():
    """打印系统信息"""
    config = get_config()
    
    print("\n🔧 系统配置信息:")
    print(f"   • API 地址: http://{config.api_host}:{config.api_port}")
    print(f"   • 调试模式: {'开启' if config.debug else '关闭'}")
    print(f"   • 数据库: {config.database_url.split('@')[-1] if '@' in config.database_url else 'local'}")
    
    print("\n🐍 Python 环境:")
    print(f"   • Python 版本: {sys.version.split()[0]}")
    print(f"   • 平台: {sys.platform}")
    print(f"   • 工作目录: {os.getcwd()}")
    
    print("\n🦀 Rust 后端:")
    if is_rust_available():
        try:
            rust_info = get_rust_system_info()
            print(f"   • 状态: 可用")
            print(f"   • 版本: {rust_info.get('version', 'unknown')}")
            print(f"   • 功能: {', '.join(rust_info.get('features', []))}")
        except Exception as e:
            print(f"   • 状态: 错误 - {e}")
    else:
        print(f"   • 状态: 不可用")


async def quick_test():
    """快速系统测试"""
    print("\n🧪 执行快速系统测试...")
    
    try:
        # 测试服务管理器
        service_manager = get_service_manager()
        print("   ✅ 服务管理器: OK")
        
        # 测试配置
        config = get_config()
        if validate_system_config():
            print("   ✅ 系统配置: OK")
        else:
            print("   ❌ 系统配置: 失败")
            return False
        
        # 测试依赖
        if check_dependencies():
            print("   ✅ 依赖检查: OK")
        else:
            print("   ❌ 依赖检查: 失败")
            return False
        
        print("\n🎉 系统测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 系统测试失败: {e}")
        return False


def show_help():
    """显示帮助信息"""
    help_text = """
用法: python run.py [选项]

选项:
  --help, -h        显示此帮助信息
  --test, -t        执行系统测试
  --info, -i        显示系统信息
  --start, -s       启动服务器（默认）
  --version, -v     显示版本信息

示例:
  python run.py              # 启动服务器
  python run.py --test       # 执行系统测试
  python run.py --info       # 显示系统信息
    """
    print(help_text)


async def main():
    """主函数"""
    # 解析命令行参数
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if "--help" in args or "-h" in args:
        show_help()
        return
    
    if "--version" in args or "-v" in args:
        print("Reachy Mini Control System v1.0.0")
        return
    
    # 打印横幅
    print_banner()
    
    if "--info" in args or "-i" in args:
        print_system_info()
        return
    
    if "--test" in args or "-t" in args:
        print_system_info()
        success = await quick_test()
        if not success:
            sys.exit(1)
        return
    
    # 默认启动服务器
    print_system_info()
    
    # 执行快速测试
    if not await quick_test():
        print("\n❌ 系统测试失败，无法启动服务器")
        sys.exit(1)
    
    print("\n🚀 启动服务器...")
    print("按 Ctrl+C 停止服务器\n")
    
    try:
        # 启动主应用
        await main_async()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序异常退出: {e}")
        sys.exit(1)