# ETF_TW Plugin Readiness Assessment

**日期：2026-04-11**
**評估者：ETF_Master**

---

## 整體完成度：65%

| 模組 | 完成度 | 卡點 |
|------|--------|------|
| ETF_TW 核心（102 腳本、5券商適配器、4用戶實例、Dashboard） | 90% | 腳本有 legacy 殘留（layered_review_* 系列） |
| 財經三技能（analysis / market-pro / finance） | 85% | 各自獨立，缺乏統一入口 |
| 知識體系（Wiki 31頁 + Schema + Graphify） | 75% | 決策鏈 cron 尚未跑過完整循環 |
| Cron 決策鏈（5任務） | 70% | 剛整合，未經實戰驗證 |
| Plugin 封裝（安裝器、配置嚮導、密鑰管理） | 15% | 最大缺口 |

## 安全與可移植性問題

- 憑證直接寫在 `instance_config.json` 裡（安全風險）
- 路徑硬編碼為 `~/.hermes/profiles/etf_master/`（不可移植）
- 沒有 `pyproject.toml` 或安裝指引
- 家族身份、策略偏好、券商帳號全綁在 instance 裡（拆不出「通用核心」vs「個人配置」）

## 自主下單交易完成度：35%

### 已有 ✅
- 券商 API 對接（永豐已跑通）
- 下單→回報→核對 完整 lifecycle
- 風控硬限制（risk_controller.py：單筆50萬上限等）
- 多用戶 instance（4個家庭成員各有一位）
- Dashboard 即時監控
- 策略狀態對齊（收益優先 + 高波動警戒）

### 還缺 ❌（65%）

| 缺口 | 權重 | 說明 |
|------|------|------|
| **回測驗證** | 20% | 沒有歷史回測，策略是否有效全是假設 |
| **Paper 自主交易試跑** | 15% | 決策鏈從未在無人監督下連續跑過 |
| **熔斷機制壓力測試** | 10% | risk_limits 存在但沒被極端情境打過 |
| **決策 provenance** | 8% | 為什麼買/賣的推理鏈沒有完整紀錄 |
| **異常自癒** | 7% | cron 失敗、API 斷線、資料異常的自動恢復 |
| **合規日誌** | 5% | 自主交易後每筆都要可追溯、可舉證 |

## 補強優先級

### P0 — 安全與可移植性（plugin 生命線）
1. 密鑰管理重構（環境變數 / 系統鑰匙圈）
2. 路徑去硬編碼（$ETF_TW_ROOT）
3. pyproject.toml
4. 配置嚮導 setup_agent.py

### P1 — 品質保證（信任基礎）
5. 關鍵路徑測試（order_lifecycle / risk_controller / submit_verification）
6. 腳本除塵（清除 15-20 支 legacy）
7. 審計日誌強化（決策 provenance）

### P2 — 決策鏈成熟度（自主交易前置條件）
8. 決策品質評分回饋迴圈
9. 回測框架
10. Paper Auto-Trade 模式

## 時程預估

以目前節奏，8-12 週後可考慮開啟 live auto-trade，前提是 P0-P2 全部到位。

---
*本文件由 ETF_Master 評估產出，作為後續補強的基線參考。*