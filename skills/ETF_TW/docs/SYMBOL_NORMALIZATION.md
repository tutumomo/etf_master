# ETF_TW Symbol Normalization v1

## 目的

建立 ETF_TW 的正式 symbol 正規化規範，避免下列問題：
- `0050` 與 `0050.TW` 同時出現在 state
- watchlist / market_cache / intelligence / tape 出現重複訊號
- dashboard 與 agent 摘要顯示重複標的
- 未來 alert、order matching、review 流程因雙 key 發生誤判

---

## 核心原則

### 1. State 層只允許 canonical symbol
canonical symbol 範例：
- `0050`
- `00878`
- `006208`
- `00679B`
- `00922`

**state 檔內禁止把 `.TW` / `.TWO` 當成主鍵。**

### 2. Provider symbol 只在外部取價層使用
例如：
- canonical: `0050`
- provider: `0050.TW`

例如：
- canonical: `00679B`
- provider: `00679B.TWO`

### 3. watchlist / positions / orders / portfolio / summary 一律使用 canonical symbol
適用於：
- `watchlist.json`
- `positions.json`
- `orders_open.json`
- `portfolio_snapshot.json`
- `intraday_tape_context.json`
- `agent_summary.json`
- `market_intelligence.json`

### 4. market_cache 可保留 provider 嘗試資訊，但 quotes key 應以 canonical symbol 為準
允許保留：
- `attempted_symbols`
- `source`

但最終 key 不應是 `.TW` / `.TWO` 版本。

---

## 正式規則

### Canonicalization Rule
- 若 symbol 含有 `.TW` / `.TWO` / 其他 provider suffix
- 在進入 ETF_TW state 前，必須先轉回 canonical symbol

### Canonicalization Examples
- `0050.TW` → `0050`
- `00878.TW` → `00878`
- `006208.TW` → `006208`
- `00679B.TWO` → `00679B`

---

## 分層責任

### State Layer
儲存 canonical symbol。

### Provider Layer
根據 `symbol_mappings.json` 把 canonical symbol 轉成 provider candidates。

### Display Layer
顯示名稱由 watchlist / ETF catalog 決定，不應靠 provider symbol 回填。

---

## 改造目標

### 第一波
- `watchlist.json` 去除 `.TW` 重複 symbol
- `market_cache.json` quotes key 改為 canonical symbol
- `market_intelligence.json` 只輸出 canonical symbol
- `intraday_tape_context.json` 只輸出 canonical symbol
- `agent_summary.json` 不再因 provider variant 出現重複指標

### 第二波
- 將 `instance_config.watchlist` 中的 provider-style symbols 在載入時 canonicalize
- 補 regression test，防止 `.TW` / `.TWO` 再次進入 state

---

## 一句話總結

> ETF_TW 的 state 世界只認 canonical symbol；provider suffix 只存在於外部抓價與映射層。
