---
name: taiwan-finance
version: v1.0.0
description: 台灣全方位財經分析技能套件 (投行、個股、私募、財管整合版)
metadata:
  version: v1.0.0
  source: "https://github.com/anthropics/financial-services-plugins"
  modifications: "由 Antigravity 進行深度重構：1. 採用標準 OpenClaw 技能架構 (SKILL.md + references/)；2. 整合原始五大外掛功能；3. 全面在地化為台灣金融語境。"
---

# 台灣財經全方位技能套件 (Taiwan Finance Suite)

本技能將 Agent 轉化為精通台灣金融市場的高階分析專家。支援投行併購、個股研究、私募股權及財富管理等五大核心領域，並配備在地化數據檢索邏輯。

## 快速引用 (Quick Reference)

| 模組名稱 | 涵蓋功能 | 參考路徑 |
|---|---|---|
| [財務分析核心](references/financial-analysis.md) | 建模、估值 (DCF/Comps)、三表分析、LBO | [financial-analysis.md](references/financial-analysis.md) |
| [個股研究 (ER)](references/equity-research.md) | 法說會、月營收、催化劑日曆、研究報告 | [equity-research.md](references/equity-research.md) |
| [投資銀行 (IB)](references/investment-banking.md) | Pitch Deck、CIM、Teaser、併購模型 | [investment-banking.md](references/investment-banking.md) |
| [私募股權 (PE)](references/private-equity.md) | 盡職調查 (DD)、案源篩選、單元經濟學 | [private-equity.md](references/private-equity.md) |
| [財富管理 (WM)](references/wealth-management.md) | 資產配置、財務規劃、客戶評論 | [wealth-management.md](references/wealth-management.md) |

## 核心工作流 (Core Workflow)

### 1. 數據獲取與驗證
優先使用「公開資訊觀測站 (MOPS)」與「Yahoo 股市」。詳細搜尋語法請參閱各模組。

### 2. 分析與建模
根據使用者需求，調用對應模組的邏輯：
- **公司估值**：參閱 `financial-analysis.md` 中的 DCF 與 Comps 章節。
- **財報分析**：參閱 `equity-research.md` 中的法說會與三表分析。

### 3. 輸出規範 (台灣在地化)
- **術語**：使用繁體中文標準術語（毛利率、三大法人、營收年增率）。
- **單位**：預設為新台幣 (TWD)「億元」或「百萬元」。

## 指令範例集 (Slash Commands)
- `/comps [2330]` -> 執行台股與全球同業倍數比較。
- `/dcf [2454]` -> 依據台灣市場參數執行估值建模。
- `/earnings [2317]` -> 檢索最新法說會與月營收動能。
- `/memo [項目名稱]` -> 撰寫投委會 (IC) 備忘錄 (適用於 PE/IB)。

---
**備註**：本技能文件由原「單一文件版」升級為「標準分層架構版」，完整保留並在地化了原始儲存庫的所有功能模組。
