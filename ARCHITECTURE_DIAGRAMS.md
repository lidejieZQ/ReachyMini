# Reachy Mini 系统架构图表

本文档包含了 Reachy Mini 系统的各种架构图表，帮助理解系统的整体结构和组件关系。

## 1. 系统总体架构图

```mermaid
graph TB
    subgraph "用户层"
        U1[Web浏览器]
        U2[移动设备]
        U3[API客户端]
    end
    
    subgraph "网络层"
        N1[Nginx反向代理]
        N2[负载均衡器]
    end
    
    subgraph "前端层"
        F1[React应用]
        F2[静态资源]
        F3[Service Worker]
    end
    
    subgraph "API网关层"
        A1[FastAPI应用]
        A2[中间件层]
        A3[路由处理]
    end
    
    subgraph "业务逻辑层"
        B1[服务管理器]
        B2[健康检查]
        B3[系统监控]
        B4[任务调度]
    end
    
    subgraph "核心服务层"
        C1[Rust核心模块]
        C2[Python绑定]
        C3[WebSocket服务]
    end
    
    subgraph "数据层"
        D1[SQLite数据库]
        D2[配置文件]
        D3[日志文件]
        D4[缓存系统]
    end
    
    subgraph "基础设施层"
        I1[操作系统]
        I2[Docker容器]
        I3[进程管理]
    end
    
    U1 --> N1
    U2 --> N1
    U3 --> N1
    N1 --> N2
    N2 --> F1
    N2 --> A1
    F1 --> F2
    F1 --> F3
    A1 --> A2
    A2 --> A3
    A3 --> B1
    B1 --> B2
    B1 --> B3
    B1 --> B4
    B1 --> C1
    C1 --> C2
    C1 --> C3
    B1 --> D1
    B1 --> D2
    B1 --> D3
    B1 --> D4
    C1 --> I1
    A1 --> I2
    I2 --> I3
```

## 2. 组件交互图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Browser as 浏览器
    participant Nginx as Nginx
    participant React as React应用
    participant FastAPI as FastAPI
    participant ServiceMgr as 服务管理器
    participant Rust as Rust模块
    participant DB as 数据库
    
    User->>Browser: 访问系统
    Browser->>Nginx: HTTP请求
    Nginx->>React: 静态资源请求
    React-->>Browser: 页面渲染
    Browser->>Nginx: API请求
    Nginx->>FastAPI: 转发请求
    FastAPI->>ServiceMgr: 业务处理
    ServiceMgr->>Rust: 调用核心功能
    ServiceMgr->>DB: 数据操作
    DB-->>ServiceMgr: 返回数据
    Rust-->>ServiceMgr: 返回结果
    ServiceMgr-->>FastAPI: 处理结果
    FastAPI-->>Nginx: JSON响应
    Nginx-->>Browser: 返回响应
    Browser-->>User: 显示结果
```

## 3. 数据流图

```mermaid
flowchart LR
    subgraph "输入层"
        I1[用户输入]
        I2[API调用]
        I3[定时任务]
        I4[WebSocket消息]
    end
    
    subgraph "处理层"
        P1[请求验证]
        P2[业务逻辑]
        P3[数据转换]
        P4[错误处理]
    end
    
    subgraph "存储层"
        S1[内存缓存]
        S2[数据库]
        S3[文件系统]
        S4[配置存储]
    end
    
    subgraph "输出层"
        O1[HTTP响应]
        O2[WebSocket推送]
        O3[日志记录]
        O4[系统状态]
    end
    
    I1 --> P1
    I2 --> P1
    I3 --> P2
    I4 --> P2
    
    P1 --> P2
    P2 --> P3
    P3 --> P4
    
    P2 --> S1
    P2 --> S2
    P3 --> S3
    P4 --> S4
    
    S1 --> O1
    S2 --> O1
    P4 --> O2
    P4 --> O3
    S4 --> O4
