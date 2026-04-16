---
name: opencli-explorer
description: Use when creating a new OpenCLI adapter from scratch, adding support for a new website or platform, or exploring a site's API endpoints via browser DevTools. Covers API discovery workflow, authentication strategy selection, YAML/TS adapter writing, and testing.
tags: [opencli, adapter, browser, api-discovery, cli, web-scraping, automation]
---

# CLI-EXPLORER — 适配器探索式开发完全指南

> 本文档教你（或 AI Agent）如何为 OpenCLI 添加一个新网站的命令。  
> 从零到发布，覆盖 API 发现、方案选择、适配器编写、测试验证全流程。

> [!TIP]
> **只想为一个具体页面快速生成一个命令？** 看 [opencli-oneshot skill](../opencli-oneshot/SKILL.md)（~150 行，4 步搞定）。
> 本文档适合从零探索一个新站点的完整流程。

---

## AI Agent 开发者必读：用浏览器探索

> [!CAUTION]
> **你（AI Agent）必须通过浏览器打开目标网站去探索！**  
> 不要只靠 `opencli explore` 命令或静态分析来发现 API。  
> 你拥有浏览器工具，必须主动用它们浏览网页、观察网络请求、模拟用户交互。

### 为什么？

很多 API 是**懒加载**的（用户必须点击某个按钮/标签才会触发网络请求）。字幕、评论、关注列表等深层数据不会在页面首次加载时出现在 Network 面板中。**如果你不主动去浏览和交互页面，你永远发现不了这些 API。**

### AI Agent 探索工作流（必须遵循）

| 步骤 | 工具 | 做什么 |
|------|------|--------|
| 0. 打开浏览器 | `browser_navigate` | 导航到目标页面 |
| 1. 观察页面 | `browser_snapshot` | 观察可交互元素（按钮/标签/链接） |
| 2. 首次抓包 | `browser_network_requests` | 筛选 JSON API 端点，记录 URL pattern |
| 3. 模拟交互 | `browser_click` + `browser_wait_for` | 点击"字幕""评论""关注"等按钮 |
| 4. 二次抓包 | `browser_network_requests` | 对比步骤 2，找出新触发的 API |
| 5. 验证 API | `browser_evaluate` | `fetch(url, {credentials:'include'})` 测试返回结构 |
| 6. 写代码 | — | 基于确认的 API 写适配器 |

### 常犯错误

| ❌ 错误做法 | ✅ 正确做法 |
|------------|------------|
| 只用 `opencli explore` 命令，等结果自动出来 | 用浏览器工具打开页面，主动浏览 |
| 直接在代码里 `fetch(url)`，不看浏览器实际请求 | 先在浏览器中确认 API 可用，再写代码 |
| 页面打开后直接抓包，期望所有 API 都出现 | 模拟点击交互（展开评论/切换标签/加载更多） |
| 遇到 HTTP 200 但空数据就放弃 | 检查是否需要 Wbi 签名或特殊参数 |