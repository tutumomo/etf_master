"""
Cathay (國泰證券) Broker API Integration (Placeholder)
"""
from typing import Dict, Tuple, Optional
from .base_broker import BaseBroker

class CathayBroker(BaseBroker):
    def connect(self) -> bool:
        print("[Cathay] Not connected: official securities trading API is not integrated")
        self.connected = False
        return False

    def get_account_balance(self) -> Dict:
        return {"cash": 0, "purchasing_power": 0, "currency": "TWD", "status": "not_integrated"}

    def get_inventory(self) -> list[Dict]:
        return []

    def place_order(self, symbol: str, action: str, quantity: int, price: Optional[float] = None, order_type: str = 'MARKET') -> Tuple[bool, str, Optional[Dict]]:
        return False, "國泰 adapter 尚未整合官方 API，禁止回傳假成功", {
            "broker": "Cathay",
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "status": "not_integrated"
        }