```

## 4. 服务依赖图

```mermaid
graph TD
    subgraph "核心服务"
        SM[服务管理器]
        RS[Rust系统]
        DB[数据库]
        WS[WebSocket]
        SC[任务调度器]
    end
    
    subgraph "API服务"
        FA[FastAPI应用]
        MW[中间件]
        RT[路由处理]
        EH[异常处理]
    end
    
    subgraph "前端服务"
        RA[React应用]
        SF[静态文件]
        SW[Service Worker]
    end
    
    subgraph "基础服务"
        LG[日志系统]
        CF[配置管理]
        MT[监控系统]
        CH[健康检查]
    end
    
    SM --> RS
    SM --> DB
    SM --> WS
    SM --> SC
    
    FA --> SM
    FA --> MW
    MW --> RT
    RT --> EH
    
    RA --> FA
    RA --> SF
    RA --> SW
    
    SM --> LG
    SM --> CF
    SM --> MT
    SM --> CH
    
    style SM fill:#e1f5fe
    style FA fill:#f3e5f5
    style RA fill:#e8f5e8
```

## 5. 部署架构图

```mermaid
graph TB
    subgraph "生产环境"
        subgraph "负载均衡层"
            LB[负载均衡器]
            NG[Nginx集群]
        end
        
        subgraph "应用层"
            subgraph "容器集群"
                DC1[Docker容器1]
                DC2[Docker容器2]
                DC3[Docker容器3]
            end
        end
        
        subgraph "数据层"
            DB1[主数据库]
            DB2[从数据库]
            RD[Redis缓存]
        end
        
        subgraph "监控层"
            PM[Prometheus]
            GF[Grafana]
            AL[AlertManager]
        end
    end
    
    subgraph "开发环境"
        DEV[开发服务器]
        DEVDB[开发数据库]
    end
    
    subgraph "测试环境"
        TEST[测试服务器]
        TESTDB[测试数据库]
    end
    
    LB --> NG
    NG --> DC1
    NG --> DC2
    NG --> DC3
    
    DC1 --> DB1
    DC2 --> DB1
    DC3 --> DB1
    DB1 --> DB2
    
    DC1 --> RD
    DC2 --> RD
    DC3 --> RD
    
    DC1 --> PM
    DC2 --> PM
    DC3 --> PM
    PM --> GF
    PM --> AL
```

## 6. 网络拓扑图

```mermaid
graph LR
    subgraph "外网"
        INT[互联网]
        CDN[CDN]
    end
    
    subgraph "DMZ区"
        FW[防火墙]
        LB[负载均衡]
        NG[Nginx]
    end
    
    subgraph "应用区"
        APP1[应用服务器1]
        APP2[应用服务器2]
        APP3[应用服务器3]
    end
    
    subgraph "数据区"
        DB[数据库服务器]
        CACHE[缓存服务器]
        FILE[文件服务器]
    end
    
    subgraph "管理区"
        MON[监控服务器]
        LOG[日志服务器]
        BACKUP[备份服务器]
    end
    
    INT --> CDN
    CDN --> FW
    FW --> LB
    LB --> NG
    NG --> APP1
    NG --> APP2
    NG --> APP3
    
    APP1 --> DB
    APP2 --> DB
    APP3 --> DB
    
    APP1 --> CACHE
    APP2 --> CACHE
    APP3 --> CACHE
    
    APP1 --> FILE
    APP2 --> FILE
    APP3 --> FILE
    
    APP1 --> MON
    APP2 --> MON
    APP3 --> MON
    
    APP1 --> LOG
    APP2 --> LOG
    APP3 --> LOG
    
    DB --> BACKUP
    FILE --> BACKUP
```

## 7. 状态机图

```mermaid
stateDiagram-v2
    [*] --> Initializing: 系统启动
    
    Initializing --> Starting: 初始化完成
    Initializing --> Failed: 初始化失败
    
    Starting --> Running: 所有服务启动成功
    Starting --> Failed: 服务启动失败
    
    Running --> Healthy: 健康检查通过
    Running --> Degraded: 部分服务异常
    Running --> Stopping: 收到停止信号
    
    Healthy --> Degraded: 检测到异常
    Healthy --> Stopping: 收到停止信号
    
    Degraded --> Healthy: 服务恢复正常
    Degraded --> Failed: 关键服务失败
    Degraded --> Stopping: 收到停止信号
    
    Stopping --> Stopped: 优雅关闭完成
    Stopping --> Failed: 关闭过程异常
    
    Failed --> Restarting: 自动重启
    Failed --> Stopped: 手动停止
    
    Restarting --> Initializing: 重启完成
    Restarting --> Failed: 重启失败
    
    Stopped --> [*]: 系统关闭
