# ETF_TW 技能包檔案清單

## 統計摘要
- **Python 腳本**: 33 個
- **Markdown 文件**: 15+ 個
- **JSON 配置**: 5 個
- **資料庫 (SQLite)**: 1 個
- **總檔案數**: 68 個

---

## Python 腳本清單 (33 個)

### 主腳本 (16 個)
位於 `scripts/` 目錄：
1. `etf_tw.py` - 主入口與核心功能
2. `validate_order.py` - 訂單驗證
3. `preview_order.py` - 訂單預覽
4. `paper_trade.py` - 模擬交易
5. `calc_dca.py` - DCA 試算
6. `compare_etf.py` - ETF 比較
7. `risk_controller.py` - 風險控制
8. `account_manager.py` - 帳戶管理
9. `trade_logger.py` - 交易日誌
10. `beginner_flow.py` - 新手引導流程
11. `complete_trade.py` - 完整交易流程
12. `broker_adapter_example.py` - 券商適配器範例
13. `test_cathay.py` - 國泰券商測試
14. `test_sinopac.py` - 元大券商測試
15. `test_yuanlin.py` - 元富券商測試
16. `test_phase4.py` - 第四階段測試

### Adapters (6 個)
位於 `scripts/adapters/` 目錄：
1. `adapters/base.py` - 基礎適配器
2. `adapters/paper_adapter.py` - 模擬交易適配器
3. `adapters/sinopac_adapter.py` - 元大證券適配器
4. `adapters/cathay_adapter.py` - 國泰證券適配器
5. `adapters/yuanlin_adapter.py` - 元富證券適配器
6. `adapters/__init__.py` - 模組初始化

### etf_core 模組 (11 個)
位於 `scripts/etf_core/` 目錄：

**核心服務**:
1. `main_service.py` - 主服務
2. `simulator.py` - 模擬器
3. `telegram_push.py` - Telegram 推送

**Brokers (5 個)**:
4. `brokers/__init__.py`
5. `brokers/base_broker.py` - 基礎券商類
6. `brokers/broker_manager.py` - 券商管理器
7. `brokers/sinopac_broker.py` - 元大券商
8. `brokers/cathay_broker.py` - 國泰券商

**Utils (2 個)**:
9. `utils/quote.py` - 報價工具
10. `utils/news_crawler.py` - 新聞爬蟲

**Database (1 個)**:
11. `etf_core/db/database.py` - 資料庫連接與核心邏輯
12. `etf_core/db/etf_tw.db` - 核心 SQLite 資料庫

---

## 參考文件 (15+ 個)

位於 `references/` 目錄：
1. `beginner-guide.md` - 新手導引
2. `risk-controls.md` - 風控規則詳解
3. `trading-workflow.md` - 交易流程說明
4. `data-sources.md` - 資料來源與更新規則
5. `roadmap.md` - 發展路線圖
6. `broker-onboarding.md` - 券商上線指南
7. `api-integration.md` - API 整合指南
8. `phase4-complete.md` - 第四階段完成報告
9. `phase4-implementation.md` - 第四階段實作詳情
10. `phase5-sinopac-scaffold.md` - 第五階段：元大證券骨架
11. `phase6-complete.md` - 第六階段完成報告
12. `FINAL_SUMMARY.md` - 最終總結
13. `test_report_20260304.md` - 測試報告

---

## 資料檔案 (5 個)

位於 `data/` 目錄：
1. `etfs.json` - ETF 基本資料
2. `brokers.json` - 券商資訊
3. `broker_registry.json` - 券商註冊表
4. `paper_ledger.json` - 模擬帳本
5. `sample_orders.json` - 範例訂單

---

## 配置與資源 (3 個)

位於 `assets/` 目錄：
1. `config.example.json` - 配置範例
2. `requirements.txt` - Python 依賴套件
3. `etf_tw.db` - SQLite 資料庫

---

## 主要文件 (5 個)

位於根目錄：
1. `SKILL.md` - 技能定義文件
2. `TASKS.md` - 待辦事項清單
3. `INSTALL.md` - 安裝說明
4. `README.md` - 使用說明
5. `MANIFEST.md` - 本檔案清單

---

## 目錄結構總覽

```
ETF_TW/
├── SKILL.md
├── TASKS.md
├── INSTALL.md
├── README.md
├── MANIFEST.md
├── scripts/
│   ├── *.py (16 個主腳本)
│   ├── adapters/ (6 個適配器)
│   └── etf_core/ (11 個核心模組)
├── references/ (15+ 文件)
├── data/ (5 個資料檔)
├── assets/ (3 個資源檔)
└── tests/ (測試檔)
```

---

## 驗證安裝

執行以下指令確認所有檔案已正確安裝：

```bash
# 計算 Python 腳本數量
find scripts -name "*.py" -not -path "*/__pycache__/*" | wc -l
# 應輸出：33

# 計算 Markdown 文件數量
find . -name "*.md" | wc -l
# 應輸出：15+

# 計算 JSON 檔案數量
find data assets -name "*.json" | wc -l
# 應輸出：5+
```

---

## 版本資訊

- **版本**: v1.1.0
- **更新日期**: 2026-03-28
- **維護者**: ETF_Master Team
