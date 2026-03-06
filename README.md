# Feishu Organization Sync Service

飞书组织架构同步微服务 - 自动同步人员、部门信息到本地数据库。

## 🎯 项目目标

构建一个微服务，实现：
1. **定期全量同步** - 定时从飞书拉取组织架构数据
2. **实时增量更新** - 通过事件回调处理人员/部门变更
3. **Token 自动刷新** - OAuth Token 持续续期机制
4. **CLI 数据访问** - 支持命令行查询组织架构

## 🏗️ 技术架构

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    Feishu Open Platform                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   User API   │  │ Department   │  │   Events     │      │
│  │              │  │    API       │  │  Callback    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Feishu Org Sync Service (Python)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Full Sync    │  │ Event        │  │ Token        │      │
│  │ Scheduler    │  │ Handler      │  │ Manager      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite Database                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ users        │  │ departments  │  │ sync_logs    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| **语言** | Python 3.11+ | 生态丰富，飞书SDK完善 |
| **数据库** | SQLite | 免费、零配置、单文件、支持CLI |
| **Web框架** | FastAPI | 高性能、异步支持、自动文档 |
| **任务调度** | APScheduler | 轻量级、支持多种触发器 |
| **HTTP客户端** | httpx | 异步支持、现代化 |
| **CLI工具** | sqlite-utils + litecli | 强大的SQLite CLI体验 |
| **Token管理** | 自研 + schedule | 自动检测过期并刷新 |

## 📁 项目结构

```
feishu-org-sync/
├── README.md                 # 项目说明
├── requirements.txt          # Python依赖
├── config.yaml              # 配置文件
├── .env.example             # 环境变量模板
├── src/
│   ├── __init__.py
│   ├── main.py              # 服务入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── feishu_client.py     # 飞书API客户端
│   │   └── webhook_handler.py   # Webhook处理器
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── full_sync.py         # 全量同步
│   │   └── incremental_sync.py  # 增量同步
│   ├── auth/
│   │   ├── __init__.py
│   │   └── token_manager.py     # Token管理器
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py            # 数据模型
│   │   └── database.py          # 数据库操作
│   └── cli/
│       ├── __init__.py
│       └── org_cli.py           # CLI工具
├── scripts/
│   ├── start.sh             # 启动服务
│   ├── stop.sh              # 停止服务
│   └── setup.sh             # 初始化安装
└── tests/
    └── test_*.py            # 测试文件
```

## 🔄 Token 刷新机制

### 方案设计

```python
class TokenManager:
    """
    Token 自动刷新管理器
    
    策略:
    1. Token 有效期通常为 2 小时 (7200秒)
    2. 提前 10 分钟刷新（避免边界问题）
    3. 使用 refresh_token 换取新 token
    4. 失败时重试 3 次，间隔 5 秒
    5. 持久化存储到 SQLite，服务重启不丢失
    """
    
    REFRESH_BEFORE_EXPIRY = 600  # 提前10分钟刷新
    MAX_RETRY = 3
    RETRY_DELAY = 5
```

### 刷新流程

```
检查 Token 过期时间
    │
    ▼
是否小于 10 分钟？ ──否──> 继续使用当前 Token
    │是
    ▼
调用 refresh_token API
    │
    ├─成功─> 更新数据库中的 Token
    │         更新内存中的 Token
    │         记录日志
    │
    └─失败─> 重试 (最多3次)
              仍失败则告警
```

## 📊 数据库设计

### 表结构

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feishu_user_id TEXT UNIQUE NOT NULL,  -- 飞书用户ID
    open_id TEXT UNIQUE,                   -- 开放ID
    union_id TEXT,                         -- 统一ID
    name TEXT NOT NULL,                    -- 姓名
    email TEXT,                            -- 邮箱
    mobile TEXT,                           -- 手机号
    avatar_url TEXT,                       -- 头像URL
    status INTEGER DEFAULT 1,              -- 状态: 1-在职, 2-离职
    department_ids TEXT,                   -- 所属部门ID列表(JSON数组)
    leader_user_id TEXT,                   -- 直属上级ID
    city TEXT,                             -- 城市
    country TEXT,                          -- 国家
    employee_type TEXT,                    -- 员工类型
    employee_no TEXT,                      -- 工号
    gender INTEGER,                        -- 性别: 1-男, 2-女
    join_time DATETIME,                    -- 入职时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_sync_at DATETIME                  -- 最后同步时间
);

-- 部门表
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feishu_dept_id TEXT UNIQUE NOT NULL,   -- 飞书部门ID
    parent_department_id TEXT,             -- 父部门ID
    name TEXT NOT NULL,                    -- 部门名称
    name_en TEXT,                          -- 英文名称
    leader_user_id TEXT,                   -- 部门负责人ID
    order INTEGER DEFAULT 0,               -- 排序
    member_count INTEGER DEFAULT 0,        -- 成员数量
    status INTEGER DEFAULT 1,              -- 状态: 1-正常, 0-删除
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_sync_at DATETIME                  -- 最后同步时间
);

