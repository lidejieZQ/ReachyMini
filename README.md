# Reachy Mini 机器人项目 - Allspark2-Orin NX平台

## 项目概述

本项目旨在在Allspark2-Orin NX平台上实现Reachy Mini机器人的完整控制系统。该系统结合了高性能边缘AI计算、实时机器人控制、现代Web技术和容器化部署，为Reachy Mini机器人提供了一个功能完整、性能优异的控制平台。

## 核心特性

- 🤖 **完整机器人控制**: 支持Reachy Mini的头部运动、身体旋转、天线控制
- 🎥 **实时视频流**: 基于WebRTC的低延迟视频传输
- 🧠 **AI智能处理**: GPU加速的计算机视觉、语音识别和自然语言处理
- 🌐 **现代Web界面**: React + TypeScript构建的响应式控制界面
- ⚡ **高性能后端**: Python + Rust混合架构，充分利用各语言优势
- 🐳 **容器化部署**: Docker + Docker Compose一键部署
- 📡 **实时通信**: WebSocket双向通信，支持低延迟控制

## 技术架构

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   后端服务      │    │  Reachy Mini    │
│                 │    │                 │    │                 │
│ React + TS      │◄──►│ FastAPI + Rust  │◄──►│ gRPC + Python   │
│ WebRTC          │    │ WebSocket       │    │ 硬件控制        │
│ 实时控制        │    │ AI推理          │    │ 传感器数据      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Allspark2-Orin  │
                    │      NX         │
                    │ GPU加速计算     │
                    │ 边缘AI推理      │
                    └─────────────────┘
