#!/usr/bin/env python3
"""
Base adapter class for ETF_TW multi-broker architecture.

All broker adapters must inherit from this base class and implement
the required methods for their specific broker.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List, Any, final
from datetime import datetime
import json


@dataclass
class Order:
    """Represents an order (preview, paper, or live)."""
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: int
    price: Optional[float] = None
    order_type: str = 'limit'  # 'limit' or 'market'
    account_id: Optional[str] = None
    broker_id: Optional[str] = None
    mode: str = 'paper'  # 'paper', 'sandbox', 'live'
    status: str = 'pending'  # 'pending', 'submitted', 'filled', 'cancelled', 'rejected'
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    fee: float = 0.0
    tax: float = 0.0
    error: Optional[str] = None
    _truth_level: str = "SNAPSHOT"


@dataclass
class Position:
    """Represents a position in an account."""
    symbol: str
    quantity: int
    average_price: float
    current_price: Optional[float] = None
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    _truth_level: str = "SNAPSHOT"


@dataclass
class AccountBalance:
    """Represents account balance."""
    account_id: str
    broker_id: str
    buying_power: float = 0.0
    cash_available: float = 0.0
    market_value: float = 0.0
    total_value: float = 0.0
    unrealized_pnl: float = 0.0
    _truth_level: str = "SNAPSHOT"


class MarketDataProvider:
    """Centralized market data provider using yfinance as fallback."""
    
    @staticmethod
    async def get_price(symbol: str) -> float:
        """Get current price for a symbol (TWD)."""
        try:
            import yfinance as yf
            ticker = f"{symbol}.TW"
            data = yf.download(ticker, period="1d", progress=False)
            if not data.empty:
                return float(data["Close"].iloc[-1])
        except Exception:
            pass
        return 0.0

    @staticmethod
    async def get_full_data(symbol: str) -> Dict[str, Any]:
        """Get full market data (price, change, volume)."""
        try:
            import yfinance as yf
            ticker = f"{symbol}.TW"
            # Use Ticker object for more details
            tk = yf.Ticker(ticker)
            fast = tk.fast_info
            return {
                'symbol': symbol,
                'price': fast.last_price,
                'change': 0.0, # Calculation needed if not in fast_info
                'change_percent': 0.0,
                'volume': fast.last_volume,
                'timestamp': datetime.now()
            }
        except Exception:
            return {
                'symbol': symbol,
                'price': 0.0,
                'timestamp': datetime.now()
            }


class BaseAdapter(ABC):
    """
    Abstract base class for all broker adapters.
    """
    
    def __init__(self, broker_id: str, config: Dict[str, Any]):
        self.broker_id = broker_id
        self.config = config
        self.authenticated = False
        self.mode = config.get('mode', 'paper') # paper, sandbox, live
        self.market_provider = MarketDataProvider()
        
    @abstractmethod
    async def authenticate(self) -> bool:
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_account_balance(self, account_id: str) -> AccountBalance:
        pass
    
    @abstractmethod
    async def get_positions(self, account_id: str) -> List[Position]:
        pass
    
    @abstractmethod
    async def preview_order(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def validate_order(self, order: Order) -> tuple[bool, List[str]]:
        pass
    
    @final
    async def submit_order(self, order: Order) -> Order:
        """
        Unified order submission gate.
        Enforces pre-flight checks and post-submit verification. (WR-03)
        """
        # 1. Prepare context for pre-flight gate (WR-01)
        context = {
            'cash': 0.0,
            'max_concentration_pct': self.config.get('max_concentration_pct', 0.3),
            'max_single_limit_twd': self.config.get('max_single_limit_twd', 500000.0),
            'risk_temperature': self.config.get('risk_temperature', 1.0),
            'force_trading_hours': self.config.get('force_trading_hours', True),
            'inventory': {},
            'current_holding_value': 0.0,
            'total_portfolio_value': 0.0
        }
        
        # 統一獲取帳戶狀態，為風控提供資料
        try:
            balance = await self.get_account_balance(order.account_id or "")
            context['cash'] = balance.cash_available
            context['total_portfolio_value'] = balance.total_value
            
            positions = await self.get_positions(order.account_id or "")
            context['inventory'] = {p.symbol: p.quantity for p in positions}
            for p in positions:
                if p.symbol == order.symbol:
                    context['current_holding_value'] = p.market_value
                    break
        except Exception as e:
            # 獲取帳戶資料失敗，保險起見記錄錯誤
            print(f"[BaseAdapter] Failed to fetch account state: {e}")

        # --- 修正後的 lot_type 判定邏輯 (WR-01) ---
        lot_type = getattr(order, 'lot_type', None)
        if lot_type is None:
            lot_type = 'board' if order.quantity >= 1000 else 'odd'

        order_dict = {
            'symbol': order.symbol,
            'side': order.action,
            'quantity': order.quantity,
            'price': order.price or 0.0,
            'order_type': order.order_type,
            'lot_type': lot_type,
            'is_submit': True, # 代表實際執行送單
            'is_confirmed': getattr(order, 'is_confirmed', False)
        }
        
        try:
            from scripts.pre_flight_gate import check_order
        except ImportError:
            try:
                from ..pre_flight_gate import check_order
            except Exception:
                # Fallback to local import if everything fails
                import sys
                from pathlib import Path
                SCRIPTS_DIR = Path(__file__).resolve().parents[1]
                if str(SCRIPTS_DIR) not in sys.path:
                    sys.path.append(str(SCRIPTS_DIR))
                from pre_flight_gate import check_order

        gate_result = check_order(order_dict, context)
        
        if not gate_result.get('passed', False):
            order.status = 'rejected'
            order.error = f"[Pre-flight Gate] {gate_result.get('reason')}: {gate_result.get('details')}"
            return order
            
        # 2. Implementation call
        submitted_order = await self._submit_order_impl(order)
        
        # 3. Post-submit verification
        order_id = getattr(submitted_order, 'order_id', None)
        if submitted_order.status in ['submitted', 'pending'] and order_id:
             # 可能需要延後或重試，目前維持現狀
             try:
                 from scripts.submit_verification import verify_order_landing
                 verification = await verify_order_landing(self, str(order_id))
                 submitted_order._truth_level = verification.get('_truth_level', submitted_order._truth_level)
                 if verification.get('verified', False):
                     # Update status if verified as landed
                     submitted_order.status = verification.get('status', submitted_order.status)
             except ImportError: pass
             
        return submitted_order

    @abstractmethod
    async def _submit_order_impl(self, order: Order) -> Order:
        """Actual broker-specific submission logic."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        pass

    @abstractmethod
    async def list_trades(self) -> List[Any]:
        """List trades (orders) for the current session/account."""
        pass

    async def get_order_history(self, account_id: str, days: int = 30) -> List[Order]:
        """Default empty implementation for order history."""
        return []
    
    def calculate_fee(self, amount: float) -> float:
        fee_rate = self.config.get('fee_rate', 0.001425)
        min_fee = self.config.get('min_fee', 20)
        discount = self.config.get('fee_discount', 1.0) # 6折 -> 0.6
        fee = amount * fee_rate * discount
        return max(round(fee), min_fee)
    
    def calculate_tax(self, amount: float, is_sell: bool) -> float:
        if not is_sell:
            return 0.0
        tax_rate = self.config.get('tax_rate', 0.003)
        return round(amount * tax_rate)
    
    def get_broker_info(self) -> Dict[str, Any]:
        return {
            'broker_id': self.broker_id,
            'mode': self.mode,
            'authenticated': self.authenticated,
            'capabilities': self.config.get('capabilities', [])
        }


def get_adapter(broker_id: str, config: Dict[str, Any]) -> BaseAdapter:
    # Import adapters lazily to avoid circular dependencies
    from .paper_adapter import PaperAdapter
    from .sinopac_adapter import SinopacAdapter
    
    # Map broker IDs to their adapter classes
    adapter_map = {
        'paper': PaperAdapter,
        'sinopac': SinopacAdapter,
    }
    
    # Handle optional adapters
    try: from .cathay_adapter import CathayAdapter; adapter_map['cathay'] = CathayAdapter
    except ImportError: pass
    
    if broker_id not in adapter_map:
        raise ValueError(f"Unsupported broker: {broker_id}")
    
    adapter_class = adapter_map[broker_id]
    return adapter_class(broker_id, config)
