# ETF_TW 結構盤點與修正說明（2026-03-26）

## 結論
`skills/ETF_TW` 目錄本體存在，且主要腳本檔案仍在，並未遺失。
先前混淆主要來自：
- agent workspace (`agents/etf_master`) 內有 agent 專屬設定檔
- `skills/ETF_TW` 內是技能包本體

## 真實結構摘要
### 根目錄主要檔案
- SKILL.md
- TASKS.md
- MANIFEST.md
- INSTALL.md
- README.md（本次補齊）
- RELEASE_NOTES_v1.0.0.md（本次新增）

### 主要資料夾
- assets/
- data/
- references/
- scripts/

## 腳本是否還在？
在，而且仍位於 `skills/ETF_TW/scripts/` 下。

### 主要腳本舉例
- scripts/etf_tw.py
- scripts/validate_order.py
- scripts/preview_order.py
- scripts/paper_trade.py
- scripts/compare_etf.py
- scripts/calc_dca.py
- scripts/account_manager.py
- scripts/trade_logger.py

### adapter 腳本舉例
- scripts/adapters/base.py
- scripts/adapters/paper_adapter.py
- scripts/adapters/sinopac_adapter.py
- scripts/adapters/cathay_adapter.py
- scripts/adapters/yuanlin_adapter.py
- scripts/adapters/sinopac_adapter_enhanced.py

### etf_core 仍存在
- scripts/etf_core/brokers/*
- scripts/etf_core/db/*
- scripts/etf_core/utils/*
- scripts/etf_core/main_service.py
- scripts/etf_core/simulator.py

## 哪些檔案屬於不應打包到公開版？
### 應排除
- assets/config.json
- .venv/
- __pycache__/
- *.pyc
- shioaji.log
- 私有 `.env` / 憑證（若位於其他路徑也不可帶入）
- 本地審查/測試報告（若包含個資、帳務、內部驗證資訊）

### 可保留
- SKILL.md
- TASKS.md
- MANIFEST.md
- README.md
- INSTALL.md
- references/
- scripts/（扣除 pyc / cache / 本地資料庫殘留需視情況）
- data/（需注意是否含個人化資料）

## 放錯層的問題
本次確認：
- agent 專屬的策略狀態 / 抬頭顯示設定，位於 `agents/etf_master/`，屬 agent 層，不屬 ETF_TW 可分發技能包本體。
- 這不是腳本遺失，而是 agent 與 skill 兩層職責不同。

## 修正動作
- 補齊 README.md
- 統一技能版本號為 v1.0.0
- 重新整理可分發打包規則
- 重新打包 v1.0.0 公開版
