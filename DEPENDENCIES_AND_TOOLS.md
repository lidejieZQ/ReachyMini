# Reachy Mini 项目依赖和工具总结

## 项目概述

本文档记录了 Reachy Mini 项目中使用的所有依赖包、开发工具、模型和其他资源，便于项目维护和部署。

## 技术栈总览

### 前端技术栈
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **包管理器**: npm

### 后端技术栈
- **主要语言**: Python 3.8+
- **Web框架**: FastAPI
- **高性能模块**: Rust
- **数据库**: SQLite/PostgreSQL
- **异步运行时**: asyncio (Python) + Tokio (Rust)

## Python 依赖包

### 核心框架依赖

```toml
[core-dependencies]
fastapi = "^0.104.0"          # 现代化的Web框架，提供自动API文档
uvicorn = "^0.24.0"           # ASGI服务器，支持异步处理
pydantic = "^2.5.0"          # 数据验证和序列化
starlette = "^0.27.0"        # FastAPI的底层ASGI框架
```

**用途说明**:
- `fastapi`: 提供REST API接口、自动文档生成、数据验证
- `uvicorn`: 高性能ASGI服务器，支持WebSocket和异步处理
- `pydantic`: 数据模型定义、请求/响应验证、配置管理
- `starlette`: 底层Web框架，提供中间件和路由功能

### 数据库相关

```toml
[database-dependencies]
sqlalchemy = "^2.0.0"        # ORM框架，数据库抽象层
alembic = "^1.13.0"          # 数据库迁移工具
aiosqlite = "^0.19.0"        # 异步SQLite驱动
psycopg2-binary = "^2.9.0"   # PostgreSQL驱动（可选）
```

**用途说明**:
- `sqlalchemy`: 提供ORM功能，数据库操作抽象
- `alembic`: 管理数据库结构变更和版本控制
- `aiosqlite`: 异步SQLite操作支持
- `psycopg2-binary`: PostgreSQL数据库连接（生产环境）

### Rust 集成

```toml
[rust-integration]
pyo3 = "^0.20.0"             # Python-Rust绑定
maturin = "^1.4.0"           # Rust-Python包构建工具
```

**用途说明**:
- `pyo3`: 在Python中调用Rust函数，提供高性能计算能力
- `maturin`: 构建和发布Rust-Python混合包

### 工具和实用库

```toml
[utility-dependencies]
requests = "^2.31.0"         # HTTP客户端库
aiohttp = "^3.9.0"           # 异步HTTP客户端
click = "^8.1.0"             # 命令行接口工具
rich = "^13.7.0"             # 终端美化和进度条
loguru = "^0.7.0"            # 现代化日志库
python-dotenv = "^1.0.0"     # 环境变量管理
pytest = "^7.4.0"            # 测试框架
pytest-asyncio = "^0.21.0"   # 异步测试支持
black = "^23.12.0"           # 代码格式化工具
flake8 = "^6.1.0"            # 代码风格检查
mypy = "^1.8.0"              # 静态类型检查
```

**用途说明**:
- `requests/aiohttp`: HTTP请求处理，API调用
- `click`: 构建命令行工具和脚本
- `rich`: 终端输出美化，进度显示
- `loguru`: 结构化日志记录
- `python-dotenv`: 环境配置管理
- `pytest`: 单元测试和集成测试
- `black/flake8/mypy`: 代码质量保证工具

## Rust 依赖包

### 核心依赖

```toml
[dependencies]
tokio = { version = "1.35", features = ["full"] }  # 异步运行时
serde = { version = "1.0", features = ["derive"] }  # 序列化框架
anyhow = "1.0"                                      # 错误处理
log = "0.4"                                         # 日志接口
chrono = { version = "0.4", features = ["serde"] }  # 时间处理
thiserror = "1.0"                                   # 错误类型定义
```

**用途说明**:
- `tokio`: 异步运行时，提供高性能并发处理
- `serde`: 数据序列化/反序列化，与Python数据交换
- `anyhow`: 简化错误处理，提供上下文信息
- `log`: 统一日志接口
- `chrono`: 时间和日期处理
- `thiserror`: 自定义错误类型

### Python 绑定

```toml
[dependencies.pyo3]
version = "0.20"
features = ["extension-module", "abi3-py38"]
```

**用途说明**:
- `pyo3`: 提供Python-Rust互操作能力
- `extension-module`: 构建Python扩展模块
- `abi3-py38`: 稳定ABI支持，兼容Python 3.8+

## 前端依赖包

### 核心框架

```json
{
  "dependencies": {
    "react": "^18.2.0",           // React核心库
    "react-dom": "^18.2.0",       // React DOM渲染
    "typescript": "^5.2.2"        // TypeScript支持
  }
}
```

### 开发工具

```json
{
  "devDependencies": {
    "@types/react": "^18.2.43",          // React类型定义
    "@types/react-dom": "^18.2.17",      // React DOM类型定义
    "@typescript-eslint/eslint-plugin": "^6.14.0",  // TS ESLint插件
    "@typescript-eslint/parser": "^6.14.0",         // TS ESLint解析器
    "@vitejs/plugin-react": "^4.2.1",               // Vite React插件
    "eslint": "^8.55.0",                            // 代码检查工具
    "eslint-plugin-react-hooks": "^4.6.0",         // React Hooks规则
    "eslint-plugin-react-refresh": "^0.4.5",       // React刷新支持
    "vite": "^5.0.8"                                // 构建工具
  }
}
```

