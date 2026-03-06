# 部署指南

Feishu Organization Sync Service 部署说明

## 环境要求

- Docker >= 20.0
- Docker Compose >= 2.0
- 飞书应用（已开通通讯录权限）

## 快速开始

### 1. 克隆代码

```bash
git clone https://github.com/mark-devlab2/feishu-org-sync.git
cd feishu-org-sync
```

### 2. 配置环境变量

复制示例配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 飞书应用配置
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_DOMAIN=https://open.feishu.cn

# Webhook 加密密钥（可选，用于验证飞书请求）
WEBHOOK_ENCRYPT_KEY=your_encrypt_key

# 同步间隔（秒）
SYNC_INTERVAL=3600

# 数据库路径
DATABASE_PATH=/app/data/org_sync.db
```

### 3. 启动服务

使用 Docker Compose：

```bash
docker-compose up -d
```

查看日志：

```bash
docker-compose logs -f
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 查看统计信息
curl http://localhost:8000/api/stats
```

---

## 飞书应用配置

### 1. 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 进入「控制台」→「创建应用」
3. 选择「企业自建应用」

### 2. 开启权限

在「权限管理」中添加以下权限：

**通讯录权限**:
- `contact:user.base:readonly` - 读取用户基本信息
- `contact:user.department:readonly` - 读取用户部门信息
- `contact:department.base:readonly` - 读取部门基础信息
- `contact:department.user:readonly` - 读取部门成员信息

**事件订阅权限**:
- `contact:user.created_v3` - 用户创建事件
- `contact:user.updated_v3` - 用户更新事件
- `contact:user.deleted_v3` - 用户删除事件
- `contact:department.created_v3` - 部门创建事件
- `contact:department.updated_v3` - 部门更新事件
- `contact:department.deleted_v3` - 部门删除事件

### 3. 配置事件订阅

在「事件订阅」中设置：

- **请求地址**: `http://your-server:8001/webhook`
- **加密密钥**: 与 `.env` 中的 `WEBHOOK_ENCRYPT_KEY` 一致

### 4. 发布应用

点击「版本管理与发布」→「创建版本」→「申请发布」

需要管理员审批后才能正常使用。

---

## 运行模式

### 模式1: 全功能模式（推荐）

同时运行 API、Webhook 和定时同步：

```bash
docker-compose up -d
```

服务端口：
- API 服务: `8000`
- Webhook 服务: `8001`

### 模式2: 仅 API 服务

```bash
docker run -p 8000:8000 \
  -e FEISHU_APP_ID=xxx \
  -e FEISHU_APP_SECRET=xxx \
  feishu-org-sync \
  python -m src.main --mode api
```

### 模式3: 仅同步服务

```bash
docker run \
  -e FEISHU_APP_ID=xxx \
  -e FEISHU_APP_SECRET=xxx \
  feishu-org-sync \
  python -m src.main --mode sync
```

---

## CLI 工具使用

进入容器使用 CLI：

```bash
# 查看部门列表
docker exec feishu-org-sync python -m src.cli.main departments

# 查看用户列表
docker exec feishu-org-sync python -m src.cli.main users

# 搜索用户
docker exec feishu-org-sync python -m src.cli.main search "张三"

# 查看统计
docker exec feishu-org-sync python -m src.cli.main stats

# 手动执行同步
docker exec feishu-org-sync python -m src.cli.main sync
```

---

## 数据备份

数据库文件位于容器内 `/app/data/org_sync.db`，已通过 volume 挂载到主机：

```bash
# 备份数据库
cp ./data/org_sync.db ./backup/org_sync_$(date +%Y%m%d).db

# 恢复数据库
cp ./backup/org_sync_20260306.db ./data/org_sync.db
```

---

## 故障排查

### 问题1: 无法获取 Token

检查：
- App ID 和 App Secret 是否正确
- 应用是否已发布
- 网络是否能访问飞书服务器

### 问题2: Webhook 接收不到事件

检查：
- 服务器是否有公网 IP 或域名
- 防火墙是否开放端口
- 飞书应用的事件订阅 URL 是否正确

### 问题3: 同步失败

查看日志：

```bash
docker-compose logs -f app
```

常见原因：
- 权限不足（检查应用权限）
- Token 过期（重启服务重新获取）
- 网络问题

---

## 更新升级

```bash
# 拉取最新代码
git pull origin master

# 重建镜像
docker-compose build

# 重启服务
docker-compose up -d
```
