# Wiki Log — 台灣 ETF 投資知識庫

> 所有 wiki 動作的時間序列記錄。僅追加，不刪改。
> 格式：`## [YYYY-MM-DD] action | subject`
> 動作：ingest, update, query, lint, create, archive, delete
> 超過 500 筆時輪替：改名為 log-YYYY.md，重新開始。

## [2026-04-11] create | Wiki initialized
- Domain: 台灣 ETF 投資知識庫
- 基礎結構建立：SCHEMA.md, index.md, log.md
- 目錄：raw/, entities/, concepts/, comparisons/, queries/, raw/articles/, raw/data/, raw/papers/, raw/assets/

## [2026-04-11] ingest | etf_universe_tw.json 初始攝入
- 來源：raw/data/etf_universe_tw.json（325 檔 ETF，213 TWSE + 112 TPEX）
- 新增 15 個實體頁（entities/）：0050, 0051, 0056, 006204, 006208, 00679B, 00687B, 00713, 00772B, 00830, 00878, 00881, 00891, 00919, 00929
- 新增 5 個概念頁（concepts/）：市值型, 高股息, 債券型, 產業型, 發行商生態, 家族投資需求
- 新增 3 個比較頁（comparisons/）：0050-vs-006208, 0056-vs-00878-vs-00929, 00679B-vs-00687B
- 共計 24 個頁面建立

## [2026-04-12] ingest | Graphify & Karpathy LLM Wiki | type: article+spec | quality: secondary+primary

- 來源1：raw/articles/aivi-graphify-overview-2026.md（article / secondary — 第三方產品介紹頁）
- 來源2：raw/specs/karpathy-llm-wiki-gist-2026.md（spec / primary — Karpathy 原始 Gist）
- 新增 2 個實體頁：graphify, andrej-karpathy
- 新增 3 個概念頁：llm-wiki-模式, 雙通道提取引擎, 知識圖譜-vs-RAG（comparison）
- 更新 SCHEMA.md：新增「知識工具標籤」和「人物」分類
- 建立 _meta/classification.md：分類日誌首次建立
- 建立新目錄：raw/specs/, raw/datasets/, raw/news/, raw/transcripts/, _meta/, _archive/
- 更新 index.md：頁面數 27 → 32
## 2026-04-14 — Graphify 實測整合寫入

### 任務
三方整合第一步：將 graphify 實測結果寫入 wiki 頁面

### 更新的頁面
1. `concepts/decision-chain.md` — 新增「Graphify 實測：ETF_TW 系統決策架構」章節
   - 系統三層決策架構（Community 4/6/7 對應）
   - 5 個 God Nodes 與系統邊界
   - Surprising Connections 發現
   - 與決策鏈五步驟的對應表
2. `concepts/知識圖譜-vs-RAG.md` — 新增「ETF_TW 實測數據」章節
   - 實測結果：75% EXTRACTED、528 社群、8 個 ETF 超邊
   - 圖譜 vs RAG 實測維度對比表
3. `entities/graphify.md` — 更新為 primary quality，新增完整實測數據

### 資料來源
- `ETF_TW/graphify-out/GRAPH_REPORT.md`（graphify 分析報告）
- `ETF_TW/graphify-out/graph.json`（完整圖譜資料）

### 下一步
- 將 graphify 發現的 ETF 節點（00679B、00878 等）對應到 wiki entity 頁
- 考慮建立 graphify → wiki 自動同步腳本

### 2026-04-14 — ETF 系統共現關聯寫入（第二步）

#### 更新的頁面（5個 ETF entity 頁）
| 頁面 | 新增共現 ETF |
|------|-------------|
| 00679B-yuanta-us-20y-bond | 00637L, 00713, 00878, 00881, 00892, 00922, 00923, **00929**（7共現） |
| 00878-cathay-esg-high-dividend | 00637L, 00679B, 00713, 00881, 00892, 00922, 00923, **00929**（7共現） |
| 00929-fuhwa-tech-optimal-income | 00923, 00679B, 00878, 00892（3共現） |
| 00713-yuanta-high-div-low-vol | 00637L, 00679B, 00881, 00878（3共現） |
| 00881-cathay-tech-leaders | 00713, 00637L, 00679B, 00878（3共現） |

#### 資料來源
- `ETF_TW/graphify-out/graph.json` → `hyperedges`（8個 ETF 生態超邊）

#### 待完成
- 00637L、00892、00922、00923 尚未建立 wiki entity 頁
- 可惜的是 graphify 的 ETF 節點主要是「文件提及」，不是「代碼邏輯關聯」（只有一個代碼節點 live_trading_sop_code_1 提及 TSE00878）

## [2026-04-16] ingest | Shioaji 官方文件 | type: spec | quality: primary

- 來源：https://sinotrade.github.io/zh/ → raw/specs/shioaji-official-docs-2026.md
- 分類：spec/primary（官方 API 文件，含程式碼範例與 API 端點）
- 新增 1 個實體頁：entities/shioaji.md
- 更新 3 個概念頁：taiwan-etf-trading.md（+API 參數表、使用限制）、shioaji-quantity-bug.md（+交叉引用）、settlement-t2.md（+交叉引用）
- 更新 index.md：頁面數 32 → 33
- URL 分類規則新增：sinotrade.github.io → spec/primary（官方文件）

### 拆分重構

- 新增 `concepts/shioaji-api-limits.md` — 從 shioaji.md 拆出 API 限制獨立概念頁
- 更新 `concepts/settlement-t2.md` — 併入結算 API（SettlementV1）欄位說明
- 精簡 `entities/shioaji.md` — 使用限制/結算改為摘要+交叉引用，指向拆分頁
- 更新 `index.md`：頁面數 33 → 34
