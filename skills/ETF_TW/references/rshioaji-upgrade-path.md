# rshioaji 補強路徑與改進清單

> 目的：把 Shioaji Next-Gen（rshioaji）相關資訊整理成可追蹤、可落地、可避免走彎路的改進路線，作為 ETF_TW 後續擴充與驗證的參考文件。

---

## 1. 這份文件要解決什麼問題

ETF_TW 目前已具備：
- 以 `shioaji` / SinoPac 為核心的 live / paper 流程
- state-first 的 dashboard / 持倉 / 風控同步機制
- 盤感輔助層與即時市場資料整合

但隨著 `rshioaji` 出現，能力邊界開始擴大到：
- Python 原生綁定
- HTTP API
- SSE 串流
- CLI
- OpenAPI
- built-in dashboard
- 多語言 client

這份文件的目標不是「立刻切換主架構」，而是先把：
1. **哪些能力是真的可用**
2. **哪些能力適合補進 ETF_TW**
3. **哪些能力暫時不該碰 production path**

先釐清，避免後續反覆試錯。

---

## 2. 已確認的主要來源

以下資訊來源用來支撐本文件的整理：

### 官方 / 上游來源
- **rshioaji GitHub repository**
  - `https://github.com/Sinotrade/rshioaji`
- **Shioaji 官方 Quick Start**
  - `https://sinotrade.github.io/quickstart/`
- **Shioaji 官方 Upgrade / QA / Login / Terms / Order & Deal Event**
  - `https://sinotrade.github.io/upgrade/`
  - `https://sinotrade.github.io/qa/`
  - `https://sinotrade.github.io/tutor/login/`
  - `https://sinotrade.github.io/tutor/prepare/terms/`
  - `https://sinotrade.github.io/tutor/order_deal_event/`

### 觀察到的重點
- `rshioaji` 目前標示為 **Alpha Stage**，表示 API 與行為仍可能變動。
- `rshioaji` 提供 **Python 原生綁定**、**HTTP API + SSE**、**CLI**、**Dashboard**、**OpenAPI**。
- 官方 Shioaji 文件仍然是驗證交易流程、模擬流程、下單與授權條件的基礎真相源。

---

## 3. rshioaji 能補強 ETF_TW 的哪些面向

### 3.1 事件驅動與即時串流
ETF_TW 目前已有盤感與 state 同步，但多數流程仍偏向「同步刷新 / 定時同步」。

rshioaji 的 SSE / event 模式適合補強：
- 即時報價推播
- 委託狀態變化
- API 健康度監控
- 伺服器連線狀態
- 盤中異常事件通知

**價值**：減少輪詢，提升即時性，讓 dashboard / tape context 更接近事件驅動。

---

### 3.2 多語言與工具化介面
rshioaji 的 HTTP API / OpenAPI / CLI 讓交易能力不再侷限於 Python 腳本。

可用來補強：
- typed client 建置
- 交易流程自動化
- 其他語言整合（JS/TS、Go、Rust、Java/Kotlin 等）
- 外部工具鏈連接

**價值**：未來 ETF_TW 若要做跨服務整合，不必把所有能力都鎖死在 Python 腳本內。

---

### 3.3 交易伺服器與 dashboard
rshioaji 內建 dashboard 與 API server 的思路，適合和 ETF_TW 現有 dashboard 做對照。

可以補強：
- 交易伺服器健康檢查
- CA / 登入狀態檢查
- token / session 管理
- API 使用狀態
- 運行中的 stream 監控

**價值**：把「交易可用性」和「儀表板可視化」分層管理。

---

## 4. 建議的補強清單

### A. 立即可加（低風險、文件先行）
1. **rshioaji 能力矩陣**
   - Python binding
   - HTTP API
   - SSE
   - CLI
   - Dashboard
   - OpenAPI

2. **官方 / 本地 / 模擬環境分層圖**
   - 本地 wrapper 測試
   - 官方模擬環境測試
   - 正式交易前置條件
   - 哪些結果算可驗證證據

3. **驗證 SOP 補充**
   - 如何判定「測試通過」
   - 哪些紀錄必須出現在官方可見環境
   - 什麼情況只算 local smoke test，不能算正式驗證

4. **架構備註**
   - rshioaji 目前是 alpha，不納入正式唯一交易依賴
   - 先作為可選 adapter / 觀察項目

---

### B. 要驗證後再加（中風險）
1. **SSE 事件驅動資料流**
   - 報價
   - order state
   - health events

2. **HTTP API client 封裝**
   - 統一的 request / response schema
   - 錯誤處理
   - 重試 / timeout policy

3. **OpenAPI 型別化整合**
   - 用 API schema 產生 typed client
   - 減少手寫參數錯誤

4. **跨語言工具鏈**
   - 如果未來真有 JS/Go/Rust 工具鏈需求，再進一步接上

---

### C. 不建議現在加（高風險）
1. **直接把 rshioaji 當唯一 production trade path**
2. **在未驗證前就把舊流程全部切掉**
3. **把 local test 當作官方測試通過證據**
4. **為了新架構反過來重寫現有 live order SOP**

---

## 5. 避免走彎路的規則

### 規則 1：先分清楚「可用」與「已驗證可正式採用」
- 可用：能跑、能連、能顯示
- 已驗證：有官方可見紀錄、符合測試流程、可作為 SOP 依據

### 規則 2：本地成功 ≠ 官方測試通過
- 本地 wrapper / local server / local dashboard 只能證明本地流程可跑
- 若官方端沒有相對應的模擬記錄，不能算測試通過

### 規則 3：先做 adapter，別先砍舊路
- ETF_TW 現有的 shioaji / state / dashboard 路徑已經在運作
- 新能力先掛在旁邊，經過驗證後再決定是否升級為主路徑

### 規則 4：事件驅動先用在觀察層
- 先用在行情與健康監控
- 再考慮 order state
- 最後才看是否影響下單主流程

---

## 6. 建議的 ETF_TW 後續工作順序

### Phase 1：文件對齊
- 更新 ETF_TW README
- 將 rshioaji 的能力矩陣與路徑寫進 references
- 補上官方 / 本地 / 模擬環境的區分

### Phase 2：能力探勘
- 確認可用的 CLI / HTTP API / SSE endpoint
- 檢查與現有 shioaji adapter 的相容性
- 保持在非 production 路徑

### Phase 3：觀察層整合
- 用 SSE 或事件 callback 補行情 / 健康狀態
- 讓 dashboard 讀取更多即時資料
- 先不碰 live submit 主流程

### Phase 4：正式評估
- 若 alpha 版本穩定
- 再評估是否以 rshioaji 作為某些子功能的主要介面
- 仍需通過正式驗證 SOP

---

## 7. 這份文件與 ETF_TW 現有系統的關係

- **ETF_TW state / dashboard**：負責當前真實狀態與使用者可視化
- **Shioaji / rshioaji**：負責券商與交易 API 能力
- **本文件**：負責把新能力如何補進來講清楚，避免試錯成本重複發生

如果未來要調整正式流程，應先更新這份文件與相關 SOP，再動主程式。

---

## 8. 一句話總結

**rshioaji 值得納入 ETF_TW 的不是「立刻換掉現有流程」，而是先補上事件驅動、多語言、API 介面與驗證分層，讓未來擴充時有清楚路徑，不再走彎路。**
