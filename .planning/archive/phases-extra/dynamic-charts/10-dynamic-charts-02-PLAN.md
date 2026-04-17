---
phase: 10-dynamic-charts
plan: 02
type: execute
wave: 2
depends_on: [10-dynamic-charts-01]
files_modified: [dashboard/templates/index.html, dashboard/static/js/chart.js]
autonomous: false
requirements: [2, 3, 5]
user_setup: []

must_haves:
  truths:
    - "圖表上方出現週期切換按鈕"
    - "點擊按鈕後圖表動態載入新數據"
    - "MA5, MA20, MA60 線條顯示清晰"
  artifacts:
    - path: "dashboard/templates/index.html"
      provides: "週期切換 UI 按鈕群"
    - path: "dashboard/static/js/chart.js"
      provides: "前端資料抓取與繪圖邏輯"
  key_links:
    - from: "dashboard/static/js/chart.js"
      to: "/api/history"
      via: "fetch 請求帶入 period 參數"
---

<objective>
完成前端圖表介面的週期切換功能，並整合技術指標線繪製。

Purpose: 提供使用者互動式的 K 線圖切換介面。
Output: 動態圖表切換功能與技術指標疊加。
</objective>

<execution_context>
@$HOME/.gemini/get-shit-done/workflows/execute-plan.md
@$HOME/.gemini/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@dashboard/templates/index.html
@dashboard/static/js/chart.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: 前端 UI 週期切換按鈕</name>
  <files>dashboard/templates/index.html</files>
  <action>在 index.html 圖表上方新增按鈕群組 (日/週/月/季/年)，並為每個按鈕綁定 period 資料屬性。</action>
  <verify>
    <automated>確認頁面上有 id 為 period-buttons 的元素</automated>
  </verify>
  <done>介面顯示切換按鈕</done>
</task>

<task type="auto">
  <name>Task 2: 非同步資料更新與技術指標渲染</name>
  <files>dashboard/static/js/chart.js</files>
  <action>編寫 JavaScript 邏輯：監聽按鈕點擊事件，發起對 /api/history/{symbol}?period={val} 的 fetch 請求。請求成功後，使用 Chart.js (或現有圖表庫) 更新 series，並繪製 MA5/MA20/MA60 的 trace lines。</action>
  <verify>
    <automated>curl -s "http://localhost:5000/api/history/0050?period=w" | grep -q "MA5"</automated>
  </verify>
  <done>圖表隨按鈕切換並正確顯示 MA 指標</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>動態 K 線圖切換與技術指標</what-built>
  <how-to-verify>
    1. 開啟 http://localhost:5000
    2. 點擊不同的週期切換按鈕。
    3. 確認圖表數據更新且無閃爍。
    4. 確認 MA5, MA20, MA60 三條線均正確顯示。
  </how-to-verify>
  <resume-signal>Type "approved" 或報告問題</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Client→API | 請求參數合法性 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-02 | Information Disclosure | Client UI | accept | 前端僅顯示接收到的指標資訊，無敏感資料外洩風險 |
</threat_model>

<verification>
確保前端能正確處理 API 回傳的 MA 資料並動態繪製。
</verification>

<success_criteria>
使用者能順利切換週期，且繪製圖表無誤。
</success_criteria>

<output>
建立 .planning/phases/dynamic-charts/10-dynamic-charts-02-SUMMARY.md
</output>
