# API 文档

Feishu Organization Sync Service HTTP API 接口文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`

---

## 健康检查

### GET /health

检查服务健康状态

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": "2026-03-06T12:00:00"
}
```

---

## 部门管理

### GET /api/departments

获取部门列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| parent_id | string | 否 | 父部门ID，默认查询所有 |
| name | string | 否 | 按名称搜索 |
| page | int | 否 | 页码，默认1 |
| size | int | 否 | 每页数量，默认20 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "od-xxx",
        "name": "技术部",
        "parent_id": null,
        "leader_user_id": "ou-xxx",
        "order": 0,
        "status": 1
      }
    ],
    "total": 10,
    "page": 1,
    "size": 20
  }
}
```

### GET /api/departments/{dept_id}

获取部门详情

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "id": "od-xxx",
    "name": "技术部",
    "parent_id": null,
    "children": [...]
  }
}
```

### GET /api/departments/tree

获取部门树形结构

**响应示例**:
```json
{
  "code": 0,
  "data": [
    {
      "id": "od-xxx",
      "name": "公司",
      "children": [
        {
          "id": "od-yyy",
          "name": "技术部",
          "children": [...]
        }
      ]
    }
  ]
}
```

---

## 用户管理

### GET /api/users

获取用户列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| department_id | string | 否 | 部门ID筛选 |
| name | string | 否 | 姓名搜索 |
| email | string | 否 | 邮箱搜索 |
| status | int | 否 | 状态：1-在职，2-离职 |
| page | int | 否 | 页码，默认1 |
| size | int | 否 | 每页数量，默认20 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "ou-xxx",
        "name": "张三",
        "email": "zhangsan@example.com",
        "department_id": "od-xxx",
        "status": 1
      }
    ],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

### GET /api/users/{user_id}

获取用户详情

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "id": "ou-xxx",
    "name": "张三",
    "email": "zhangsan@example.com",
    "mobile": "13800138000",
    "department_id": "od-xxx",
    "department_name": "技术部",
    "job_title": "工程师",
    "status": 1
  }
}
```

### GET /api/users/search

搜索用户

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 是 | 搜索关键词（至少2个字符） |

**响应示例**:
```json
{
  "code": 0,
  "data": [
    {
      "id": "ou-xxx",
      "name": "张三",
      "email": "zhangsan@example.com"
    }
  ]
}
```

---

## 统计信息

### GET /api/stats

获取组织架构统计

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "departments": {
      "total": 10
    },
    "users": {
      "active": 95,
      "inactive": 5,
      "total": 100
    },
    "timestamp": "2026-03-06T12:00:00"
  }
}
```

---

## Webhook 接收

### POST /webhook

接收飞书事件回调

**请求头**:
| 头信息 | 说明 |
|--------|------|
| X-Lark-Signature | 签名 |
| X-Lark-Request-Timestamp | 时间戳 |
| X-Lark-Request-Nonce | 随机数 |

**支持的事件类型**:
- `contact.user.created` - 用户创建
- `contact.user.updated` - 用户更新
- `contact.user.deleted` - 用户删除
- `contact.department.created` - 部门创建
- `contact.department.updated` - 部门更新
- `contact.department.deleted` - 部门删除

**响应示例**:
```json
{
  "code": 0,
  "msg": "success"
}
```
