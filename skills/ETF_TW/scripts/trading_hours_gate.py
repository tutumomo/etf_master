#!/usr/bin/env python3
"""
交易時段硬閘門 - 非交易時段直接阻斷送單

台灣股票市場交易時段：
- 一般盤：09:00 - 13:30（當日現股買賣）
- 盤後零股：13:40 - 14:30（僅限零股交易）
- 其餘時段：非委託時間，無法下單

強制行為：收到下單指令時，第一優先判斷當前是否在交易時段。
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import sys

TW_TZ = ZoneInfo('Asia/Taipei')

# 交易時段定義
MARKET_OPEN = datetime.strptime("09:00", "%H:%M").time()
MARKET_CLOSE = datetime.strptime("13:30", "%H:%M").time()
AFTER_HOURS_START = datetime.strptime("13:40", "%H:%M").time()
AFTER_HOURS_END = datetime.strptime("14:30", "%H:%M").time()


def check_trading_hours_gate() -> str:
    """
    檢查當前是否在交易時段內。

    Returns:
        str: "regular" (一般盤), "after_hours" (盤後零股), 或拋出異常

    Raises:
        SystemExit: 如果不在交易時段內
    """
    now = datetime.now(TW_TZ)

    # 週末檢查
    if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        print("❌ 錯誤：現在是週末，台灣股市休市，無法下單", file=sys.stderr)
        sys.exit(1)

    current_time = now.time().replace(second=0, microsecond=0)

    # 檢查是否在一般盤時段
    if MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return "regular"

    # 檢查是否在盤後零股時段
    if AFTER_HOURS_START <= current_time <= AFTER_HOURS_END:
        return "after_hours"

    # 非交易時段
    print(f"❌ 錯誤：現在非交易時段 ({current_time.strftime('%H:%M')})，無法下單", file=sys.stderr)
    print("   台灣股市交易時段：", file=sys.stderr)
    print("   - 一般盤：09:00 - 13:30", file=sys.stderr)
    print("   - 盤後零股：13:40 - 14:30", file=sys.stderr)
    sys.exit(1)


def is_trading_hours() -> bool:
    """
    檢查當前是否在交易時段內（不拋出異常，僅返回布林值）。

    Returns:
        bool: True 如果在交易時段內，False 否則
    """
    now = datetime.now(TW_TZ)

    if now.weekday() >= 5:
        return False

    current_time = now.time().replace(second=0, microsecond=0)

    if MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return True

    if AFTER_HOURS_START <= current_time <= AFTER_HOURS_END:
        return True

    return False


def get_trading_hours_info() -> dict:
    """
    獲取交易時段資訊。

    Returns:
        dict: 包含交易時段資訊的字典
    """
    now = datetime.now(TW_TZ)
    current_time = now.time().replace(second=0, microsecond=0)
    is_weekend = now.weekday() >= 5

    in_regular = not is_weekend and MARKET_OPEN <= current_time <= MARKET_CLOSE
    in_after_hours = not is_weekend and AFTER_HOURS_START <= current_time <= AFTER_HOURS_END

    return {
        "is_trading_hours": not is_weekend and (in_regular or in_after_hours),
        "is_weekend": is_weekend,
        "current_time": current_time.strftime("%H:%M"),
        "in_regular_hours": in_regular,
        "in_after_hours": in_after_hours,
        "regular_hours": "09:00 - 13:30",
        "after_hours": "13:40 - 14:30",
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # 檢查模式
        info = get_trading_hours_info()
        print("交易時段檢查結果：")
        print(f"  當前時間：{info['current_time']}")
        print(f"  是否交易時段：{'是' if info['is_trading_hours'] else '否'}")
        print(f"  一般盤時段：{info['regular_hours']} - {'✓' if info['in_regular_hours'] else '✗'}")
        print(f"  盤後零股：{info['after_hours']} - {'✓' if info['in_after_hours'] else '✗'}")
    else:
        # 硬閘門模式
        try:
            result = check_trading_hours_gate()
            print(f"✓ 交易時段檢查通過：目前是 {result} 時段")
        except SystemExit as e:
            raise
