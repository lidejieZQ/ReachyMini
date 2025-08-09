# Reachy Mini Robot Control System

<div align="center">

![Reachy Mini](https://img.shields.io/badge/Robot-Reachy%20Mini-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Rust](https://img.shields.io/badge/Rust-1.70+-orange)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688)
![License](https://img.shields.io/badge/License-MIT-yellow)

**现代化的机器人控制平台，集成 Python 后端、Rust 核心和 React 前端**

[English](README_EN.md) | 中文

</div>

## 🚀 项目概述

Reachy Mini 是一个现代化的机器人控制系统，采用混合语言架构设计，结合了 Python 的易用性、Rust 的高性能和 React 的现代化前端体验。系统提供了完整的机器人控制、监控和管理功能。

### ✨ 核心特性

- 🔧 **混合语言架构**: Python + Rust + TypeScript
- ⚡ **高性能**: Rust 核心模块提供实时控制能力
- 🌐 **现代化 Web 界面**: React + TypeScript 前端
- 📊 **实时监控**: 系统健康检查和状态监控
- 🔌 **RESTful API**: 完整的 API 接口
- 🔄 **WebSocket 支持**: 实时双向通信
- 🐳 **容器化部署**: Docker 支持
- 📚 **完整文档**: 详细的架构和 API 文档

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端层 (React) │    │  API层 (FastAPI) │    │ 核心层 (Rust)    │
│                 │    │                 │    │                 │
│ • React 18      │◄──►│ • FastAPI       │◄──►│ • 高性能计算     │
│ • TypeScript    │    │ • WebSocket     │    │ • 实时控制       │
│ • Vite          │    │ • 中间件        │    │ • PyO3 绑定     │
│ • 实时监控      │    │ • 异常处理      │    │ • 硬件接口       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                    ┌─────────────────┐
                    │   数据层         │
                    │                 │
                    │ • SQLite/PostgreSQL │
                    │ • 配置管理       │
                    │ • 日志系统       │
                    │ • 缓存系统       │
                    └─────────────────┘
```

## 📋 技术栈

### 后端
- **Python 3.8+**: 主要业务逻辑
- **FastAPI**: 现代化 Web 框架
- **Rust**: 高性能核心模块
- **PyO3**: Python-Rust 绑定
- **SQLAlchemy**: ORM 框架
- **Alembic**: 数据库迁移

### 前端
- **React 18**: 用户界面框架
- **TypeScript**: 类型安全
- **Vite**: 构建工具
- **CSS3**: 样式设计

### 基础设施
- **Docker**: 容器化部署
- **Nginx**: 反向代理
- **SQLite/PostgreSQL**: 数据存储

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- Rust 1.70+
- Docker (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/lidejieZQ/ReachyMini.git
cd ReachyMini
```

2. **后端设置**
```bash
cd backend/python
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Rust 模块构建**
```bash
cd ../rust
cargo build --release
```

4. **前端设置**
```bash
cd ../../frontend
npm install
npm run build
```

5. **启动服务**
```bash
cd ../backend/python
source venv/bin/activate
python main.py
```

6. **访问应用**
   - Web 界面: http://localhost:8000
   - API 文档: http://localhost:8000/docs
   - 健康检查: http://localhost:8000/health

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📖 项目结构

```
ReachyMini/
├── backend/                    # 后端代码
│   ├── python/                # Python 后端
│   │   ├── api/              # API 路由
│   │   ├── core/             # 核心业务逻辑
│   │   ├── models/           # 数据模型
│   │   ├── services/         # 业务服务
│   │   ├── utils/            # 工具函数
│   │   ├── main.py           # 应用入口
│   │   └── requirements.txt  # Python 依赖
│   └── rust/                 # Rust 核心模块
│       ├── src/              # Rust 源码
│       ├── Cargo.toml        # Rust 配置
│       └── target/           # 构建输出
├── frontend/                   # 前端代码
│   ├── src/                  # React 源码
│   │   ├── components/       # React 组件
│   │   ├── App.tsx           # 主应用组件
│   │   └── main.tsx          # 入口文件
│   ├── package.json          # Node.js 依赖
│   └── vite.config.ts        # Vite 配置
├── config/                     # 配置文件
├── docs/                       # 文档
├── scripts/                    # 脚本文件
├── tests/                      # 测试文件
├── docker-compose.yml          # Docker 编排
├── PROJECT_ARCHITECTURE.md     # 架构文档
├── OPERATIONAL_LOGIC.md        # 运行逻辑文档
├── ARCHITECTURE_DIAGRAMS.md    # 架构图表
└── README.md                   # 项目说明
```

## 🔧 API 接口

### 核心端点

- `GET /api/health` - 系统健康检查
- `GET /system/info` - 系统信息
- `GET /system/status` - 系统状态
- `WS /ws` - WebSocket 连接

### 示例请求

```bash
# 健康检查
curl http://localhost:8000/api/health

# 系统信息
curl http://localhost:8000/system/info

# 系统状态
curl http://localhost:8000/system/status
```

## 🖥️ Web 界面

系统提供了现代化的 Web 管理界面：

- **主页**: 系统概览和快速导航
- **健康检查页面**: 实时系统状态监控
- **系统状态**: 详细的组件状态信息
- **API 文档**: 交互式 API 文档

## 🔍 监控和日志

### 健康检查
- 自动健康检查机制
- 组件状态监控
- 实时状态更新

### 日志系统
- 结构化日志记录
- 多级别日志支持
- 日志轮转和归档

### 性能监控
- 系统资源监控
- API 响应时间统计
- 错误率监控

## 🧪 测试

```bash
# Python 测试
cd backend/python
python -m pytest tests/

# Rust 测试
cd backend/rust
cargo test

# 前端测试
cd frontend
npm test
```

## 📚 文档

- [项目架构文档](PROJECT_ARCHITECTURE.md)
- [运行逻辑文档](OPERATIONAL_LOGIC.md)
- [架构图表集合](ARCHITECTURE_DIAGRAMS.md)
- [依赖和工具总结](DEPENDENCIES_AND_TOOLS.md)
- [前端集成总结](FRONTEND_INTEGRATION_SUMMARY.md)
- [Rust 集成总结](backend/RUST_INTEGRATION_SUMMARY.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 👥 作者

- **lidejie** - *初始工作* - [lidejieZQ](https://github.com/lidejieZQ)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://reactjs.org/) - 用户界面库
- [Rust](https://www.rust-lang.org/) - 系统编程语言
- [PyO3](https://pyo3.rs/) - Python-Rust 绑定

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 项目 Issues: [GitHub Issues](https://github.com/lidejieZQ/ReachyMini/issues)
- 邮箱: lidejie@example.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

</div>