-- Token 表
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at DATETIME NOT NULL,
    token_type TEXT DEFAULT 'tenant',      -- tenant/user
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 同步日志表
CREATE TABLE sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,               -- full/incremental/event
    status TEXT NOT NULL,                  -- success/failed
    total_users INTEGER DEFAULT 0,
    total_departments INTEGER DEFAULT 0,
    added_users INTEGER DEFAULT 0,
    updated_users INTEGER DEFAULT 0,
    deleted_users INTEGER DEFAULT 0,
    error_message TEXT,
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds INTEGER
);

-- 事件处理日志
CREATE TABLE event_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,              -- user_add/user_update/dept_add/...
    event_data TEXT,                       -- 事件数据JSON
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',         -- pending/processing/success/failed
    error_message TEXT
);
```

## 🚀 同步策略

### 1. 全量同步 (Full Sync)

**频率**: 每天凌晨 2:00

**流程**:
```
开始全量同步
    │
    ▼
获取所有部门列表
    │
    ▼
遍历每个部门 ──> 获取部门成员
    │                │
    │                ▼
    │            批量插入/更新用户
    │                │
    ▼                │
保存部门信息 <─────┘
    │
    ▼
标记已删除的用户/部门
    │
    ▼
记录同步日志
```

### 2. 增量同步 (Event-Driven)

**事件类型**:
- `contact.user.created_v3` - 用户创建
- `contact.user.updated_v3` - 用户更新
- `contact.user.deleted_v3` - 用户删除
- `contact.department.created_v3` - 部门创建
- `contact.department.updated_v3` - 部门更新
- `contact.department.deleted_v3` - 部门删除

**Webhook 处理**:
```python
@app.post("/webhook/feishu")
async def handle_feishu_event(request: Request):
    event = await request.json()
    
    # 验证签名
    if not verify_signature(request):
        raise HTTPException(401, "Invalid signature")
    
    # 处理挑战请求（首次配置）
    if event.get("type") == "url_verification":
        return {"challenge": event["challenge"]}
    
    # 处理业务事件
    event_type = event.get("header", {}).get("event_type")
    handler = EVENT_HANDLERS.get(event_type)
    
    if handler:
        await handler(event)
    
    return {"status": "ok"}
```

## 🛠️ CLI 工具

### 功能设计

```bash
# 查询用户
org-cli user list                    # 列出所有用户
org-cli user get <user_id>           # 获取用户信息
org-cli user search <keyword>        # 搜索用户
org-cli user dept <dept_id>          # 获取部门成员

# 查询部门
org-cli dept list                    # 列出所有部门
org-cli dept tree                    # 显示部门树形结构
org-cli dept get <dept_id>           # 获取部门信息

# 同步管理
org-cli sync status                  # 查看同步状态
org-cli sync now                     # 立即执行同步
org-cli sync logs                    # 查看同步日志

# 数据库操作
org-cli db query "SELECT * FROM users LIMIT 10"
org-cli db shell                     # 进入交互式 SQL shell
```

## 📦 部署方案

### 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/mark-devlab2/feishu-org-sync.git
cd feishu-org-sync

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入飞书应用凭证

# 4. 初始化数据库
python -m src.db.init

# 5. 启动服务
./scripts/start.sh
```

### 生产环境

使用 Docker Compose 部署:

```yaml
version: '3.8'
services:
  feishu-sync:
    build: .
    container_name: feishu-org-sync
    restart: unless-stopped
    environment:
      - FEISHU_APP_ID=${FEISHU_APP_ID}
      - FEISHU_APP_SECRET=${FEISHU_APP_SECRET}
      - DATABASE_URL=/data/org.db
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
```

## 🔒 安全考虑

1. **Token 加密存储** - 数据库中的 Token 使用 AES 加密
2. **Webhook 签名验证** - 防止伪造请求
3. **IP 白名单** - 仅允许飞书服务器 IP 访问 Webhook
4. **最小权限原则** - 飞书应用仅申请必要权限

## 📋 开发计划

### Phase 1: 基础架构 (Week 1)
- [ ] 项目初始化和 GitHub 仓库
- [ ] SQLite 数据库设计和初始化
- [ ] Token 管理机制
- [ ] 飞书 API 客户端封装

### Phase 2: 同步功能 (Week 2)
- [ ] 全量同步实现
- [ ] Webhook 事件处理
- [ ] 增量同步逻辑
- [ ] 同步日志记录

### Phase 3: CLI 和优化 (Week 3)
- [ ] CLI 工具开发
- [ ] 性能优化
- [ ] 错误处理和重试
- [ ] 监控和告警

### Phase 4: 测试和文档 (Week 4)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 完整文档
- [ ] 部署脚本

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

## 📄 License

MIT License
