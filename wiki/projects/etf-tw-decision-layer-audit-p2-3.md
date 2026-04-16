# ETF_TW 決策層審計（P2-3）

## 結論
決策層目前已經比早期版本成熟，但仍有 3 類風險：
1. 建議數量仍有硬編碼傾向
2. AI reasoning 雖然不再是空字串，但仍偏「摘要式合理化」
3. consensus 仲裁可用，但目前仍偏 preview 治理，不是完整執行治理

## 已修 bug
- `generate_ai_agent_response.py` 的 confidence 降級邏輯原本會把 low 誤升成 medium，現已修正為 high→medium、medium→low、low 保持 low。

## 主要風險
### 1. 建議數量硬編碼
- `run_auto_decision_scan.py` preview payload `quantity=100`
- `generate_ai_agent_response.py` candidate `quantity=100`
- 目前較像 placeholder，不是真正 sizing

### 2. reasoning 仍偏事後合理化
- 有 market / position / risk 摘要
- 但仍需更緊密對齊實際 score path

### 3. consensus 偏 preview 治理
- 目前主要影響 preview mode 標記
- 還不等於完整 live execution gate
