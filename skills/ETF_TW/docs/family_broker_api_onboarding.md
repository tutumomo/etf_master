# 家庭券商 API 接入研究與設定備忘（2026-04-24）

## 家庭券商分配

| Agent | 家庭成員 | 指定券商 | broker_id | 目前系統狀態 |
|---|---|---|---|---|
| etf_master | TOMO / 主人 | 永豐金證券 | `sinopac` | 已有 Shioaji live 接入經驗；仍需每次 live 查詢/下單走嚴格真相分級與 pre-flight |
| etf_wife | 太太 | 國泰證券 | `cathay` | 已寫入個人設定；正式 API 尚待確認與接入 |
| etf_son | 少爺 | 元大證券 | `yuanlin`（現有系統命名；實際為 Yuanta） | 已寫入個人設定；元大 OneAPI 需申請開通 |
| etf_daughter | 千金 | 國泰證券 | `cathay` | 已寫入個人設定；正式 API 尚待確認與接入 |

> 安全狀態：家人 agent 目前仍維持 paper / research-only。正式 API 憑證、測試環境驗證與人工授權完成前，不啟用 live trading。

## 元大證券 API 初步研究（兒子）

資料來源：元大證券官方「API下單」頁面。

已知事實：
- 元大證券提供 **OneAPI / API 下單**，官方頁面標示支援自行撰寫下單決策系統。
- 官方提供多種範例：C#、Python、COM/Excel、Delphi、WPF。
- API 權限需依帳號開通，登入模式包含：`S` 證券帳號、`F` 期貨帳號。
- 申請流程：
  1. 下載 API 測試軟體並上傳測試資料。
  2. 線上或臨櫃簽署 API 服務申請暨委託交易風險預告書。
  3. 請營業員協助開通 API 功能。
  4. 測試環境若需固定 IP 防火牆，需聯繫營業員申請。
- 官方限制摘要：登入不可重複；登入失敗不可太頻繁；報價/帳務/交易類 FunctionID 有每秒次數限制；單次交易最多 30 筆。

接入方向：
- 短期：下載官方 Python 範例與操作文件，在隔離測試目錄確認是否支援 macOS / Linux，或是否依賴 Windows COM/元件。
- 中期：為 ETF_TW 實作 `YuantaOneAPIAdapter`，不要沿用目前 scaffold 回傳假資料的 `yuanlin_adapter.py` 做 live。
- 風控：先做 read-only / sandbox 查詢，再做小額 paper 對照；正式下單必須另行授權。

## 國泰證券 API 初步研究（太太、女兒）

資料來源：國泰金控 CaaS 開發者中心、公開搜尋結果、目前 ETF_TW 既有 adapter 狀態。

已知事實：
- 國泰金控有 CaaS / Open API 開發者中心，但目前公開可驗證資料偏向金融開放 API / 合作平台，不等同於「個人國泰證券台股下單 API」。
- 目前 ETF_TW 的 `cathay_adapter.py` 是 scaffold，會模擬登入/餘額/持倉，**不能視為真實國泰 API 接入**。
- 尚未找到像永豐 Shioaji 或元大 OneAPI 這種明確面向個人台股下單的公開 Python API 文件。

接入方向：
- 第一優先：請國泰證券營業員確認是否提供個人台股 API 下單 / 帳務查詢服務、申請條件、SDK/元件、測試環境、支援 OS。
- 若官方不提供個人 API：只能維持 paper / 手動匯入持倉 / 券商畫面輔助對帳，不應用爬蟲或逆向登入方式處理真實下單。
- 若官方提供 API：建立新的真實 `CathayAdapter`，把現有 scaffold 改名或加硬阻斷，避免假資料被誤當 live truth。

## ETF_TW 實作待辦

1. `data/broker_registry.json` 更新券商 API 狀態：元大為官方 OneAPI 可申請；國泰標記為待營業員確認。
2. 元大：新增/替換真實 OneAPI adapter，先支援 read-only 查詢，再支援 sandbox/測試下單。
3. 國泰：查證後決定是否能做真實 adapter；查證前不可啟用 live。
4. Dashboard：家人 agent 顯示「指定券商 / API 接入狀態 / live 是否啟用」。
5. 所有家人 agent 的 live submit 預設 disabled；不得因 instance_config 有帳戶 alias 就送真單。

## 來源

- 元大證券 API 下單：https://www.yuanta.com.tw/file-repository/content/API/page/index.html
- 元大證券 API 申請說明：https://www.yuanta.com.tw/eyuanta/Securities/DigitalArea/ApiOrder?MainId=00410&C1=8d6fa61e-cbc3-45d8-b99e-3c8c6477f1ee&C2=&Level=1
- 國泰金控 CaaS 開發者中心：https://caas.cathayholdings.com/developerCenter/apiGuide
