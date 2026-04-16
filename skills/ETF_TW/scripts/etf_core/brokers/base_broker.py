"""
Base Broker Interface for ETF_TW Pro
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional

class BaseBroker(ABC):
    def __init__(self, account_id: str, api_key: str, secret_key: str, is_simulation: bool = True):
        self.account_id = account_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.is_simulation = is_simulation
        self.connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker's API"""
        pass
        
    @abstractmethod
    def get_account_balance(self) -> Dict:
        """Get cash balance and purchasing power"""
        pass
        
    @abstractmethod
    def get_inventory(self) -> list[Dict]:
        """Get current stock/ETF holdings"""
        pass
        
    @abstractmethod
    def place_order(self, symbol: str, action: str, quantity: int, price: Optional[float] = None, order_type: str = 'MARKET') -> Tuple[bool, str, Optional[Dict]]:
        """
        Place an order
        action: 'BUY' or 'SELL'
        order_type: 'MARKET' or 'LIMIT'
        Returns (success, message, order_details)
        """
        pass
