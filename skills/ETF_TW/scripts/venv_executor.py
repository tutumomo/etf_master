#!/usr/bin/env python3
"""
ETF_TW Venv Executor - 強制使用正確的虛擬環境執行腳本

這個 executor 確保所有 ETF_TW 命令都使用正確的 .venv 環境，
避免因為環境錯誤導致「正式單變預演」的問題。

使用方式 (從 Hermes / 本地腳本呼叫):
    python scripts/venv_executor.py <script_name> [args...]

範例:
    python venv_executor.py complete_trade 00929 buy 200 --price 19.55

重要規則:
1. 正式送單一定走 skills/ETF_TW/.venv/bin/python
2. preview / live submit 分開，不能互相覆蓋
3. 所有執行都會傳遞 instance id（優先 AGENT_ID，兼容 legacy OPENCLAW_AGENT_NAME）
"""

import os
import subprocess
import sys
from pathlib import Path

# ETF_TW 技能根目錄
ETF_TW_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ETF_TW_ROOT / ".venv" / "bin" / "python"

# 檢查虛擬環境是否存在
if not VENV_PYTHON.exists():
    print(f"❌ 錯誤：虛擬環境不存在：{VENV_PYTHON}", file=sys.stderr)
    print("請先執行：python -m venv .venv && source .venv/bin/activate && pip install -r assets/requirements.txt", file=sys.stderr)
    sys.exit(1)

# 檢查 shioaji 是否已安裝 (僅警告，不阻斷)
SHIOAJI_INSTALLED = False
try:
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import shioaji"],
        check=True,
        capture_output=True,
        text=True
    )
    SHIOAJI_INSTALLED = True
except subprocess.CalledProcessError as e:
    print(f"⚠️  警告：shioaji 套件未安裝在虛擬環境中", file=sys.stderr)
    print(f"   錯誤：{e.stderr}", file=sys.stderr)
    print("如需正式下單，請執行：source .venv/bin/activate && pip install shioaji", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print("用法：python venv_executor.py <script_name> [args...]")
        print("")
        print("範例:")
        print("  python venv_executor.py complete_trade 00929 buy 200 --price 19.55")
        print("  python venv_executor.py trading_hours check")
        sys.exit(1)

    script_name = sys.argv[1]
    args = sys.argv[2:]

    # 支援子目錄腳本 (如 etf_core/main_service.py)
    if "/" in script_name:
        script_path = ETF_TW_ROOT / script_name
    else:
        script_path = ETF_TW_ROOT / "scripts" / f"{script_name}.py"

    if not script_path.exists():
        print(f"❌ 錯誤：腳本不存在：{script_path}", file=sys.stderr)
        sys.exit(1)

    # 使用虛擬環境的 Python 執行
    print(f"[VENV] 使用虛擬環境：{VENV_PYTHON}")
    print(f"[VENV] 執行腳本：{script_path}")
    if args:
        print(f"[VENV] 參數：{' '.join(args)}")
    print("-" * 60)

    # 設置環境變數
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ETF_TW_ROOT) + ":" + env.get("PYTHONPATH", "")
    env["ETF_TW_ROOT"] = str(ETF_TW_ROOT)

    # 傳遞 instance id 以保持 state 對齊（優先 AGENT_ID，兼容 legacy OPENCLAW_AGENT_NAME）
    for var in ["AGENT_ID", "OPENCLAW_AGENT_NAME"]:
        if var in os.environ:
            env[var] = os.environ[var]

    # 執行腳本
    result = subprocess.run(
        [str(VENV_PYTHON), str(script_path)] + args,
        env=env,
        cwd=str(ETF_TW_ROOT),
        text=True
    )

    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
