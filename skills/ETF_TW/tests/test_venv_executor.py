#!/usr/bin/env python3
"""
Test venv_executor.py and trading_hours_gate.py

測試重點:
1. venv_executor.py 正確使用 .venv/bin/python
2. trading_hours_gate.py 正確檢查交易時段
3. state_reconciliation_enhanced.py 正確對帳
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ETF_TW_ROOT / ".venv" / "bin" / "python"


def test_venv_exists():
    """測試虛擬環境是否存在"""
    print("測試 1: 檢查虛擬環境...")
    assert VENV_PYTHON.exists(), f"❌ 虛擬環境不存在：{VENV_PYTHON}"
    print(f"  ✓ 虛擬環境存在：{VENV_PYTHON}")
    return True


def test_shioaji_installed():
    """測試 shioaji 是否已安裝"""
    print("測試 2: 檢查 shioaji 套件...")
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "-c", "import shioaji"],
            check=True,
            capture_output=True,
            text=True
        )
        print("  ✓ shioaji 已安裝")
        return True
    except subprocess.CalledProcessError:
        print("  ⚠️  shioaji 未安裝 (可選，如需正式下單請安裝)")
        return True  # 不強制要求


def test_trading_hours_gate():
    """測試交易時段閘門"""
    print("測試 3: 檢查交易時段閘門...")

    # 載入模組
    sys.path.insert(0, str(ETF_TW_ROOT / "scripts"))
    from trading_hours_gate import is_trading_hours, get_trading_hours_info

    info = get_trading_hours_info()
    print(f"  當前時間：{info['current_time']}")
    print(f"  是否交易時段：{'是' if info['is_trading_hours'] else '否'}")

    # 驗證邏輯
    now = datetime.now(ZoneInfo('Asia/Taipei'))
    expected_trading = now.weekday() < 5 and (
        datetime.strptime("09:00", "%H:%M").time() <= now.time().replace(second=0, microsecond=0) <= datetime.strptime("13:30", "%H:%M").time() or
        datetime.strptime("13:40", "%H:%M").time() <= now.time().replace(second=0, microsecond=0) <= datetime.strptime("14:30", "%H:%M").time()
    )

    assert info['is_trading_hours'] == expected_trading, "交易時段判斷錯誤"
    print("  ✓ 交易時段閘門邏輯正確")
    return True


def test_venv_executor_script():
    """測試 venv_executor.py 腳本"""
    print("測試 4: 檢查 venv_executor.py...")

    script_path = ETF_TW_ROOT / "scripts" / "venv_executor.py"
    assert script_path.exists(), f"腳本不存在：{script_path}"

    # 測試執行 without args (應該顯示使用說明)
    result = subprocess.run(
        [str(VENV_PYTHON), str(script_path)],
        capture_output=True,
        text=True
    )

    assert "用法：" in result.stdout, "應該顯示使用說明"
    print("  ✓ venv_executor.py 執行正常")
    return True


def test_state_reconciliation_script():
    """測試 state_reconciliation_enhanced.py 腳本"""
    print("測試 5: 檢查 state_reconciliation_enhanced.py...")

    script_path = ETF_TW_ROOT / "scripts" / "state_reconciliation_enhanced.py"
    assert script_path.exists(), f"腳本不存在：{script_path}"

    # 測試執行 (應該能正常啟動)
    result = subprocess.run(
        [str(VENV_PYTHON), str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(ETF_TW_ROOT)
    )

    # 應該輸出對帳結果
    assert "狀態對帳檢查" in result.stdout or "對帳時間" in result.stdout, "應該輸出對帳結果"
    print("  ✓ state_reconciliation_enhanced.py 執行正常")
    return True


def main():
    """執行所有測試"""
    print("=" * 72)
    print("ETF_TW 修復驗證測試")
    print("=" * 72)

    tests = [
        test_venv_exists,
        test_shioaji_installed,
        test_trading_hours_gate,
        test_venv_executor_script,
        test_state_reconciliation_script,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ❌ 測試失敗：{e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ 測試錯誤：{e}")
            failed += 1

    print("\n" + "=" * 72)
    print(f"測試結果：{passed} 通過，{failed} 失敗")
    print("=" * 72)

    if failed > 0:
        sys.exit(1)

    print("\n✅ 所有測試通過！修復已正確實施。")
    sys.exit(0)


if __name__ == "__main__":
    main()