**用途说明**:
- `react/react-dom`: React框架核心
- `typescript`: 静态类型检查
- `@types/*`: TypeScript类型定义
- `eslint`: 代码质量检查
- `vite`: 快速构建和热重载

## 开发工具

### 代码编辑器和IDE
- **推荐**: Visual Studio Code
- **插件**:
  - Python Extension Pack
  - Rust Analyzer
  - ES7+ React/Redux/React-Native snippets
  - Prettier - Code formatter
  - GitLens

### 版本控制
- **Git**: 分布式版本控制系统
- **GitHub**: 代码托管和协作平台

### 构建和部署工具

```bash
# Python环境管理
pyenv          # Python版本管理
virtualenv     # 虚拟环境
pip           # Python包管理器

# Rust工具链
rustc         # Rust编译器
cargo         # Rust包管理器和构建工具
rustup        # Rust工具链管理器

# 前端工具
node.js       # JavaScript运行时
npm           # Node.js包管理器
vite          # 前端构建工具
```

### 测试工具

```bash
# Python测试
pytest        # 测试框架
coverage      # 代码覆盖率

# Rust测试
cargo test    # 内置测试工具

# 前端测试
vitest        # Vite测试框架（可选）
jest          # JavaScript测试框架（可选）
```

## 数据库

### 开发环境
- **SQLite**: 轻量级文件数据库
  - 文件位置: `data/reachy_mini.db`
  - 优点: 零配置，适合开发和测试
  - 限制: 单用户，性能有限

### 生产环境（可选）
- **PostgreSQL**: 企业级关系数据库
  - 版本: 13+
  - 特性: 高性能，支持并发，ACID事务
  - 配置: 通过环境变量设置连接参数

## 模型和AI服务

### 机器学习框架（预留）
```python
# 可能用到的ML库
torch          # PyTorch深度学习框架
tensorflow     # TensorFlow机器学习平台
opencv-python  # 计算机视觉库
numpy          # 数值计算库
scipy          # 科学计算库
```

### AI服务接口（预留）
- **OpenAI API**: 自然语言处理
- **Google Cloud Vision**: 图像识别
- **Azure Cognitive Services**: 多模态AI服务

## 系统依赖

### 操作系统要求
- **开发环境**: macOS, Linux, Windows
- **生产环境**: Linux (Ubuntu 20.04+ 推荐)
- **硬件平台**: Allspark2-Orin NX

### 系统库
```bash
# Ubuntu/Debian
sudo apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3-dev

# macOS (通过Homebrew)
brew install \
    rust \
    python@3.11 \
    node \
    git
```

## 环境配置

### 环境变量
```bash
# 应用配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///data/reachy_mini.db
# DATABASE_URL=postgresql://user:pass@localhost/reachy_mini

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/reachy_mini.log

# Rust配置
RUST_LOG=info
RUST_BACKTRACE=1
```

### 配置文件
- `config/development.toml`: 开发环境配置
- `config/production.toml`: 生产环境配置
- `.env`: 环境变量文件
- `pyproject.toml`: Python项目配置
- `Cargo.toml`: Rust项目配置
- `package.json`: Node.js项目配置

## 部署相关

### 容器化（可选）
```dockerfile
# Docker相关文件
Dockerfile              # 应用容器定义
docker-compose.yml      # 多服务编排
.dockerignore          # Docker忽略文件
```

### 进程管理
```bash
# 系统服务
systemd               # Linux服务管理
supervisor           # 进程监控和管理
pm2                  # Node.js进程管理（可选）
```

### 反向代理
```nginx
# Nginx配置示例
server {
    listen 80;
    server_name reachy-mini.local;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 性能监控

### 应用监控
- **日志聚合**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **指标收集**: Prometheus + Grafana
- **错误追踪**: Sentry
- **性能分析**: py-spy (Python), perf (系统级)

### 系统监控
- **资源监控**: htop, iotop, nethogs
- **系统指标**: collectd, telegraf
- **健康检查**: 内置 `/api/health` 端点

## 安全相关

### 依赖安全
```bash
# Python安全检查
pip-audit             # 依赖漏洞扫描
safety               # 安全漏洞检查
bandit               # 代码安全分析

# Rust安全检查
cargo audit          # 依赖审计
cargo deny           # 许可证和安全检查

# 前端安全检查
npm audit            # npm依赖审计
yarn audit           # yarn依赖审计
```

### 证书和加密
- **TLS证书**: Let's Encrypt (生产环境)
- **密钥管理**: 环境变量或密钥管理服务
- **数据加密**: 数据库级别加密

## 总结

本项目采用现代化的技术栈，通过合理的依赖管理和工具选择，实现了：

1. **高性能**: Rust + Python + React 的组合提供了最佳的性能和开发体验
2. **可维护性**: 完善的类型系统、测试框架和代码质量工具
3. **可扩展性**: 模块化设计，支持水平和垂直扩展
4. **安全性**: 多层次的安全检查和最佳实践
5. **可部署性**: 支持多种部署方式，从开发到生产的完整流程

定期更新依赖包版本，关注安全公告，保持项目的健康和安全。