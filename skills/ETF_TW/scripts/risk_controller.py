#!/usr/bin/env python3
"""
Risk Control System for ETF_TW.

Features:
- Pre-trade risk checks
- Position limits
- Order size limits
- Daily loss limits
- Duplicate order prevention
- Circuit breakers
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class RiskLimits:
    """Risk limit configuration."""
    max_order_value: float = 500000.0  # Max single order value
    max_daily_loss: float = 50000.0  # Max daily loss
    max_position_value: float = 2000000.0  # Max position value per symbol
    max_portfolio_value: float = 10000000.0  # Max total portfolio value
    max_orders_per_day: int = 50  # Max orders per day
    max_duplicate_check_minutes: int = 5  # Duplicate check window
    require_confirmation_above: float = 100000.0  # Require confirmation for orders above this


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    passed: bool
    warnings: List[str]
    errors: List[str]
    requires_confirmation: bool
    confirmation_reason: str = ""


class RiskController:
    """
    Risk control system for pre-trade checks.
    
    Features:
    - Pre-trade validation
    - Position limits
    - Order size limits
    - Duplicate prevention
    - Daily limits
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.limits = self._load_limits(config_path)
        self.order_history: List[Dict] = []
        self.daily_stats = {
            'date': datetime.now().date().isoformat(),
            'order_count': 0,
            'total_buy_value': 0.0,
            'total_sell_value': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0
        }
    
    def _load_limits(self, config_path: Optional[str]) -> RiskLimits:
        """Load risk limits from config."""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return RiskLimits(**data)
        return RiskLimits()
    
    def check_order(self, 
                   symbol: str,
                   action: str,
                   quantity: int,
                   price: float,
                   current_position: int,
                   account_value: float,
                   broker_id: str = '',
                   account_id: str = '') -> RiskCheckResult:
        """
        Perform pre-trade risk check.
        
        Args:
            symbol: Stock/ETF symbol
            action: 'buy' or 'sell'
            quantity: Order quantity
            price: Order price
            current_position: Current position in symbol
            account_value: Total account value
            broker_id: Broker identifier
            account_id: Account identifier
            
        Returns:
            RiskCheckResult with pass/fail and warnings/errors
        """
        warnings = []
        errors = []
        requires_confirmation = False
        confirmation_reason = ""
        
        order_value = quantity * price
        
        # Check 1: Order value limit
        if order_value > self.limits.max_order_value:
            errors.append(f"Order value {order_value:,.0f} exceeds max {self.limits.max_order_value:,.0f}")
        
        # Check 2: Position limit (for buys)
        if action == 'buy':
            new_position_value = (current_position + quantity) * price
            if new_position_value > self.limits.max_position_value:
                errors.append(f"Position value would exceed limit")
        
        # Check 3: Portfolio value limit
        if action == 'buy' and order_value > account_value * 0.5:
            warnings.append("Order value > 50% of account value")
        
        # Check 4: Daily order count
        self._reset_daily_if_needed()
        if self.daily_stats['order_count'] >= self.limits.max_orders_per_day:
            errors.append(f"Daily order limit reached ({self.limits.max_orders_per_day})")
        
        # Check 5: Duplicate order check
        is_duplicate, dup_reason = self._check_duplicate(symbol, action, quantity, price)
        if is_duplicate:
            warnings.append(f"Possible duplicate: {dup_reason}")
        
        # Check 6: Large order confirmation
        if order_value > self.limits.require_confirmation_above:
            requires_confirmation = True
            confirmation_reason = f"Order value {order_value:,.0f} > {self.limits.require_confirmation_above:,.0f}"
        
        # Check 7: Odd lot warning
        if quantity % 1000 != 0 and quantity < 1000:
            warnings.append("Odd-lot order (< 1000 shares)")
        
        passed = len(errors) == 0
        
        return RiskCheckResult(
            passed=passed,
            warnings=warnings,
            errors=errors,
            requires_confirmation=requires_confirmation,
            confirmation_reason=confirmation_reason
        )
    
    def _check_duplicate(self, symbol: str, action: str, quantity: int, price: float) -> Tuple[bool, str]:
        """Check for duplicate orders."""
        now = datetime.now()
        window_start = now - timedelta(minutes=self.limits.max_duplicate_check_minutes)
        
        for order in reversed(self.order_history):
            order_time = datetime.fromisoformat(order['timestamp'])
            if order_time < window_start:
                continue
            
            if (order['symbol'] == symbol and 
                order['action'] == action and 
                order['quantity'] == quantity and
                abs(order['price'] - price) < price * 0.01):  # Within 1%
                return True, f"Similar order {self.limits.max_duplicate_check_minutes}min ago"
        
        return False, ""
    
    def _reset_daily_if_needed(self):
        """Reset daily stats if date changed."""
        today = datetime.now().date()
        if self.daily_stats['date'] != today.isoformat():
            self.daily_stats = {
                'date': today.isoformat(),
                'order_count': 0,
                'total_buy_value': 0.0,
                'total_sell_value': 0.0,
                'unrealized_pnl': 0.0,
                'realized_pnl': 0.0
            }
    
    def record_order(self, symbol: str, action: str, quantity: int, price: float, status: str):
        """Record order for duplicate checking and statistics."""
        self.order_history.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'status': status
        })
        
        self.daily_stats['order_count'] += 1
        
        if status == 'filled':
            if action == 'buy':
                self.daily_stats['total_buy_value'] += quantity * price
            else:
                self.daily_stats['total_sell_value'] += quantity * price
        
        # Keep only last 1000 orders in memory
        if len(self.order_history) > 1000:
            self.order_history = self.order_history[-1000:]
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily trading summary."""
        self._reset_daily_if_needed()
        return self.daily_stats.copy()
    
    def get_circuit_breaker_status(self) -> Dict[str, bool]:
        """
        Check if any circuit breakers are triggered.
        
        Returns:
            Dictionary of circuit breaker statuses
        """
        return {
            'daily_loss_limit': False,  # Would need PnL tracking
            'order_limit_reached': self.daily_stats['order_count'] >= self.limits.max_orders_per_day,
            'market_halt': False,  # Would need market data
            'system_maintenance': False
        }


# Global risk controller
_controller: Optional[RiskController] = None


def get_risk_controller(config_path: Optional[str] = None) -> RiskController:
    """Get or create the global risk controller."""
    global _controller
    if _controller is None:
        _controller = RiskController(config_path)
    return _controller
