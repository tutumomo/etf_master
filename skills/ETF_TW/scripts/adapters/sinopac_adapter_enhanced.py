#!/usr/bin/env python3
"""
SinoPac Securities Enhanced Adapter for ETF_TW.
Includes:
- ✅ 漲跌停檢查
- ✅ 交易限額查詢
- ✅ 成交回報回調框架
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

try:
    import shioaji as sj
    from shioaji.constant import Action, StockPriceType, OrderType, StockOrderCond, StockOrderLot
    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False

from .base import BaseAdapter, Order, Position, AccountBalance

try:
    from ..trading_hours_gate import get_trading_hours_info
except ImportError:
    from trading_hours_gate import get_trading_hours_info

class SinopacAdapterEnhanced(BaseAdapter):
    """
    Enhanced SinoPac Securities (Shioaji) adapter.
    包含所有基礎功能 + 進階檢查與回調
    """
    
    def __init__(self, broker_id: str, config: Dict[str, Any]):
        super().__init__(broker_id, config)
        self.api_key = config.get('api_key')
        self.secret_key = config.get('secret_key')
        self.mode = config.get('mode', 'paper')
        self.api = None
        self.stock_account = None
        self.order_callbacks = []  # 訂單回調列表
        
        if SHIOAJI_AVAILABLE:
            self.api = sj.Shioaji(simulation=(self.mode != 'live'))
    
    async def authenticate(self) -> bool:
        """Authenticate with Shioaji API."""
        if not SHIOAJI_AVAILABLE:
            return False
        
        try:
            accounts = self.api.login(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            
            if accounts:
                self.authenticated = True
                # 自動設定預設帳戶
                for acc in accounts:
                    if acc.account_id == "0737121":  # 優先使用證券帳戶
                        self.stock_account = acc
                        break
                
                if not self.stock_account and accounts:
                    self.stock_account = accounts[0]
                
                print(f"[SinoPac Enhanced] 登入成功，使用帳戶：{self.stock_account.account_id}")
                return True
            else:
                return False
        except Exception as e:
            print(f"[SinoPac Enhanced] 認證失敗：{e}")
            return False
    
    # ✅ 功能 1: 漲跌停檢查
    async def check_price_limits(self, symbol: str, price: float) -> Dict[str, Any]:
        """
        檢查價格是否超過漲跌停限制
        
        Returns:
            {
                'valid': bool,
                'limit_up': float,
                'limit_down': float,
                'reference': float,
                'warnings': List[str]
            }
        """
        result = {
            'valid': True,
            'limit_up': None,
            'limit_down': None,
            'reference': None,
            'warnings': []
        }
        
        try:
            clean_symbol = symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            
            if contract:
                result['limit_up'] = contract.limit_up
                result['limit_down'] = contract.limit_down
                result['reference'] = contract.reference
                
                # 檢查漲停
                if price > contract.limit_up:
                    result['valid'] = False
                    result['warnings'].append(f"價格 {price} 超過漲停價 {contract.limit_up}")
                
                # 檢查跌停
                if price < contract.limit_down:
                    result['valid'] = False
                    result['warnings'].append(f"價格 {price} 低於跌停價 {contract.limit_down}")
                
                # 檢查偏離參考價過遠
                if contract.reference:
                    deviation = abs(price - contract.reference) / contract.reference
                    if deviation > 0.10:  # 偏離超過 10%
                        result['warnings'].append(f"價格 {price} 偏離參考價 {contract.reference} 達 {deviation*100:.2f}%")
        
        except Exception as e:
            result['warnings'].append(f"無法檢查漲跌停：{e}")
        
        return result
    
    # ✅ 功能 2: 交易限額查詢
    async def query_trade_limits(self) -> Dict[str, Any]:
        """
        查詢交易限額（需審核通過後才能使用）
        
        Returns:
            {
                'can_query': bool,
                'buy_limit': float,
                'sell_limit': float,
                'error': str
            }
        """
        result = {
            'can_query': False,
            'buy_limit': 0,
            'sell_limit': 0,
            'error': None
        }
        
        if not self.authenticated:
            result['error'] = "未認證"
            return result
        
        try:
            # 嘗試查詢交易限額
            # 注意：此功能需要審核通過後才能使用
            limits = self.api.query_trade_limit()
            
            if limits:
                result['can_query'] = True
                result['buy_limit'] = getattr(limits, 'buy_limit', 0)
                result['sell_limit'] = getattr(limits, 'sell_limit', 0)
            else:
                result['error'] = "無法查詢交易限額（可能尚未開通）"
        
        except Exception as e:
            result['error'] = f"查詢失敗：{e}"
        
        return result
    
    # ✅ 功能 3: 成交回報回調框架
    def on_order_complete(self, callback: Callable):
        """
        註冊訂單完成回調函數
        
        Usage:
        @adapter.on_order_complete
        def my_callback(api, order, status):
            print(f"訂單完成：{order}")
        """
        self.order_callbacks.append(callback)
    
    def _handle_order_callback(self, api, order, status):
        """內部回調處理"""
        for callback in self.order_callbacks:
            try:
                callback(api, order, status)
            except Exception as e:
                print(f"回調執行失敗：{e}")
    
    async def validate_order(self, order: Order) -> tuple[bool, List[str]]:
        """
        增強版訂單驗證（包含漲跌停檢查）
        """
        warnings = []
        errors = []
        
        if not self.authenticated:
            return False, ['未認證']
        
        if not order.symbol:
            return False, ['需要指定標的']
        
        if order.quantity <= 0:
            return False, ['數量必須為正數']
        
        # ✅ 漲跌停檢查
        if order.price:
            limit_check = await self.check_price_limits(order.symbol, order.price)
            
            if not limit_check['valid']:
                errors.extend(limit_check['warnings'])
            
            warnings.extend(limit_check['warnings'][:-1] if limit_check['warnings'] else [])
        
        # 檢查零股
        if order.quantity % 1000 != 0:
            warnings.append("非整股交易（Odd Lot），請確認券商介面支援")
        
        if errors:
            return False, errors
        
        return True, warnings
    
    async def submit_order(self, order: Order) -> Order:
        """
        增強版下單（包含回調設定）
        """
        if not self.authenticated:
            order.status = 'rejected'
            order.error = '未認證'
            return order
        
        try:
            # 1. 取得合約
            clean_symbol = order.symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            
            # 2. 設定動作
            action = Action.Buy if order.action.lower() == 'buy' else Action.Sell
            
            # 3. 設定價格類型
            if order.order_type and order.order_type.lower() == 'limit':
                price_type = StockPriceType.LMT
            else:
                price_type = StockPriceType.MKT
            
            # 4. 建立訂單
            # 台股內部統一以「股」表示；送 Shioaji 時才依市場別轉換：
            # Common 整股用「張」；零股用「股」，盤中 IntradayOdd、盤後 Odd。
            if order.quantity % 1000 == 0:
                lots = order.quantity // 1000
                order_lot = StockOrderLot.Common
            elif 1 <= order.quantity <= 999:
                lots = order.quantity
                hours_info = get_trading_hours_info()
                order_lot = StockOrderLot.Odd if hours_info.get("in_after_hours") else StockOrderLot.IntradayOdd
                if price_type != StockPriceType.LMT:
                    price_type = StockPriceType.LMT
            else:
                order.status = 'rejected'
                order.error = '非整張數量必須為 1-999 股零股'
                return order
            
            sj_order = self.api.Order(
                price=order.price or contract.reference,
                quantity=lots,
                action=action,
                price_type=price_type,
                order_type=OrderType.ROD,
                order_lot=order_lot,
            )
            
            # 5. 設定回調
            self.api.set_order_callback(self._handle_order_callback)
            
            # 6. 送出訂單
            trade = self.api.place_order(self.stock_account, sj_order)
            
            order.status = 'submitted'
            order.order_id = str(getattr(trade, 'id', ''))
            order.created_at = datetime.now()
            
            print(f"[SinoPac Enhanced] 訂單已送出：{order.action} {order.symbol} {order.quantity}股")
            
            return order
        
        except Exception as e:
            order.status = 'rejected'
            order.error = str(e)
            print(f"[SinoPac Enhanced] 下單失敗：{e}")
            return order
    
    # 實作抽象方法
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """取得市場資料"""
        if not self.authenticated:
            return {}
        
        try:
            clean_symbol = symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            snapshots = self.api.snapshots([contract])
            
            if snapshots:
                s = snapshots[0]
                return {
                    'symbol': symbol,
                    'price': s.close,
                    'change': s.change,
                    'change_percent': s.change_rate,
                    'volume': s.volume,
                    'bid': s.bid_price,
                    'ask': s.ask_price,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            print(f"市場資料查詢失敗：{e}")
        
        return {}
    
    async def get_account_balance(self, account_id: str = None) -> AccountBalance:
        """取得帳戶餘額（需要審核通過）"""
        if not self.authenticated:
            raise RuntimeError("未認證")
        
        try:
            balance_data = self.api.account_balance(self.stock_account)
            return AccountBalance(
                account_id=account_id or self.stock_account.account_id,
                broker_id=self.broker_id,
                buying_power=float(getattr(balance_data, 'acc_balance', 0)),
                cash_available=float(getattr(balance_data, 'acc_balance', 0)),
                market_value=0.0,
                total_value=float(getattr(balance_data, 'acc_balance', 0)),
                unrealized_pnl=0.0
            )
        except Exception as e:
            print(f"餘額查詢失敗：{e}")
            raise
    
    async def get_positions(self, account_id: str = None) -> List[Position]:
        """取得持股（需要審核通過）"""
        if not self.authenticated:
            raise RuntimeError("未認證")
        
        try:
            api_positions = self.api.list_positions(self.stock_account)
            positions = []
            
            for p in api_positions:
                positions.append(Position(
                    symbol=p.code,
                    quantity=p.quantity,
                    average_price=p.price,
                    current_price=p.last_price,
                    market_value=p.last_price * p.quantity,
                    unrealized_pnl=p.pnl
                ))
            
            return positions
        except Exception as e:
            print(f"持股查詢失敗：{e}")
            raise
    
    async def preview_order(self, order: Order) -> Order:
        """預覽訂單"""
        market_data = await self.get_market_data(order.symbol)
        price = order.price or market_data.get('price', 0)
        
        amount = price * order.quantity
        fee = self.calculate_fee(amount)
        tax = self.calculate_tax(amount, order.action.lower() == 'sell')
        
        order.fee = fee
        order.tax = tax
        order.status = 'preview'
        
        return order
    
    async def get_order_status(self, order_id: str) -> Order:
        """查詢訂單狀態"""
        # TODO: 實作訂單狀態查詢
        return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消訂單"""
        # TODO: 實作取消訂單
        return False


# Factory function
def create_sinopac_adapter_enhanced(config: Dict[str, Any]) -> SinopacAdapterEnhanced:
    """建立增強版永豐適配器"""
    return SinopacAdapterEnhanced('sinopac', config)
