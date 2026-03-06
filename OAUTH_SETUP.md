# OAuth 授权登录方案

完整的飞书 OAuth 授权流程，获取并维护用户 Access Token。

## 🎯 目标

- 完成用户 OAuth 授权
- 自动获取和刷新 Access Token
- Token 持久化存储
- 持续维护（自动续期）

---

## 📋 前置条件

1. **飞书应用已创建**
   - App ID: `cli_a922e702a6f8dcd4`
   - App Secret: `ZRrAYTrhZasv0inR66WyvckrkLJNAoVg`

2. **已开启权限**
   - `contact:user.base:readonly` - 读取用户基本信息
   - `auth:user.id:readonly` - 获取用户ID

3. **配置 OAuth 回调地址**
   - 在飞书应用后台 →「安全设置」→「OAuth 2.0 回调地址」
   - 添加: `http://localhost:3000/callback`

---

## 🚀 快速开始

### 方式1: 使用 lark-mcp CLI（推荐）

```bash
# 安装飞书 MCP 工具（如果还没安装）
npm install -g @larksuiteoapi/lark-mcp

# 执行登录
lark-mcp login \
  --app-id cli_a922e702a6f8dcd4 \
  --app-secret ZRrAYTrhZasv0inR66WyvckrkLJNAoVg
```

**流程：**
1. 终端显示授权链接
2. 浏览器自动打开（或手动复制链接）
3. 你点击「同意授权」
4. Token 自动保存到本地

### 方式2: 使用 feishu-token-manager

```bash
# 进入项目目录
cd ~/projects/feishu-token-manager

# 启动 Token 管理服务
docker-compose up -d

# 查看状态
docker exec feishu-token-manager python -m src.cli status
```

---

## 🔧 详细授权流程

### Step 1: 构建授权链接

```
https://open.feishu.cn/open-apis/authen/v1/index?app_id=cli_a922e702a6f8dcd4&redirect_uri=http://localhost:3000/callback
```

### Step 2: 用户授权

1. 浏览器打开授权链接
2. 飞书显示授权页面：
   - 应用名称：你的应用名
   - 请求权限：读取用户信息
3. 点击「同意授权」

### Step 3: 获取授权码

授权成功后，浏览器重定向到：
```
http://localhost:3000/callback?code=xxx&state=yyy
```

提取 `code` 参数。

### Step 4: 换取 Access Token

```bash
curl -X POST https://open.feishu.cn/open-apis/authen/v1/access_token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "上一步获取的code"
  }'
```

响应示例：
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "access_token": "u-xxx",
    "refresh_token": "ur-xxx",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user_id": "ou_xxx"
  }
}
```

---

## 🔄 Token 自动刷新

### 刷新机制

Token 有效期为 7200 秒（2小时），需要在过期前刷新。

**自动刷新策略：**
- 提前 10 分钟（600秒）刷新
- 使用 `refresh_token` 换取新 token
- 失败时重试 3 次

### 刷新 API

```bash
curl -X POST https://open.feishu.cn/open-apis/authen/v1/refresh_access_token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {tenant_access_token}" \
  -d '{
    "grant_type": "refresh_token",
    "refresh_token": "ur-xxx"
  }'
```

---

## 💾 Token 存储

Token 保存在本地文件：`~/.feishu/tokens.json`

格式：
```json
{
  "tenant_access_token": {
    "token": "t-xxx",
    "expires_at": "2026-03-06T14:00:00",
    "created_at": "2026-03-06T12:00:00"
  },
  "ou_ff3eec6f004b3ed7e012853c264244aa": {
    "access_token": "u-xxx",
    "refresh_token": "ur-xxx",
    "expires_at": "2026-03-06T13:50:00",
    "created_at": "2026-03-06T11:50:00"
  }
}
```

---

## 🛠️ 实施方案

### 方案A: 交互式授权（当前推荐）

```bash
# 1. 运行授权脚本
python scripts/oauth_login.py

# 2. 按提示操作
# - 复制链接到浏览器
# - 点击授权
# - 返回终端确认

# 3. 验证授权结果
python -m src.cli status
```

### 方案B: 自动化服务（后续优化）

部署 Token 刷新服务：

```bash
# 启动自动刷新服务
docker-compose -f docker-compose.token.yml up -d

# 查看日志
docker logs -f feishu-token-manager
```

---

## ✅ 验证授权成功

```bash
# 查看已保存的用户 token
python -m src.cli list-users

# 获取指定用户的 access token
python -m src.cli get <user_id>

# 测试调用飞书 API
curl https://open.feishu.cn/open-apis/contact/v3/users/me \
  -H "Authorization: Bearer $(python -m src.cli get <user_id>)"
```

---

## 🚨 常见问题

### Q1: 授权页面显示「应用未发布」

**解决**: 
1. 进入飞书开放平台 → 应用管理
2. 点击「版本管理与发布」
3. 创建版本并申请发布
4. 联系管理员审批

### Q2: Token 刷新失败

**原因**: 
- refresh_token 已过期（通常30天）
- 用户取消了授权

**解决**: 重新执行授权流程

### Q3: 如何撤销授权

```bash
# 清除本地 token
python -m src.cli clear

# 或在飞书客户端 → 设置 → 隐私 → 授权管理 → 撤销应用授权
```

---

## 📞 下一步

1. **立即执行**: 运行 `lark-mcp login` 完成首次授权
2. **验证功能**: 使用获取的 token 调用飞书 API
3. **部署服务**: 启动 token-manager 实现自动刷新

需要我协助执行授权流程吗？
