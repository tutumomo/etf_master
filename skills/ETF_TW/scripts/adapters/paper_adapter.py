#!/usr/bin/env python3
"""
Paper Trading Adapter for ETF_TW.

This adapter simulates trading without real money.
Used for testing and learning.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from .base import BaseAdapter, Order, Position, AccountBalance


class PaperAdapter(BaseAdapter):
    """
    Paper trading adapter - simulates trading without real money.
    
    This adapter:
    - Maintains virtual balances and positions
    - Simulates order execution
    - Tracks paper trading history
    """
    
    def __init__(self, broker_id: str, config: Dict[str, Any]):
        super().__init__(broker_id, config)
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Order] = {}
        self.initial_balance = config.get('initial_balance', 1000000)
        
    async def authenticate(self) -> bool:
        """Authenticate for paper trading (always succeeds)."""
        account_id = self.config.get('account_id', 'paper_001')
        
        if account_id not in self.accounts:
            self.accounts[account_id] = {
                'balance': self.initial_balance,
                'buying_power': self.initial_balance,
                'positions': {},
                'created_at': datetime.now()
            }
        
        self.authenticated = True
        return True
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get simulated market data.
        
        For paper trading, we use mock data or fetch from public sources.
        """
        # In real implementation, this would fetch from TWSE or other sources
        # For now, return mock data
        return {
            'symbol': symbol,
            'price': 100.0,  # Mock price
            'change': 0.0,
            'change_percent': 0.0,
            'volume': 0,
            'timestamp': datetime.now()
        }
    
    async def get_account_balance(self, account_id: str) -> AccountBalance:
        """Get account balance."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        
        account = self.accounts[account_id]
        positions_value = sum(
            pos.get('quantity', 0) * pos.get('average_price', 0)
            for pos in account['positions'].values()
        )
        
        return AccountBalance(
            account_id=account_id,
            broker_id=self.broker_id,
            buying_power=account['buying_power'],
            cash_available=account['balance'],
            market_value=positions_value,
            total_value=account['balance'] + positions_value,
            unrealized_pnl=0.0  # Simplified
        )
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get account positions."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        
        account = self.accounts[account_id]
        positions = []
        
        for symbol, pos_data in account['positions'].items():
            positions.append(Position(
                symbol=symbol,
                quantity=pos_data['quantity'],
                average_price=pos_data['average_price'],
                current_price=pos_data.get('current_price', pos_data['average_price']),
                market_value=pos_data['quantity'] * pos_data.get('current_price', pos_data['average_price']),
                unrealized_pnl=0.0  # Simplified
            ))
        
        return positions
    
    async def preview_order(self, order: Order) -> Order:
        """Preview order with fee calculations."""
        # Get current price (mock)
        market_data = await self.get_market_data(order.symbol)
        price = order.price or market_data['price']
        
        # Calculate amounts
        quantity = order.quantity
        amount = price * quantity
        
        # Calculate fees and taxes
        fee = self.calculate_fee(amount)
        tax = self.calculate_tax(amount, order.action == 'sell')
        
        # Update order with preview data
        order.fee = fee
        order.tax = tax
        order.status = 'preview'
        
        return order
    
    async def validate_order(self, order: Order) -> tuple[bool, List[str]]:
        """Validate order before submission."""
        warnings = []
        
        # Check if authenticated
        if not self.authenticated:
            return False, ['Not authenticated']
        
        # Check account balance
        account_id = order.account_id or self.config.get('account_id', 'paper_001')
        if account_id not in self.accounts:
            return False, ['Account not found']
        
        account = self.accounts[account_id]
        
        # Get order amount
        market_data = await self.get_market_data(order.symbol)
        price = order.price or market_data['price']
        amount = price * order.quantity
        
        if order.action == 'buy':
            total_cost = amount + order.fee + order.tax
            if total_cost > account['buying_power']:
                return False, ['Insufficient buying power']
        else:  # sell
            if order.symbol not in account['positions']:
                return False, ['No position in this symbol']
            if account['positions'][order.symbol]['quantity'] < order.quantity:
                return False, ['Insufficient position quantity']
        
        # Add warnings for large orders
        if amount > 100000:  # NT$100k
            warnings.append('Large order amount')
        
        return True, warnings
    
    async def _submit_order_impl(self, order: Order) -> Order:
        """Submit order implementation (simulated with landing delay)."""
        if not self.authenticated:
            order.status = 'rejected'
            order.error = 'Not authenticated'
            return order
        
        # Generate order_id
        order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        order.order_id = order_id
        order.status = 'submitted'
        order.created_at = datetime.now()
        
        # Simulate landing delay (e.g. 2 seconds) before it appears in list_trades
        asyncio.create_task(self._delayed_landing_and_fill(order_id, order))
        
        return order
        
    async def _delayed_landing_and_fill(self, order_id: str, order: Order):
        """Simulate order landing and then subsequent fill."""
        await asyncio.sleep(2)  # Simulate 2s delay until it "lands" at broker
        self.orders[order_id] = order
        
        await asyncio.sleep(1)  # Simulate another 1s until it fills
        
        market_data = await self.get_market_data(order.symbol)
        price = order.price or market_data['price']
        
        order.filled_price = price
        order.filled_quantity = order.quantity
        order.filled_at = datetime.now()
        order.status = 'filled'
        order.fee = self.calculate_fee(price * order.quantity)
        order.tax = self.calculate_tax(price * order.quantity, order.action == 'sell')
        
        # Update account
        account_id = order.account_id or self.config.get('account_id', 'paper_001')
        self._update_account_after_fill(account_id, order)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (not applicable for paper trading immediate fills)."""
        # Paper trading fills immediately, so cancellation not supported
        return False
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        return self.orders[order_id]
    
    async def list_trades(self) -> List[Any]:
        """List trades (simulated)."""
        return list(self.orders.values())
    
    def _update_account_after_fill(self, account_id: str, order: Order):
        """Update account balance and positions after order fill."""
        account = self.accounts[account_id]
        
        if order.action == 'buy':
            # Deduct cash
            total_cost = order.filled_price * order.filled_quantity + order.fee + order.tax
            account['balance'] -= total_cost
            account['buying_power'] -= total_cost
            
            # Add/update position
            symbol = order.symbol
            if symbol not in account['positions']:
                account['positions'][symbol] = {
                    'quantity': 0,
                    'average_price': 0,
                    'current_price': order.filled_price
                }
            
            pos = account['positions'][symbol]
            total_qty = pos['quantity'] + order.filled_quantity
            total_cost_basis = (pos['quantity'] * pos['average_price'] + 
                              order.filled_quantity * order.filled_price)
            pos['average_price'] = total_cost_basis / total_qty if total_qty > 0 else 0
            pos['quantity'] = total_qty
            
        else:  # sell
            # Add cash
            total_proceeds = order.filled_price * order.filled_quantity - order.fee - order.tax
            account['balance'] += total_proceeds
            account['buying_power'] += total_proceeds
            
            # Reduce position
            symbol = order.symbol
            if symbol in account['positions']:
                pos = account['positions'][symbol]
                pos['quantity'] -= order.filled_quantity
                if pos['quantity'] <= 0:
                    del account['positions'][symbol]