```

## 8. 组件生命周期图

```mermaid
gantt
    title 系统组件启动时序图
    dateFormat X
    axisFormat %s
    
    section 基础组件
    配置加载        :done, config, 0, 1s
    日志系统        :done, logging, 1s, 2s
    
    section 核心服务
    数据库连接      :done, database, 2s, 4s
    Rust模块初始化  :done, rust, 3s, 6s
    
    section 应用服务
    FastAPI启动     :done, fastapi, 6s, 8s
    WebSocket服务   :done, websocket, 8s, 10s
    任务调度器      :done, scheduler, 10s, 12s
    
    section 前端服务
    静态文件服务    :done, static, 12s, 13s
    React应用就绪   :done, react, 13s, 14s
    
    section 监控服务
    健康检查        :done, health, 14s, 15s
    系统监控        :done, monitor, 15s, 16s
```

## 9. 错误处理流程图

```mermaid
flowchart TD
    A[异常发生] --> B{异常类型}
    
    B -->|系统异常| C[记录错误日志]
    B -->|业务异常| D[记录警告日志]
    B -->|网络异常| E[记录网络日志]
    
    C --> F{是否关键异常}
    D --> G[返回错误响应]
    E --> H{是否需要重试}
    
    F -->|是| I[触发告警]
    F -->|否| J[继续处理]
    
    H -->|是| K[执行重试逻辑]
    H -->|否| L[返回失败响应]
    
    I --> M[发送通知]
    J --> N[记录状态]
    K --> O{重试成功}
    
    O -->|是| P[返回成功响应]
    O -->|否| Q[达到重试上限]
    
    Q --> R[返回失败响应]
    
    G --> S[客户端处理]
    L --> S
    P --> S
    R --> S
    
    M --> T[运维介入]
    N --> U[继续监控]
    S --> V[用户反馈]
```

## 10. 性能监控架构图

```mermaid
graph TB
    subgraph "数据收集层"
        A1[应用指标]
        A2[系统指标]
        A3[业务指标]
        A4[日志数据]
    end
    
    subgraph "数据传输层"
        B1[Prometheus Agent]
        B2[Fluentd]
        B3[StatsD]
    end
    
    subgraph "数据存储层"
        C1[Prometheus TSDB]
        C2[Elasticsearch]
        C3[InfluxDB]
    end
    
    subgraph "数据处理层"
        D1[数据聚合]
        D2[数据清洗]
        D3[异常检测]
    end
    
    subgraph "可视化层"
        E1[Grafana仪表板]
        E2[Kibana日志分析]
        E3[自定义报表]
    end
    
    subgraph "告警层"
        F1[AlertManager]
        F2[邮件通知]
        F3[短信通知]
        F4[Webhook]
    end
    
    A1 --> B1
    A2 --> B1
    A3 --> B3
    A4 --> B2
    
    B1 --> C1
    B2 --> C2
    B3 --> C3
    
    C1 --> D1
    C2 --> D2
    C3 --> D3
    
    D1 --> E1
    D2 --> E2
    D3 --> E3
    
    D1 --> F1
    D2 --> F1
    D3 --> F1
    
    F1 --> F2
    F1 --> F3
    F1 --> F4
