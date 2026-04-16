# Shioaji API 真實行為與限制正式規則（P1-2）

## 目的
這份文件把 ETF_TW 實際踩過的 Shioaji API 行為，整理成正式規則。

它的用途不是教人幻想 API 無所不能，而是明確告訴系統：
- 哪些能查
- 哪些不能查
- 哪些查得到也不能過度解讀

---

## 1. 登入與驗證

### 正式規則
- 使用 `api.login(api_key=..., secret_key=...)`
- 參數名是 `secret_key`，不是 `api_secret`
- CA 啟用需獨立呼叫 `api.activate_ca(...)`
- 不應把登入成功直接當成交易能力完整可用

### 實務限制
- 登入成功 ≠ 可以正確查到所有訂單 / 持倉 / 額度細節
- 有些欄位看似可用，實際語義可能和直覺不同

---

## 2. `list_orders()` 不存在

### 正式規則
- 不要呼叫 `api.list_orders()`
- 正確可用的是 `api.list_trades()`

### 實務限制
- 因為 `list_orders()` 根本不存在，所以不能再設計任何依賴它的流程、文件或回答模板

---

## 3. `list_trades()` 的正式定位

### 它是什麼
- `list_trades()` 是目前可用的訂單 / trade 查詢入口之一

### 它不是什麼
- 它不是完整成交歷史真相源
- 它不是「查不到就代表沒下單」的證據
- 它也不是「查不到就代表已成交」的證據

### 正式回答規則
當 `list_trades()` 查不到某筆單時，只能說：
- 本次查詢沒有看到這筆紀錄

不能說：
- 這單一定沒送出去
- 這單一定已成交
- 這單一定失敗

### 實務用途
- 可作為委託可見性的佐證之一
- 可作為 `order_lot` / 狀態碼 / broker side 欄位的交叉驗證來源
- 必須和 submit 回應、broker_order_id、後續查詢一起看

---

## 4. `list_positions()` 的正式定位

### 它是什麼
- `list_positions()` 是持倉查詢入口之一
- 若支援 `unit=Unit.Share`，可盡量以股數語境查詢

### 它不是什麼
- 它不是永遠完整、永遠正確、永遠可直接對外宣稱的最終真相
- 當結果異常時，不能硬把它包裝成 100% 真實持倉

### 正式回答規則
當 `list_positions()` 顯示與使用者券商畫面衝突時：
- 必須明說「本次 API 無法可靠確認」
- 不得自行挑一個版本當最後真相

---

## 5. `account_balance()` 的正式定位

### 正式規則
- `account_balance()` 可提供餘額相關資訊
- 但顯示的額度不一定等於真實可自由運用現金

### 實務限制
- 必須區分：
  1. 真實現金
  2. 券商顯示額度
  3. 可下單額度 / 信用額度

### 禁止事項
- 禁止把 API 顯示的額度直接說成「帳戶現金就是這麼多」

---

## 6. quantity / order_lot 的正式規則

### 系統內部規則
- `Order.quantity` 對內以「股」為主

### Shioaji 送單語境
- `Common`：整股語境，quantity 需注意是以「張」送出
- `IntradayOdd`：盤中零股語境，quantity 以「股」送出
- `Odd`：盤後零股語境，quantity 以「股」送出

### 正式限制
- 不得用口頭心算取代 adapter 實作
- 不得再使用「非 1000 倍數一定拒絕」這種過時規則

---

## 7. submit 回應的正式定位

### submit 回應能代表什麼
- 代表 submit 流程有回應
- 代表 adapter 端拿到某種結果

### submit 回應不能單獨代表什麼
- 不能單獨證明委託已落地
- 不能單獨證明券商側已正式掛單
- 不能單獨證明後續一定查得到

### 正式規則
若沒有：
- `verified=True`
- 或 `broker_order_id`
- 或其他更強的 broker 證據

就不能把 submit 回應說成已正式掛單。

---

## 8. ghost order / 假回單正式規則

### 判定條件
符合以下條件時，視為 ghost order：
- `source_type == submit_verification`
- `verified == false`
- `order_id` 空
- `broker_order_id` 空
- `status in {pending, submitted}`

### 正式處理
- 不得列為 open order
- 不得在 dashboard 顯示成未完成委託
- 不得對外敘述成已掛單
- 應從 `orders_open.json` 清除

---

## 9. API 回答分級規則

### A 級：本次可直接陳述
- 本次 API 明確回傳的欄位
- 本次券商畫面直接可見的內容

### B 級：可作為佐證
- `list_trades()` 查到的狀態碼 / `order_lot` / 訂單欄位
- `list_positions()` 查到的持倉欄位
- `account_balance()` 查到的餘額欄位

### C 級：不能直接當事實
- state 檔
- summary
- memory
- 舊報告

---

## 10. 對外回答模板（Shioaji 類）

### 查持倉
1. 本次 API 直接看到
2. 本次 API 無法確認
3. 次級資訊（若有）
4. 建議下一步

### 查掛單 / 成交
1. 本次 `list_trades()` 直接看到
2. 本次 `list_trades()` 沒看到什麼
3. 不能因此推出什麼
4. 還需要哪些佐證

### 查餘額
1. API 顯示的欄位是什麼
2. 這欄位是現金、額度還是其他語境
3. 不能直接推成可自由動用現金

---

## 11. 邊界

這份文件可以回答：
- Shioaji 有哪些方法不能用
- `list_trades()` / `list_positions()` / `account_balance()` 應怎麼解讀
- submit 回應應如何降級解讀
- ghost order 應如何處理

這份文件不能單獨回答：
- 某筆單此刻一定已落地
- 某筆單此刻一定已成交
- 某檔持倉此刻一定是多少

這些仍需當次證據交叉驗證。
