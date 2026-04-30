# ETF_TW 實作待辦清單

## 高優先級（High Priority）

### 0. State Architecture 收斂（NEW）
**狀態**: IN_PROGRESS  
**描述**: 統一 ETF_TW 正式狀態架構，確保 dashboard / agent / scripts 全面對齊 instance state。  
**需求**:
- [x] 寫入 `docs/STATE_ARCHITECTURE.md`
- [x] refresh 主鏈改為 instance state
- [x] decision engine 支線改為 instance state
- [x] 補 `docs/SYMBOL_NORMALIZATION.md`
- [x] 主鏈 watchlist / market_cache / tape / summary canonical symbol 去重
- [x] 補更多 regression tests（state path / symbol normalization / refresh DAG）
- [x] README / dashboard/README / CHANGELOG 對齊正式架構
**影響**: 若未完成，後續功能擴充容易持續產生 state drift 與重複訊號  
**負責人**: TOMO  
**截止**: 2026-04-05

### 1. Paper Ledger Initialization
**狀態**: TODO  
**描述**: 建立模擬交易的初始持倉記錄  
**需求**:
- [ ] 建立初始買入記錄模板
- [ ] 使用者需提供初始資訊（日期、價格、股數）
- [ ] 計算初始持倉與平均成本
- [ ] 更新 `paper_ledger.md` 格式
**影響**: 無法計算精確績效指標  
**負責人**: TOMO  
**截止**: 2026-03-30

### 2. Broker Adapter 實作
**狀態**: IN_PROGRESS  
**描述**: 完成券商接入骨架與正式交易生命周期能力  
**需求**:
- [x] Sinopac 模擬連接完整實作
- [x] Sinopac 正式環境登入 / 帳務查詢 / 憑證啟用 / 基礎送單鏈路驗證
- [x] Sinopac 訂單驗證補強（漲跌停、價格偏離、零股提醒、交易時段警告）
- [x] Sinopac `get_order_status()` 基礎骨架
- [x] Sinopac `cancel_order()` 基礎骨架
- [x] Sinopac callback 註冊 / 分發基礎框架
- [x] Sinopac 訂單狀態細化 / callback 完整整合（主幹完成，edge cases 待補）
- [ ] Cathay 模擬連接完整實作
- [ ] Broker Manager 完善
- [ ] API 錯誤處理
**影響**: 正式多券商能力尚未完整  
**負責人**: TOMO  
**截止**: 2026-04-15

### 3. 風控規則強化
**狀態**: TODO  
**描述**: 增加進階風控機制  
**需求**:
- [ ] 停損機制實作
- [ ] 最大回撤監控
- [ ] 波動度調整部位
- [ ] 相關性風險檢查
**影響**: 風險控制不夠完善  
**負責人**: TOMO  
**截止**: 2026-04-01

---

## 中優先級（Medium Priority）

### 4. 報表系統
**狀態**: TODO  
**描述**: 自動生成各類報表  
**需求**:
- [ ] 盤前報告模板
- [ ] 盤後報告模板
- [ ] 週報生成
- [ ] 月報生成
- [ ] 績效分析報表
**影響**: 需要手動整理報表  
**負責人**: TOMO  
**截止**: 2026-04-20

### 5. 資料品質提升
**狀態**: TODO  
**描述**: 提升資料準確性與完整性  
**需求**:
- [ ] 多來源交叉驗證
- [ ] 異常值自動偵測
- [ ] 自動更新排程
- [ ] 資料完整性檢查
**影響**: 資料可能不準確  
**負責人**: TOMO  
**截止**: 2026-04-10

### 6. Order Status 查詢
**狀態**: IN_PROGRESS  
**描述**: 追蹤訂單狀態  
**需求**:
- [x] 訂單狀態查詢 API 基礎骨架
- [x] 取消訂單功能基礎骨架
- [x] callback 註冊 / 事件分發基礎框架
- [ ] 成交回報完整整合
- [ ] 訂單歷史記錄
- [x] 狀態映射細化基礎護欄（lifecycle helper / submit landed contract / polling terminal contract）
- [ ] 盤中正式委託 / 成交 / 查單驗證清單
- [x] `orders_open` state integration / terminal cleanup
- [x] callback / polling consistency guard
- [x] callback / polling verification metadata consistency guard
- [ ] filled 後再由 broker 真實持倉/positions 對齊持倉真相
- [x] partial fill 與 positions / fills ledger 對齊規劃
- [x] filled reconciliation report helper
- [x] filled reconciliation refresh hook
- [x] dashboard health 可承接 filled reconciliation warning
- [x] dashboard overview / template 顯示 filled reconciliation 區塊
- [x] fills ledger 最低欄位契約
- [x] callback partial fill → fills ledger sync
- [x] polling partial fill → fills ledger sync
- [x] callback dry-run / smoke test
- [x] callback terminal cleanup guard
- [x] callback / polling dedupe guard
- [x] callback / polling verification metadata consistency guard
- [x] partial fill guard
- [x] callback precedence guard
- [x] stale callback 最小護欄
- [x] timestamp precedence guard
- [x] broker source priority guard
- [x] broker seq precedence guard
- [x] callback / polling / submit metadata contract
- [x] `docs/BROKER_RECONCILIATION_RULES.md`
**影響**: 訂單追蹤能力仍未完整  
**負責人**: TOMO  
**截止**: 2026-04-05