```

### 技术栈

**后端技术**:
- **Python**: FastAPI, WebSocket, gRPC, OpenCV, PyTorch
- **Rust**: 高性能数据处理、实时视频编码、硬件接口
- **数据库**: PostgreSQL (数据存储) + Redis (缓存)
- **AI框架**: PyTorch, TensorRT, Whisper, YOLO

**前端技术**:
- **框架**: React 18 + TypeScript
- **状态管理**: Context API + useReducer
- **实时通信**: WebSocket + WebRTC
- **UI组件**: Tailwind CSS + Headless UI
- **构建工具**: Vite + ESBuild

**部署技术**:
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack

## 项目结构

```
reachy-mini/
├── 📁 backend/                 # 后端代码
│   ├── 📁 python/             # Python服务
│   │   ├── main.py           # FastAPI应用入口
│   │   ├── 📁 api/            # API路由
│   │   ├── 📁 core/           # 核心功能
│   │   ├── 📁 models/         # 数据模型
│   │   ├── 📁 services/       # 业务服务
│   │   └── 📁 utils/          # 工具函数
│   └── 📁 rust/               # Rust模块
│       ├── 📁 src/            # Rust源码
│       ├── Cargo.toml        # Rust依赖
│       └── build.rs          # 构建脚本
├── 📁 frontend/               # 前端代码
│   ├── 📁 src/                # React源码
│   │   ├── 📁 components/     # 组件
│   │   ├── 📁 contexts/       # 上下文
│   │   ├── 📁 hooks/          # 自定义Hook
│   │   ├── 📁 services/       # 服务层
│   │   └── 📁 utils/          # 工具函数
│   ├── 📁 public/             # 静态资源
│   └── package.json          # 前端依赖
├── 📁 config/                 # 配置文件
│   ├── 📁 docker/             # Docker配置
│   ├── 📁 nginx/              # Nginx配置
│   ├── 📁 env/                # 环境配置
│   └── 📁 postgres/           # 数据库配置
├── 📁 scripts/                # 脚本文件
├── 📁 docs/                   # 文档
├── 📁 tests/                  # 测试文件
├── docker-compose.yml        # Docker编排
├── 技术框架总结.md            # 技术框架文档
├── 详细技术实现方案.md        # 详细实现方案
└── README.md                 # 项目说明
```

## 快速开始

### 系统要求

- **硬件**: Allspark2-Orin NX或兼容的NVIDIA Jetson设备
- **操作系统**: Ubuntu 20.04/22.04 LTS (ARM64)
- **内存**: 至少8GB RAM
- **存储**: 至少64GB可用空间
- **GPU**: NVIDIA GPU支持CUDA 11.4+

### 环境准备

1. **安装Docker和Docker Compose**
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **安装NVIDIA Container Toolkit**
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 项目部署

1. **克隆项目**
```bash
git clone <repository-url> reachy-mini
cd reachy-mini
```

2. **配置环境**
```bash
# 设置脚本权限
chmod +x scripts/*.sh

# 复制环境配置
cp config/env/.env.development .env

# 编辑配置文件（根据实际情况修改）
nano .env
```

3. **启动开发环境**
```bash
# 一键启动开发环境
./scripts/dev-start.sh
```

4. **访问应用**
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 功能特性

### 🎮 机器人控制
- **头部控制**: 支持Pitch、Yaw、Roll三轴运动
- **身体旋转**: 360度连续旋转控制
- **天线控制**: 独立的天线位置调节
- **实时反馈**: 显示当前位置和状态信息

### 📹 视频流处理
- **实时视频**: 低延迟视频流传输
- **多分辨率**: 支持多种分辨率和帧率
- **智能压缩**: 自适应码率和质量调节
- **录制功能**: 支持视频录制和截图

### 🧠 AI智能功能
- **计算机视觉**: 物体检测、人脸识别、姿态估计
- **语音处理**: 语音识别、语音合成、情感分析
- **自然语言**: 对话理解、意图识别、智能回复
- **行为规划**: 基于AI的自主行为决策

### 🌐 Web界面
- **响应式设计**: 支持桌面和移动设备
- **实时监控**: 机器人状态实时显示
- **直观控制**: 拖拽式控制界面
- **数据可视化**: 传感器数据图表展示

## 开发指南

### 开发环境搭建

详细的开发环境搭建步骤请参考 [详细技术实现方案.md](./详细技术实现方案.md#开发指南)

### 代码规范

- **Python**: 使用Black格式化，mypy类型检查
- **Rust**: 使用rustfmt格式化，clippy代码检查
- **TypeScript**: 使用Prettier格式化，ESLint代码检查

### 测试

```bash
# 后端测试
cd backend/python && pytest tests/
cd backend/rust && cargo test

# 前端测试
cd frontend && npm test
```

## 部署指南

### 开发环境
```bash
./scripts/dev-start.sh
```

### 生产环境
```bash
./scripts/deploy.sh production
```

详细的部署配置请参考 [详细技术实现方案.md](./详细技术实现方案.md#部署配置文件)

## 性能优化

- **GPU加速**: 充分利用Allspark2-Orin NX的GPU计算能力
- **内存优化**: 智能内存管理和缓存策略
- **网络优化**: WebSocket连接池和数据压缩
- **并发处理**: 异步处理和多线程优化

## 监控和日志

- **系统监控**: CPU、GPU、内存使用率监控
- **应用监控**: API响应时间、错误率统计
- **日志管理**: 结构化日志和日志轮转
- **告警机制**: 异常情况自动告警

## 故障排除

常见问题和解决方案请参考 [详细技术实现方案.md](./详细技术实现方案.md#故障排除)

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

- 项目维护者: [您的姓名]
- 邮箱: [您的邮箱]
- 项目链接: [项目仓库地址]

## 致谢

- [Pollen Robotics](https://pollen-robotics.com/) - Reachy Mini机器人
- [NVIDIA](https://www.nvidia.com/) - Jetson平台和AI计算支持
- [React](https://reactjs.org/) - 前端框架
- [FastAPI](https://fastapi.tiangolo.com/) - 后端API框架
- [Rust](https://www.rust-lang.org/) - 系统编程语言

---

**注意**: 本项目仍在积极开发中，功能和API可能会发生变化。建议在生产环境使用前进行充分测试。