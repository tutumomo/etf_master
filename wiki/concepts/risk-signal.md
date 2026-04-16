---
title: 風險訊號儀表板
created: 2026-04-11
updated: 2026-04-15
type: concept
tags: [風險, 市場體制, 投資策略]
sources: [ETF_TW/instances/etf_master/state/market_event_context.json]
---

# 風險訊號儀表板

> 即時風險監控頁面。盤中掃描每 30 分鐘更新，盤後收工時做當日總結。此頁是判斷「今天能不能動」的關鍵依據。

## 核心訊號

| 訊號 | 當前值 | 狀態 | 判斷基準 |
|------|--------|------|----------|
| 事件體制 | risk-on | ✅ 偏多 | risk-on / neutral / risk-off |
| 全球風險 | moderate | 🟡 中性 | low / moderate / elevated / high |
| 地緣政治 | medium | 🟡 中性 | low / medium / high |
| 利率風險 | low | 🟢 降溫 | low / medium / high |
| 能源風險 | medium | 🟡 中性 | low / medium / high |
| 台股衝擊 | cautious | ⚠️ 觀望 | positive / neutral / cautious / negative |
| 防守傾向 | low | 🛡️ 偏進攻 | low / medium / high |
| 更新時間 | 2026-04-15 08:46 | — | — |

**今日判讀（2026-04-15 早班）**：體制由 cautious → balanced_bullish，risk-off 解除。核心台股 006208/0050 跳空大漲 +2.7~3.1%，risk-on 信號明顯增強。event_regime 由 risk-off 降為 neutral，global_risk 由 elevated 降至 moderate，rate_risk 降至 low（反映美債拋售壓力暫緩）。地緣+能源風險仍在但未升級，台股短線偏多但外部風險因子未除，仍需紀律執行。

## 活躍風險事件

1. **伊朗封鎖霍爾木茲海峽威脅** — 仍有 12% 石油運輸經過，實質封鎖未發生但威脅等級 medium，需持續關注
2. **美伊談判未完** — 台股明日開盤存在不確定性，為最大外部風險
3. **平均年化波動 31.7%** — 波動仍高，核心 ETF 跳空後可能引發短線獲利了結

## 訊號變動歷史

| 日期 | 變動 | 備註 |
|------|------|------|
| 2026-04-10 | 初版建立 | 從 state market_event_context 初始化 |
| 2026-04-13 | 持平無變動 | 風險訊號與 4/10 一致，地緣+能源雙高未解；盤面偏多但事件層未鬆動 |
| 2026-04-14 | 利率風險持續 | 00679B -0.48%，長天期美債承壓未止；地緣+能源雙高仍懸而未決 |
| 2026-04-15 | ⚠️ 顯著改善 | risk-off→neutral，global_risk elevated→moderate，rate_risk medium→low；核心台股大漲 risk-on 信號明顯回升 |

## 風險等級對應行動

| 等級 | 市值型 | 高股息 | 債券型 | 現金 |
|------|--------|--------|--------|------|
| low | 積極加碼 | 適度持有 | 減碼 | 極低 |
| moderate | 正常布局 | 正常持有 | 正常配置 | 低 |
| elevated | 觀望為主 | 偏重持有 | 加碼 | 中等 |
| high | 暫停買入 | 維持不動 | 偏重 | 偏高 |
| crisis | 全數迴避 | 設停損 | 最大配置 | 最高 |

**當前行動對照**（balanced_bullish + moderate risk覆蓋）：
- 市值型（0050/006208）：體制升級為偏多，可正常布局，006208 已有 1000 股續抱，0050 已有 253 股續抱
- 高股息（00878）：偏重持有，已有 100 股，配息成長路徑未變
- 債券型（00679B）：已有 100 股（27.17），持續觀望，利率風險降至 low 後可考慮加碼
- 現金：中等偏低（目前 215,185 / 458,497 = 46.9%）
- 掛單：目前無活躍掛單（orders_open.json 為空）

## 關聯頁面

- [[market-view]] — 市場體制判讀（風險訊號的決策上游）
- [[家族投資需求]] — 各成員的風險承受度對照
- [[債券型-etf]] — 防守偏重時的首選工具
