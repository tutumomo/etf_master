"""
auto_trade — Phase 2 半自動交易模組

模組組成：
  vwap_calculator.py   30 分鐘 VWAP 計算（買入掃描的核心數據）
  buy_scanner.py       09:30/11:00/13:00 買入訊號掃描
  sell_scanner.py      13:15 trailing stop 賣出訊號掃描
  peak_tracker.py      持倉以來收盤最高價追蹤
  pending_queue.py     待 ack 訊號管理
  circuit_breaker.py   Kill-switch 熔斷器
  ack_handler.py       Dashboard ack/reject API 後端

設計原則：
  1. 所有訊號最終都走 scripts.pre_flight_gate.check_order()，不繞過任何安全檢查
  2. 半自動：訊號入 pending queue，使用者 ack 後才下單
  3. 訊號 15 分鐘未 ack 自動過期
  4. 所有觸發、ack、reject、過期、執行都寫入 auto_trade_history.jsonl
"""

__version__ = "0.1.0-phase2"
