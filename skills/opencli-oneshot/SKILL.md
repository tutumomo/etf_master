---
name: opencli-oneshot
description: Use when quickly generating a single OpenCLI command from a specific URL and goal description. 4-step process — open page, capture API, write YAML adapter, test. For full site exploration, use opencli-explorer instead.
tags: [opencli, adapter, quick-start, yaml, cli, one-shot, automation]
---

# CLI-ONESHOT — 单点快速 CLI 生成

> 给一个 URL + 一句话描述，4 步生成一个 CLI 命令。
> 完整探索式开发请看 [opencli-explorer skill](../opencli-explorer/SKILL.md)。

---

## 输入

| 项目 | 示例 |
|------|------|
| **URL** | `https://x.com/jakevin7/lists` |
| **Goal** | 获取我的 Twitter Lists |

---

## 流程

### Step 1: 打开页面 + 抓包

```
1. browser_navigate → 打开目标 URL
2. 等待 3-5 秒（让页面加载完、API 请求触发）
3. browser_network_requests → 筛选 JSON API
```

**关键**：只关注返回 `application/json` 的请求，忽略静态资源。
如果没有自动触发 API，手动点击目标按钮/标签再抓一次。

### Step 2: 锁定一个接口

从抓包结果中找到**那个**目标 API。看这几个字段：

| 字段 | 关注什么 |
|------|----------|
| URL | API 路径 pattern（如 `/i/api/graphql/xxx/ListsManagePinTimeline`） |
| Method | GET / POST |
| Headers | 有 Cookie? Bearer? CSRF? 自定义签名? |
| Response | 数据在哪个路径（如 `data.list.lists`） |

### Step 3: 验证接口能复现

在 `browser_evaluate` 中用 `fetch` 复现请求：

```javascript
// Tier 2 (Cookie): 大多数情况
fetch('/api/endpoint', { credentials: 'include' }).then(r => r.json())

// Tier 3 (Header): 如 Twitter 需要额外 header
const ct0 = document.cookie.match(/ct0=([^;]+)/)?.[1];
fetch('/api/endpoint', {
  headers: { 'Authorization': 'Bearer ...', 'X-Csrf-Token': ct0 },
  credentials: 'include'
}).then(r => r.json())
```

如果 fetch 能拿到数据 → 用 YAML 或简单 TS adapter。
如果 fetch 拿不到（签名/风控）→ 需要更复杂方案。

### Step 4: 写适配器 + 测试

**YAML 适配器**（简单场景）：
```yaml
name: my-command
description: "获取 X Lists"
command: opencli run my-command
steps:
  - open: "{{url}}"
  - wait: 3000
  - api: /i/api/graphql/xxx/ListsManagePinTimeline
  - extract: data.list.lists
```

**测试**：
```bash
opencli run my-command
```