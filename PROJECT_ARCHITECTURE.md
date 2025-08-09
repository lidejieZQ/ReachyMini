# Reachy Mini 项目架构文档

## 项目概述

Reachy Mini 是一个基于 Allspark2-Orin NX 平台的机器人控制系统，采用现代化的多层架构设计，集成了 Python FastAPI 后端、Rust 高性能模块和 React 前端界面。

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Reachy Mini 系统架构                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    HTTP/WebSocket    ┌─────────────────────────┐
│                 │ ◄──────────────────► │                         │
│   前端 (React)   │                      │    后端 (Python)        │
│                 │                      │                         │
│  ┌─────────────┐ │                      │  ┌─────────────────────┐ │
│  │ 健康检查页面 │ │                      │  │   FastAPI 应用      │ │
│  │ 控制面板    │ │                      │  │   - REST API        │ │
│  │ 状态监控    │ │                      │  │   - WebSocket       │ │
│  └─────────────┘ │                      │  │   - 静态文件服务     │ │
│                 │                      │  └─────────────────────┘ │
└─────────────────┘                      │                         │
                                         │  ┌─────────────────────┐ │
                                         │  │   服务管理器         │ │
                                         │  │   - 生命周期管理     │ │
                                         │  │   - 组件协调        │ │
                                         │  │   - 状态监控        │ │
                                         │  └─────────────────────┘ │
                                         │           │               │
                                         │           ▼               │
                                         │  ┌─────────────────────┐ │
                                         │  │   Rust 绑定模块      │ │
                                         │  │   - 高性能计算       │ │
                                         │  │   - 硬件接口        │ │
                                         │  │   - 实时处理        │ │
                                         │  └─────────────────────┘ │
                                         └─────────────────────────┘
                                                     │
                                                     ▼
                                         ┌─────────────────────────┐
                                         │    Rust 核心模块         │
                                         │                         │
                                         │  ┌─────────────────────┐ │
                                         │  │  ReachyMiniSystem   │ │
                                         │  │  - 系统管理         │ │
                                         │  │  - 配置管理         │ │
                                         │  │  - 状态监控         │ │
                                         │  └─────────────────────┘ │
                                         └─────────────────────────┘
```

## 技术栈架构

### 前端层 (Frontend)
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **状态管理**: React Hooks (useState, useEffect)
- **样式**: CSS Modules
- **通信**: Fetch API + WebSocket

### 后端层 (Backend)
- **Web框架**: FastAPI (Python)
- **异步处理**: asyncio
- **中间件**: CORS, GZip
- **静态文件**: StaticFiles
- **生命周期**: Lifespan 管理

### 核心服务层 (Core Services)
- **服务管理器**: ServiceManager
- **数据库管理**: DatabaseManager
- **配置管理**: Config System
- **异常处理**: Custom Exception Handlers

### 高性能层 (Rust Module)
- **语言**: Rust
- **绑定**: PyO3 (Python-Rust 绑定)
- **异步**: Tokio
- **序列化**: Serde
- **错误处理**: anyhow + thiserror

## 数据流架构

```
用户交互 → React 组件 → HTTP/WebSocket → FastAPI 路由 → 服务管理器 → Rust 模块 → 硬件/AI
    ↑                                                                              ↓
    └──────────────────── 响应数据 ←──────────────────────────────────────────────┘
```

## 核心组件详解

### 1. 前端架构 (Frontend)

```
frontend/src/
├── App.tsx                 # 主应用组件，路由管理
├── App.css                 # 全局样式
├── main.tsx               # 应用入口点
├── components/
│   ├── HealthCheck.tsx    # 健康检查页面组件
│   └── HealthCheck.css    # 健康检查样式
└── vite-env.d.ts         # TypeScript 类型声明
```

**关键特性**:
- SPA (单页应用) 路由
- 响应式设计
- 实时数据更新
- 模态框交互
- 错误处理和重试机制

### 2. 后端架构 (Backend Python)

```
backend/python/
├── main.py                # FastAPI 应用入口
├── service_manager.py     # 核心服务管理器
├── rust_bindings.py      # Rust 模块绑定
├── core/
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库管理
│   └── exceptions.py     # 异常处理
├── api/                  # API 路由模块
├── models/              # 数据模型
├── services/            # 业务服务
└── utils/               # 工具函数
```

**关键特性**:
- 异步 FastAPI 应用
- 生命周期管理
- 中间件支持
- 静态文件服务
- WebSocket 支持
- 健康检查机制

### 3. Rust 核心模块

```
backend/rust/src/
├── lib.rs               # 库入口，核心系统
├── python_bindings.rs   # Python 绑定接口
├── config.rs           # 配置管理
└── Cargo.toml          # 依赖配置
```

**关键特性**:
- 高性能异步处理
- 内存安全
- Python 互操作性
- 配置验证
- 错误处理

## 运行时架构

### 启动流程

```
1. main.py 启动
   ↓
2. 创建 FastAPI 应用
   ↓
3. 设置中间件和路由
   ↓
4. 初始化服务管理器
   ↓
5. 启动 Rust 模块
   ↓
6. 启动 Web 服务器
   ↓
7. 系统就绪
```

### 请求处理流程

```
前端请求 → FastAPI 路由 → 业务逻辑 → Rust 模块 → 返回响应
```

### 健康检查流程

```
1. 前端访问 /health
2. 返回 React 应用 (index.html)
3. React 路由到 HealthCheck 组件
4. 组件调用 /api/health API
5. 后端返回系统状态 JSON
6. 前端渲染健康检查页面
```

## 配置架构

### 配置层级

```
环境变量 → 配置文件 → 默认值
```

### 配置传递

```
Python Config → JSON → Rust Config
```

## 部署架构

### 开发环境
- 前端: Vite 开发服务器 (端口 3000)
- 后端: Python 开发服务器 (端口 8000)
- 代理: Vite 代理配置

### 生产环境
- 集成服务器: FastAPI + 静态文件服务 (端口 8000)
- 前端构建: 静态文件部署
- 反向代理: Nginx (可选)

## 扩展性设计

### 水平扩展
- 微服务架构支持
- 负载均衡器支持
- 数据库集群支持

### 垂直扩展
- 模块化设计
- 插件系统
- 配置驱动

## 安全架构

### 网络安全
- CORS 配置
- HTTPS 支持
- 请求限制

### 数据安全
- 输入验证
- 错误处理
- 日志记录

## 监控架构

### 健康检查
- 系统状态监控
- 组件状态检查
- 性能指标收集

### 日志系统
- 结构化日志
- 日志级别管理
- 日志轮转

## 总结

Reachy Mini 项目采用现代化的分层架构，通过 Python 和 Rust 的结合，实现了高性能和易维护性的平衡。前端使用 React 提供现代化的用户界面，后端使用 FastAPI 提供高性能的 API 服务，Rust 模块负责计算密集型任务，整体架构具有良好的可扩展性和维护性。