# Sinopac / Shioaji Onboarding Guide (Public)

## 目的
這份文件記錄 ETF_TW 技能接入永豐金證券（Sinopac）/ Shioaji API 的公開流程，重點是避免未來在新電腦、新 agent 或新部署時重走彎路。

> 本文件為公開版，不包含 API key、secret、個人帳戶資訊、憑證檔案、憑證密碼、私有 `.env` 路徑等敏感資訊。

---

## 核心結論
1. **本地模擬測試成功，不等於官方測試通過**。
2. 必須以 **永豐 / Shioaji 官方可見的模擬委託紀錄** 作為測試通過標準。
3. 正式環境登入成功，不代表正式交易已完全打通。
4. 正式送單前，通常還需要完成 **CA 憑證啟用**。
5. 盤中 / 盤後 / 零股時段不同，會直接影響送單驗證結果與排錯判讀。

---

## 官方參考入口
- 官方文件首頁：
  - https://sinotrade.github.io/zh/
- AI Assistant / 測試與準備總入口：
  - https://sinotrade.github.io/zh/ai_assistant/
- 前置準備總入口：
  - https://sinotrade.github.io/zh/tutor/prepare/
- API 委託下單同意書 / 測試流程：
  - https://sinotrade.github.io/zh/tutor/prepare/terms/
- 官方測試流程範例：
  - https://sinotrade.github.io/zh/tutor/prepare/example_testing_flow/
- 快速入門：
  - https://sinotrade.github.io/zh/tutor/quick_start/
- 模擬交易說明：
  - https://sinotrade.github.io/zh/tutor/simulation/
- Snapshot 文件：
  - https://sinotrade.github.io/zh/tutor/market_data/snapshot/
- Token / 金鑰申請說明：
  - https://sinotrade.github.io/zh/tutor/prepare/token/#_2
- CA 憑證下載入口：
  - https://www.sinotrade.com.tw/newweb/PythonAPIKey/

> 補充備忘可參考：`references/shioaji-useful-links.md`

---

## 流程總覽
### Phase 1：準備金鑰與套件
1. 安裝 `shioaji`
2. 申請 / 取得 API key 與 secret
3. 確認可登入模擬環境與正式環境
4. 確認登入後能辨識正確帳戶類型（證券帳戶 vs 海外帳戶）

### Phase 2：完成官方認列模擬測試
1. 使用 **simulation=True**
2. 使用官方格式與官方可見流程送出模擬單
3. 驗收標準不是本地程式回成功，而是 **官方端看得到模擬委託紀錄**
4. 官方模擬測試通過後，正式環境權限才可能自動審核開通

### Phase 3：驗證正式環境查詢能力
1. 正式環境登入
2. 查 `account_balance()`
3. 查 `list_positions()`
4. 查 `list_trades()`
5. 確認用的是正確的證券帳戶，而不是海外帳戶

### Phase 4：啟用 CA 憑證
1. 下載 CA 憑證
2. 以憑證檔 + 憑證密碼執行 `activate_ca()`
3. 若未啟用，正式送單常見錯誤會要求先 activate CA

### Phase 5：正式送單鏈路驗證
1. 在正確交易時段測試最小正式單
2. 先驗證委託可受理，再驗證成交 / 查單 / 持股變化
3. 盤中與盤後零股測試要分開看待，不可混為一談

---

## 官方測試驗收的關鍵知識
### 錯誤觀念
- 「我本地程式有回 success，所以官方應該算通過」

### 正確觀念
- 官方人員看得到模擬委託紀錄，才算真的測試通過
- 若官方看不到紀錄，即使本地有結果，也不代表完成認列流程

---

## 帳戶辨識注意事項
登入後可能會看到多個帳戶，例如：
- 海外帳戶
- 證券帳戶

### 重點
- 查股票帳務 / 持股 / 現貨下單時，要用 **證券帳戶**
- 不可把海外帳戶拿去做 stock balance / stock order 驗證

---

## CA 憑證注意事項
### 下載位置
CA 憑證下載網址：
- https://www.sinotrade.com.tw/newweb/PythonAPIKey/

### 密碼規則
CA 憑證密碼為：
- **含英文字母的身分證字號**

### 實務提醒
- CA 憑證檔與密碼屬敏感資訊
- 不可寫入公開版技能文件
- 應外部化保存在私有部署文件與私有設定中

---

## 正式送單前的最小檢查清單
1. 已完成官方可見模擬測試
2. 正式環境登入成功
3. `account_balance()` 可查
4. `list_positions()` 可查
5. `list_trades()` 可查
6. 已啟用 CA 憑證
7. 使用正確證券帳戶
8. 確認市場時段與 `order_lot` 類型正確

---

## 常見錯誤與判讀
### 1. `Account Not Acceptable.`
可能原因：
- 官方模擬測試尚未完成 / 尚未被官方認列
- 正式權限尚未自動審核開通

### 2. `Please activate ca for person_id: ...`
可能原因：
- 尚未啟用 CA 憑證

### 3. `該股票已收盤`
可能原因：
- 不在正確交易時段
- 用整股邏輯測試，但市場已收盤

### 4. 本地模擬成功，但官方看不到模擬單
可能原因：
- 測試方式未對齊官方可見流程
- 驗收標準誤判

### 5. `Contracts` / 商品檔相關錯誤
可能原因：
- 登入時未正確載入商品檔
- 程式使用 `api.Contracts` 前未完成合約載入

---

## 時段與測試提醒
### 整股 / 盤中零股
- 09:00 ~ 13:30

### 盤後零股
- 13:40 ~ 14:30

### 重點
- 盤中委託與盤後零股的 `order_lot`、成交邏輯與驗證方式不同
- 測試前要先確認目標是：
  - 正式整股測試
  - 盤中零股測試
  - 盤後零股測試

---

## 建議文件搭配
### 公開版應搭配
- `sinopac-troubleshooting-public.md`
- `broker-onboarding.md`
- `trading-workflow.md`

### 私有版應另存
- 憑證存放位置
- `.env` 位置
- 實際證券帳戶 ID
- 私有部署步驟

---

## 最後結論
真正打通永豐 / Shioaji，不只是安裝套件與登入成功，而是要依序完成：
- 官方可見模擬測試
- 正式帳務查詢
- CA 啟用
- 正式送單鏈路驗證
- 後續盤中成交 / 查單 / callback 驗證

這份流程文件的目的，就是讓未來新部署不要再重走冤枉路。
