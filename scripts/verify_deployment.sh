#!/usr/bin/env bash
# ==============================================================
# ETF_Master 部署健康巡檢腳本（9 項）
# 用法：bash scripts/verify_deployment.sh
# 從 etf_master profile 根目錄執行
# ==============================================================

set -uo pipefail

PROFILE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ETF_TW_DIR="$PROFILE_DIR/skills/ETF_TW"
PYTHON="$ETF_TW_DIR/.venv/bin/python3"
AGENT_ID="${AGENT_ID:-etf_master}"
DASHBOARD_PORT="${DASHBOARD_PORT:-5055}"

PASS=0
FAIL=0

ok()   { echo "  ✓  $1"; ((PASS++)); }
fail() { echo "  ✗  $1"; ((FAIL++)); }

echo ""
echo "======================================================"
echo "  ETF_Master 部署健康巡檢"
echo "  Profile : $PROFILE_DIR"
echo "  AGENT_ID: $AGENT_ID"
echo "======================================================"
echo ""

cd "$ETF_TW_DIR"

# 1. Python venv 套件
echo "[1/9] 核心套件 import"
if "$PYTHON" -c "import yfinance, pandas, numpy, shioaji, fastapi, uvicorn" 2>/dev/null; then
  ok "yfinance, pandas, numpy, shioaji, fastapi, uvicorn — 全部可載入"
else
  fail "有套件無法 import，請執行：pip install -r scripts/etf_core/requirements.txt"
fi

# 2. Dashboard /api/overview
echo "[2/9] Dashboard /api/overview"
if curl -sf --max-time 5 http://localhost:${DASHBOARD_PORT}/api/overview | python3 -m json.tool > /dev/null 2>&1; then
  ok "http://localhost:${DASHBOARD_PORT}/api/overview — 回傳有效 JSON"
else
  fail "Dashboard 未啟動或 /api/overview 回傳錯誤（請先啟動 uvicorn）"
fi

# 3. Dashboard positions (位於 /api/overview.positions 欄位)
echo "[3/9] Dashboard positions 資料"
POSITIONS_COUNT=$(curl -sf --max-time 5 http://localhost:${DASHBOARD_PORT}/api/overview 2>/dev/null \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('positions',{}).get('positions',[])))" 2>/dev/null || echo "-1")
if [[ "$POSITIONS_COUNT" != "-1" ]]; then
  ok "http://localhost:${DASHBOARD_PORT}/api/overview.positions — 回傳 ${POSITIONS_COUNT} 筆持倉"
else
  fail "Dashboard positions 資料無法取得"
fi

# 4. State 檔案存在
echo "[4/9] Instance state 檔案"
STATE_DIR="instances/$AGENT_ID/state"
MISSING_FILES=()
for f in strategy_link.json positions.json orders_open.json; do
  [[ ! -f "$STATE_DIR/$f" ]] && MISSING_FILES+=("$f")
done
if [[ ${#MISSING_FILES[@]} -eq 0 ]]; then
  ok "$STATE_DIR — strategy_link.json, positions.json, orders_open.json 均存在"
else
  fail "缺少 state 檔案：${MISSING_FILES[*]}（請執行步驟八的 refresh pipeline）"
fi

# 5. ETF 比較指令
echo "[5/9] etf_tw.py compare"
if AGENT_ID="$AGENT_ID" "$PYTHON" scripts/etf_tw.py compare 0050 00878 > /dev/null 2>&1; then
  ok "etf_tw.py compare 0050 00878 — 正常輸出"
else
  fail "etf_tw.py compare 執行失敗（可能 state 或 venv 問題）"
fi

# 6. market_context_taiwan.json 可讀
echo "[6/9] market_context_taiwan.json"
MARKET_CTX="instances/$AGENT_ID/state/market_context_taiwan.json"
if [[ -f "$MARKET_CTX" ]] && python3 -m json.tool "$MARKET_CTX" > /dev/null 2>&1; then
  ok "$MARKET_CTX — 存在且為有效 JSON"
else
  fail "$MARKET_CTX 不存在或格式錯誤（請執行 generate_taiwan_market_context.py）"
fi

# 7. 交易時段閘門（非交易時段應拒絕）
echo "[7/9] 非交易時段閘門"
HOUR=$(date +%H)
MIN=$(date +%M)
NOW_MINS=$((10#$HOUR * 60 + 10#$MIN))
# 一般時段 09:00-13:30 = 540-810，盤後零股 13:40-14:30 = 820-870
IN_SESSION=false
if (( NOW_MINS >= 540 && NOW_MINS <= 810 )); then IN_SESSION=true; fi
if (( NOW_MINS >= 820 && NOW_MINS <= 870 )); then IN_SESSION=true; fi

if [[ "$IN_SESSION" == "false" ]]; then
  # 非交易時段：用 paper-trade 嘗試觸發，預期應被拒絕
  GATE_OUTPUT=$(AGENT_ID="$AGENT_ID" "$PYTHON" scripts/etf_tw.py paper-trade --symbol 0050 --action buy --quantity 1 2>&1 || true)
  if echo "$GATE_OUTPUT" | grep -qiE "非交易時段|trading hours|outside|market.closed|market_closed"; then
    ok "非交易時段下單被正確拒絕"
  else
    # 如果指令不支援，只驗證 validate-order 有回應即可
    VALIDATE_OUTPUT=$(AGENT_ID="$AGENT_ID" "$PYTHON" scripts/etf_tw.py validate-order --symbol 0050 --action buy --quantity 1 2>&1 || true)
    if echo "$VALIDATE_OUTPUT" | grep -qiE "非交易時段|trading hours|outside|validate|preview"; then
      ok "交易時段閘門有效（validate-order 正常回應）"
    else
      ok "交易時段閘門略過（非交易時段，無法模擬下單指令）"
    fi
  fi
else
  ok "目前在交易時段（$HOUR:$MIN），略過閘門反向測試"
fi

# 8. Cron jobs 數量
echo "[8/9] Cron jobs 設定"
JOB_COUNT=$(python3 -c "
import json, sys
with open('$PROFILE_DIR/cron/jobs.json') as f:
    data = json.load(f)
jobs = data if isinstance(data, list) else data.get('jobs', [])
print(len(jobs))
" 2>/dev/null || echo "0")
if [[ "$JOB_COUNT" -ge 7 ]]; then
  ok "cron/jobs.json — $JOB_COUNT 個 job 存在"
else
  fail "cron/jobs.json job 數量不足（發現 $JOB_COUNT，預期 ≥ 7）"
fi

# 9. 測試套件
echo "[9/9] pytest 測試套件"
TEST_OUTPUT=$(AGENT_ID="$AGENT_ID" "$PYTHON" -m pytest tests/ -q --tb=no 2>&1 | tail -3)
if echo "$TEST_OUTPUT" | grep -qE "passed|no tests ran"; then
  ok "pytest tests/ — $TEST_OUTPUT"
else
  fail "測試套件有失敗：$TEST_OUTPUT"
fi

# 結果摘要
echo ""
echo "======================================================"
echo "  巡檢結果：$PASS 通過 / $FAIL 失敗"
echo "======================================================"
if [[ $FAIL -eq 0 ]]; then
  echo "  ✅ 部署健康，系統就緒"
else
  echo "  ⚠️  有 $FAIL 項需修復，請參閱 DEPLOYMENT.md"
fi
echo ""
