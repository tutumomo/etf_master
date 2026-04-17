---
phase: 10-dynamic-charts
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [scripts/etf_core/data_engine.py, scripts/etf_tw.py]
autonomous: true
requirements: [1, 3]
user_setup: []

must_haves:
  truths:
    - "API 支援週期參數 d/w/m/q/y"
    - "計算出的 MA5/MA20/MA60 指標數值正確"
  artifacts:
    - path: "scripts/etf_core/data_engine.py"
      provides: "週期性資料取得與技術指標計算邏輯"
    - path: "scripts/etf_tw.py"
      provides: "更新 API 路由參數定義"
  key_links:
    - from: "scripts/etf_tw.py"
      to: "scripts/etf_core/data_engine.py"
      via: "API 參數傳遞與資料處理"
---

<objective>
實現後端資料處理引擎對多週期 K 線數據的支援，以及對技術指標 (MA) 的動態計算。

Purpose: 提供前端所需的各週期 K 線資料與技術指標數值。
Output: 更新後的 API 資料引擎與路由處理。
</objective>

<execution_context>
@$HOME/.gemini/get-shit-done/workflows/execute-plan.md
@$HOME/.gemini/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@scripts/etf_core/data_engine.py
@scripts/etf_tw.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 實作多週期資料擷取與 MA 計算</name>
  <files>scripts/etf_core/data_engine.py, scripts/tests/test_data_engine.py</files>
  <behavior>
    - Test 1: 驗證 get_history(symbol, period='w') 回傳正確週期數據
    - Test 2: 驗證 get_ma(data, [5, 20, 60]) 計算出正確移動平均線值
  </behavior>
  <action>修改 scripts/etf_core/data_engine.py，增加對週期參數 (d, w, m, q, y) 的解析與對應的 yfinance/sinopac 資料轉換。增加技術指標計算邏輯，確保回傳包含 MA5, MA20, MA60 的結構。</action>
  <verify>
    <automated>pytest scripts/tests/test_data_engine.py</automated>
  </verify>
  <done>資料引擎支援各週期切換與技術指標運算</done>
</task>

<task type="auto">
  <name>Task 2: 更新 API 路由支援 period 參數</name>
  <files>scripts/etf_tw.py</files>
  <action>更新 /api/history/{symbol} 路由處理器，接收 period 查詢參數，並呼叫 data_engine 取得對應週期數據。</action>
  <verify>
    <automated>curl "http://localhost:5000/api/history/0050?period=w"</automated>
  </verify>
  <done>API 可透過 URL 參數取得不同週期資料</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Client→API | 用戶輸入 period 參數，可能為異常字串 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-01 | Tampering | API Input | mitigate | 使用白名單檢查 period 參數是否為 [d,w,m,q,y] |
</threat_model>

<verification>
確保後端 API 能正常處理週期參數，且運算後的資料結構正確。
</verification>

<success_criteria>
API 回傳資料包含 Open, High, Low, Close 以及 MA5, MA20, MA60。
</success_criteria>

<output>
建立 .planning/phases/dynamic-charts/10-dynamic-charts-01-SUMMARY.md
</output>