### 6A. Filled / Positions Reconciliation Close-the-loop
**狀態**: IN_PROGRESS  
**描述**: 從「能發現 filled 與 positions 尚未對齊」走到「能穩定完成對齊與清警訊」。  
**需求**:
- [x] filled fact 與 positions truth 邊界定義
- [x] `filled_reconciliation.py`
- [x] unreconciled symbols helper
- [x] reconciliation report helper
- [x] reconciliation report state IO
- [x] refresh hook
- [x] dashboard health / overview / template / global banner 接線
- [ ] 定義 filled 後 broker positions 對齊的正式完成條件
- [ ] 補 positions 更新後 snapshot / summary 對齊 helper
- [ ] 補 unreconciled 狀態清除條件與時機

### 6B. Submit / Verification / Polling / Callback Contract Completion
**狀態**: IN_PROGRESS  
**描述**: 補齊四條來源路徑的正式 contract。  
**需求**:
- [x] submit verification metadata contract
- [x] polling metadata contract
- [x] callback metadata contract
- [x] precedence helper
- [x] timestamp precedence
- [x] source priority
- [x] broker seq precedence
- [x] partial fill monotonicity guard
- [x] submit_response metadata contract 正式化

### 6C. Partial Fill / Fills Ledger / Portfolio Boundary
**狀態**: IN_PROGRESS  
**描述**: 把 partial fill 升級成正式 fill facts 與持倉邊界管理鏈。  
**需求**:
- [x] fills ledger 最低欄位契約
- [x] fills ledger state IO
- [x] callback partial fill → fills ledger sync
- [x] polling partial fill → fills ledger sync
- [x] partial fill 不直接進 `positions.json`
- [x] partial fill 不直接變 snapshot holdings
- [x] callback / polling terminal filled → fills ledger sync
- [ ] 規劃 filled 後 fills ledger / positions / snapshot 的最終一致性閉環

### 6D. Dashboard / Summary / Docs Consolidation
**狀態**: IN_PROGRESS  
**描述**: 把 reconciliation / fills / warning 的顯示與文件收成一體。  
**需求**:
- [x] dashboard health 可承接 filled reconciliation warning
- [x] dashboard overview / template 顯示 filled reconciliation 區塊
- [x] global banner / refresh 後摘要提示 unreconciled fills
- [x] `docs/BROKER_RECONCILIATION_RULES.md`
- [x] filled reconciliation count 接入 agent summary

---

## 低優先級（Low Priority）

### 7. 新聞與情報
**狀態**: TODO  
**描述**: 整合新聞與情報分析  
**需求**:
- [ ] 新聞爬蟲實作
- [ ] 情緒分析
- [ ] 重要事件提醒
- [ ] 新聞摘要生成
**影響**: 缺乏市場情報  
**負責人**: TOMO  
**截止**: 2026-05-01

### 8. 進階技術指標
**狀態**: TODO  
**描述**: 增加更多技術指標  
**需求**:
- [ ] 布林通道
- [ ] KD 指標
- [ ] MACD 柱狀圖
- [ ] 成交量分析
**影響**: 技術分析不夠完整  
**負責人**: TOMO  
**截止**: 2026-04-25

### 9. CLI 完善
**狀態**: TODO  
**描述**: 完善 CLI 介面  
**需求**:
- [ ] 命令補全
- [ ] 互動式提示
- [ ] 輸出格式美化
- [ ] 錯誤訊息優化
**影響**: 使用體驗不佳  
**負責人**: TOMO  
**截止**: 2026-04-15

---

## 已完成的任務

### ✅ v1.0 核心功能（2026-03-23）
- [x] ETF 基本資料查詢
- [x] ETF 比較功能
- [x] 即時報價（Yahoo Finance）
- [x] 技術指標計算（MA/RSI/MACD）
- [x] DCA 試算
- [x] 模擬交易（paper trade）
- [x] 持倉追蹤與損益計算
- [x] 基本風控規則
- [x] 交易日誌與帳本
- [x] 新手導引文件
- [x] 風控規則文件
- [x] 交易流程文件
- [x] 資料來源說明

---

## 任務狀態圖例

- **TODO**: 尚未開始
- **IN_PROGRESS**: 進行中
- **BLOCKED**: 被阻塞（需依賴其他任務）
- **REVIEW**: 待審查
- **DONE**: 已完成

---

## 更新記錄

### 2026-03-23
- 初始任務清單建立
- 分類高/中/低優先級
- 設定截止日
