# ETF_TW Release Notes v1.0.0

Release date: 2026-03-26

## Highlights
- 明確對齊 ETF 優先 / 台灣 ETF 優先 / 保留國外 ETF 能力 的技能主軸
- 補強永豐金證券（Shioaji）正式接入狀態說明
- 更新 TASKS.md，反映正式環境登入、帳務查詢、CA 啟用、基礎送單鏈路已完成
- 新增 README.md，補齊技能包標準入口說明
- 整理可分發版本規則，排除私密設定與本地殘留檔

## Packaging policy
The public v1.0.0 package excludes:
- assets/config.json
- .venv/
- __pycache__/
- *.pyc
- shioaji.log
- local/private test and review artifacts that may contain sensitive information

## Notes
This release is intended for public distribution without secrets. Personal account credentials, API keys, certificates, and environment files must stay outside the distributable package.