```

## 11. 安全架构图

```mermaid
graph TB
    subgraph "安全边界"
        subgraph "外部安全"
            WAF[Web应用防火墙]
            DDoS[DDoS防护]
            SSL[SSL/TLS加密]
        end
        
        subgraph "网络安全"
            FW[防火墙]
            VPN[VPN接入]
            IDS[入侵检测]
        end
        
        subgraph "应用安全"
            AUTH[身份认证]
            AUTHZ[权限控制]
            CSRF[CSRF防护]
            XSS[XSS防护]
        end
        
        subgraph "数据安全"
            ENCRYPT[数据加密]
            BACKUP[数据备份]
            AUDIT[审计日志]
        end
        
        subgraph "运行时安全"
            SANDBOX[沙箱隔离]
            MONITOR[安全监控]
            INCIDENT[事件响应]
        end
    end
    
    WAF --> FW
    DDoS --> FW
    SSL --> AUTH
    
    FW --> AUTH
    VPN --> AUTH
    IDS --> MONITOR
    
    AUTH --> AUTHZ
    AUTHZ --> CSRF
    CSRF --> XSS
    
    XSS --> ENCRYPT
    ENCRYPT --> BACKUP
    BACKUP --> AUDIT
    
    AUDIT --> SANDBOX
    SANDBOX --> MONITOR
    MONITOR --> INCIDENT
```

## 12. 扩展性架构图

```mermaid
graph LR
    subgraph "当前架构"
        subgraph "单体应用"
            APP[Reachy Mini应用]
            DB[SQLite数据库]
        end
    end
    
    subgraph "水平扩展"
        subgraph "多实例部署"
            APP1[应用实例1]
            APP2[应用实例2]
            APP3[应用实例3]
            LB[负载均衡器]
        end
        
        subgraph "数据库集群"
            MASTER[主数据库]
            SLAVE1[从数据库1]
            SLAVE2[从数据库2]
        end
    end
    
    subgraph "微服务架构"
        subgraph "服务拆分"
            API[API网关]
            AUTH_SVC[认证服务]
            HEALTH_SVC[健康检查服务]
            MONITOR_SVC[监控服务]
        end
        
        subgraph "服务发现"
            CONSUL[Consul]
            ETCD[etcd]
        end
    end
    
    subgraph "云原生架构"
        subgraph "容器编排"
            K8S[Kubernetes]
            DOCKER[Docker容器]
        end
        
        subgraph "服务网格"
            ISTIO[Istio]
            ENVOY[Envoy代理]
        end
    end
    
    APP --> LB
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> MASTER
    APP2 --> MASTER
    APP3 --> MASTER
    MASTER --> SLAVE1
    MASTER --> SLAVE2
    
    API --> AUTH_SVC
    API --> HEALTH_SVC
    API --> MONITOR_SVC
    
    AUTH_SVC --> CONSUL
    HEALTH_SVC --> CONSUL
    MONITOR_SVC --> CONSUL
    
    K8S --> DOCKER
    ISTIO --> ENVOY
```

## 图表说明

### 图表类型说明

1. **系统总体架构图**: 展示了系统的分层架构和各层之间的关系
2. **组件交互图**: 描述了用户请求的完整处理流程
3. **数据流图**: 展示了数据在系统中的流转过程
4. **服务依赖图**: 显示了各个服务组件之间的依赖关系
5. **部署架构图**: 描述了系统在不同环境中的部署结构
6. **网络拓扑图**: 展示了网络层面的架构设计
7. **状态机图**: 描述了系统的各种状态和状态转换
8. **组件生命周期图**: 展示了系统启动时各组件的启动顺序和时间
9. **错误处理流程图**: 描述了系统的错误处理机制
10. **性能监控架构图**: 展示了系统监控和告警的架构
11. **安全架构图**: 描述了系统的安全防护体系
12. **扩展性架构图**: 展示了系统的扩展演进路径

### 使用建议

- **开发阶段**: 重点关注组件交互图和数据流图
- **部署阶段**: 重点关注部署架构图和网络拓扑图
- **运维阶段**: 重点关注性能监控架构图和错误处理流程图
- **扩展阶段**: 重点关注扩展性架构图

### 图表更新

这些图表应该随着系统的演进而更新，建议：

1. **定期审查**: 每个版本发布后审查图表的准确性
2. **及时更新**: 架构变更时及时更新相关图表
3. **版本控制**: 将图表纳入版本控制系统
4. **文档同步**: 确保图表与技术文档保持同步

通过这些架构图表，可以更好地理解 Reachy Mini 系统的整体设计和各组件之间的关系，为系统的开发、部署、运维和扩展提供重要参考。